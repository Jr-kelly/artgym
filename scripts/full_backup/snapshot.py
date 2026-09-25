#!/usr/bin/env python3
"""Resumable, content-deduplicated project backup using standard tar+zstd packs."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(8 * 1024**2), b''):
            h.update(data)
    return h.hexdigest()


def signature(st):
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


class Snapshot:
    def __init__(self, folder):
        self.folder = folder
        self.spec = json.loads((folder / 'spec.json').read_text())
        self.packs = folder / 'packs'
        self.packs.mkdir(exist_ok=True)
        self.entries = {}
        self.blobs = {}
        self.pack_records = []
        for path in sorted(self.packs.glob('*.json')):
            record = json.loads(path.read_text())
            packed = self.packs / record['name']
            if not packed.is_file() or sha_file(packed) != record['sha256']:
                raise ValueError('Invalid completed pack: ' + str(packed))
            self.pack_records.append(record)
            self.blobs.update({k: dict(pack=record['name'], size=v) for k, v in record['blobs'].items()})
        journal = folder / 'entries.jsonl'
        if journal.exists():
            for line in journal.read_text().splitlines():
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self.entries[entry['path']] = entry
        self.journal = journal.open('a')
        self.pending = {}
        self.tar = None
        self.raw = None
        self.pack_bytes = 0
        self.started = now()
        self.last_status = 0
        self.visited = set()
        self.errors = []
        self.secret_findings = []
        prior = folder / 'credential-findings.json'
        if prior.exists():
            self.secret_findings = json.loads(prior.read_text())
        self.bytes_read = 0
        self.reused = 0
        self.current = None
        self.patterns = [
            (name, re.compile(pattern)) for name, pattern in [
                ('github_classic', rb'gh[pousr]_[A-Za-z0-9]{36,255}'),
                ('github_fine_grained', rb'github_pat_[A-Za-z0-9_]{60,255}'),
                ('private_key', rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
                ('openai_project_key', rb'sk-proj-[A-Za-z0-9_-]{40,255}'),
            ]
        ]

    def status(self, stage='snapshotting', force=False):
        if not force and time.monotonic() - self.last_status < 15:
            return
        self.last_status = time.monotonic()
        record = dict(stage=stage, updated=now(), started=self.started,
                      files_visited=len(self.visited), files_recorded=len(self.entries),
                      bytes_read_this_process=self.bytes_read, reused_files=self.reused,
                      unique_blobs=len(self.blobs) + len(self.pending),
                      completed_packs=len(self.pack_records),
                      compressed_bytes=sum(p['bytes'] for p in self.pack_records),
                      current=self.current, errors=self.errors,
                      credential_findings=len(self.secret_findings))
        atomic(self.folder / 'status.json', record)
        print(json.dumps(record, ensure_ascii=False), flush=True)

    def add_blob(self, digest, data):
        if digest in self.blobs or digest in self.pending:
            return
        import tarfile
        if self.tar is None:
            index = len(self.pack_records)
            self.raw = self.packs / ('wuji-full-backup-20260925-pack-%04d.tar' % index)
            self.tar = tarfile.open(self.raw, 'w', format=tarfile.PAX_FORMAT)
        info = tarfile.TarInfo('blobs/' + digest)
        info.size = len(data)
        info.mode = 0o600
        self.tar.addfile(info, io.BytesIO(data))
        self.pending[digest] = len(data)
        self.pack_bytes += len(data) + 512
        if self.pack_bytes >= self.spec['pack_raw_bytes']:
            self.seal()

    def seal(self):
        if self.tar is None:
            return
        self.tar.close()
        self.tar = None
        compressed = self.raw.with_suffix('.tar.zst')
        temporary = Path(str(compressed) + '.tmp')
        subprocess.run(['zstd', '-q', '-T2', '-3', '-f', str(self.raw), '-o', str(temporary)], check=True)
        subprocess.run(['zstd', '-q', '-t', str(temporary)], check=True)
        temporary.replace(compressed)
        record = dict(name=compressed.name, bytes=compressed.stat().st_size,
                      raw_bytes=self.raw.stat().st_size, sha256=sha_file(compressed),
                      created=now(), blobs=self.pending)
        atomic(compressed.with_suffix('.json'), record)
        self.pack_records.append(record)
        self.blobs.update({k: dict(pack=record['name'], size=v) for k, v in self.pending.items()})
        self.pending = {}
        self.pack_bytes = 0
        self.raw.unlink()
        self.journal.flush()
        self.status(force=True)

    def scan_credentials(self, data, entry, offset):
        for kind, pattern in self.patterns:
            match = pattern.search(data)
            if match:
                finding = dict(path=entry, kind=kind, offset=offset + match.start(),
                               value_sha256=hashlib.sha256(match.group()).hexdigest())
                if finding not in self.secret_findings:
                    self.secret_findings.append(finding)
                    atomic(self.folder / 'credential-findings.json', self.secret_findings)

    def save(self, entry):
        self.entries[entry['path']] = entry
        self.journal.write(json.dumps(entry, ensure_ascii=False) + '\n')
        self.status()

    def capture_file(self, path, archive_path, st):
        previous = self.entries.get(archive_path)
        if previous and previous.get('signature') == signature(st) and all(
                c['sha256'] in self.blobs or c['sha256'] in self.pending for c in previous.get('chunks', [])):
            self.reused += 1
            self.status()
            return
        for attempt in range(3):
            chunks = []
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                before = os.fstat(stream.fileno())
                remaining = before.st_size
                offset = 0
                tail = b''
                while remaining:
                    data = stream.read(min(self.spec['chunk_bytes'], remaining))
                    if not data:
                        break
                    self.bytes_read += len(data)
                    digest.update(data)
                    h = hashlib.sha256(data).hexdigest()
                    self.scan_credentials(tail + data, archive_path, max(0, offset - len(tail)))
                    tail = data[-512:]
                    self.add_blob(h, data)
                    chunks.append(dict(sha256=h, size=len(data)))
                    offset += len(data)
                    remaining -= len(data)
                    self.status()
                after = os.fstat(stream.fileno())
            current = path.stat()
            stable = signature(before) == signature(after) == signature(current) and remaining == 0
            # Append-only logs can be captured as an explicitly dated prefix. All
            # other changing files must become stable; no CP is silently truncated.
            append_log = (path.suffix in ('.log', '.jsonl') or path.name.startswith('events.out.tfevents'))
            prefix = (append_log and remaining == 0 and before.st_ino == after.st_ino == current.st_ino
                      and after.st_size >= before.st_size and current.st_size >= before.st_size)
            if stable or prefix:
                entry = dict(path=archive_path, type='file', size=before.st_size,
                             sha256=digest.hexdigest(), chunks=chunks, mode=stat.S_IMODE(before.st_mode),
                             mtime_ns=before.st_mtime_ns, uid=before.st_uid, gid=before.st_gid,
                             signature=signature(before), captured=now(),
                             consistency='stable_file' if stable else 'active_log_prefix')
                self.save(entry)
                return
        raise RuntimeError('File remained unstable after three attempts: ' + str(path))

    def visit(self, path, archive_path):
        self.current = archive_path
        self.visited.add(archive_path)
        try:
            st = path.lstat()
            metadata = dict(path=archive_path, mode=stat.S_IMODE(st.st_mode), mtime_ns=st.st_mtime_ns,
                            uid=st.st_uid, gid=st.st_gid, captured=now())
            if stat.S_ISLNK(st.st_mode):
                self.save(dict(metadata, type='symlink', target=os.readlink(path)))
            elif stat.S_ISDIR(st.st_mode):
                self.save(dict(metadata, type='directory'))
                for child in sorted(path.iterdir(), key=lambda p: p.name):
                    self.visit(child, archive_path + '/' + child.name)
            elif stat.S_ISREG(st.st_mode):
                self.capture_file(path, archive_path, st)
            else:
                raise RuntimeError('Unsupported special filesystem entry: ' + str(path))
        except (OSError, RuntimeError) as exc:
            self.errors.append(dict(path=archive_path, error=str(exc), time=now()))
            self.status(force=True)

    def run(self):
        self.status(force=True)
        for alias, directory in self.spec['roots'].items():
            self.visit(Path(directory), alias)
        self.seal()
        self.journal.flush()
        # Capture new files and changed checkpoints after the long first pass.
        self.errors = []
        self.visited = set()
        for alias, directory in self.spec['roots'].items():
            self.visit(Path(directory), alias)
        self.seal()
        self.journal.close()
        manifest = self.folder / 'wuji-full-backup-20260925-manifest.jsonl'
        with manifest.open('w') as output:
            for name in sorted(self.visited):
                if name in self.entries:
                    entry = self.entries[name]
                    assert all(c['sha256'] in self.blobs for c in entry.get('chunks', []))
                    output.write(json.dumps(entry, ensure_ascii=False) + '\n')
        active = [self.entries[p] for p in self.visited if p in self.entries]
        summary = dict(version=1, format='sha256-chunks-in-tar-zstd-v1', started=self.started, finished=now(),
                       roots=self.spec['roots'], scope=self.spec['scope'],
                       remote_pending=self.spec.get('remote_pending', []),
                       consistency='Per-file capture plus reconciliation pass; not an atomic cross-file filesystem snapshot. Active logs are captured through their observed length. Training was not paused.',
                       entries=len(active), files=sum(e['type'] == 'file' for e in active),
                       directories=sum(e['type'] == 'directory' for e in active),
                       symlinks=sum(e['type'] == 'symlink' for e in active),
                       logical_bytes=sum(e.get('size', 0) for e in active),
                       unique_blob_bytes=sum(e['size'] for e in self.blobs.values()),
                       manifest=dict(name=manifest.name, sha256=sha_file(manifest), bytes=manifest.stat().st_size),
                       packs=[{k: v for k, v in p.items() if k != 'blobs'} for p in self.pack_records],
                       blob_index=self.blobs, errors=self.errors,
                       credential_findings=self.secret_findings,
                       local_snapshot_complete=not self.errors,
                       all_hosts_complete=not self.errors and not self.spec.get('remote_pending'))
        atomic(self.folder / 'wuji-full-backup-20260925-index.json', summary)
        atomic(self.folder / 'credential-findings.json', self.secret_findings)
        self.status('snapshot_complete' if not self.errors else 'snapshot_incomplete', force=True)
        if self.errors:
            raise RuntimeError('Snapshot has errors; see index.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    Snapshot(parser.parse_args().folder).run()
