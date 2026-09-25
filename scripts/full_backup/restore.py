#!/usr/bin/env python3
"""Verify all packs, restore selected/all paths, and verify each file SHA256."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def safe_relative(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Unsafe relative path: ' + name)
    return p


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--destination', type=Path)
    p.add_argument('--prefix', action='append', default=[])
    p.add_argument('--verify-only', action='store_true')
    p.add_argument('--relocate-internal-links', action='store_true')
    args = p.parse_args()
    index = json.loads((args.backup / 'wuji-full-backup-20260925-index.json').read_text())
    manifest = args.backup / index['manifest']['name']
    assert digest(manifest) == index['manifest']['sha256'], 'Manifest checksum mismatch'
    entries = [json.loads(line) for line in manifest.read_text().splitlines()]
    selected = [e for e in entries if not args.prefix or any(
        e['path'] == prefix or e['path'].startswith(prefix.rstrip('/') + '/') for prefix in args.prefix)]
    if not selected:
        raise ValueError('No files match selection')
    needed = {c['sha256'] for e in selected for c in e.get('chunks', [])}
    if args.verify_only and not args.prefix:
        needed = set(index['blob_index'])
    packs = {index['blob_index'][b]['pack'] for b in needed}
    all_records = {r['name']: r for r in index['packs']}
    if not args.verify_only:
        if not args.destination:
            raise ValueError('--destination is required for restoration')
        args.destination.mkdir(parents=True, exist_ok=True)
        if any(args.destination.iterdir()):
            raise ValueError('Restore destination must be empty')
    verified_blobs = set()
    with tempfile.TemporaryDirectory(prefix='wuji-restore-') as temp:
        cache = Path(temp)
        for name in sorted(packs):
            path = args.backup / name
            if not path.is_file():
                path = args.backup / 'packs' / name
            record = all_records[name]
            assert path.stat().st_size == record['bytes'] and digest(path) == record['sha256'], name
            proc = subprocess.Popen(['zstd', '-q', '-d', '-c', str(path)], stdout=subprocess.PIPE)
            try:
                with tarfile.open(fileobj=proc.stdout, mode='r|') as archive:
                    for member in archive:
                        blob = member.name.removeprefix('blobs/')
                        if member.name != 'blobs/' + blob or len(blob) != 64 or any(c not in '0123456789abcdef' for c in blob):
                            raise ValueError('Invalid blob member')
                        if blob not in needed:
                            continue
                        assert member.isfile() and member.size == index['blob_index'][blob]['size']
                        stream = archive.extractfile(member)
                        h = hashlib.sha256()
                        output = None if args.verify_only else (cache / blob).open('wb')
                        try:
                            for data in iter(lambda: stream.read(8 * 1024**2), b''):
                                h.update(data)
                                if output:
                                    output.write(data)
                        finally:
                            if output:
                                output.close()
                        assert h.hexdigest() == blob, 'Blob checksum mismatch: ' + blob
                        verified_blobs.add(blob)
                proc.stdout.close()
                assert proc.wait() == 0, 'Decompression failed: ' + name
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
            print(json.dumps(dict(pack=name, verified_blobs=len(verified_blobs), needed=len(needed))), flush=True)
        assert needed == verified_blobs, 'Missing blobs'
        restored = 0
        if not args.verify_only:
            # Files precede symlinks so a stored symlink cannot redirect a write.
            for entry in selected:
                relative = safe_relative(entry['path'])
                target = args.destination.joinpath(*relative.parts)
                if entry['type'] == 'directory':
                    target.mkdir(parents=True, exist_ok=True)
                elif entry['type'] == 'file':
                    target.parent.mkdir(parents=True, exist_ok=True)
                    h = hashlib.sha256()
                    with target.open('xb') as output:
                        for chunk in entry['chunks']:
                            with (cache / chunk['sha256']).open('rb') as source:
                                for data in iter(lambda: source.read(8 * 1024**2), b''):
                                    output.write(data)
                                    h.update(data)
                    assert h.hexdigest() == entry['sha256'] and target.stat().st_size == entry['size']
                    os.chmod(target, entry['mode'])
                    os.utime(target, ns=(entry['mtime_ns'], entry['mtime_ns']))
                    restored += 1
            for entry in selected:
                if entry['type'] != 'symlink':
                    continue
                target = args.destination.joinpath(*safe_relative(entry['path']).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                link = entry['target']
                if args.relocate_internal_links and os.path.isabs(link):
                    for alias, original in sorted(index['roots'].items(), key=lambda x: -len(x[1])):
                        if link == original or link.startswith(original.rstrip('/') + '/'):
                            suffix = link[len(original):].lstrip('/')
                            replacement = args.destination / alias / suffix
                            link = os.path.relpath(replacement, target.parent)
                            break
                target.symlink_to(link)
            for entry in reversed(selected):
                if entry['type'] == 'directory':
                    target = args.destination.joinpath(*safe_relative(entry['path']).parts)
                    os.chmod(target, entry['mode'])
                    os.utime(target, ns=(entry['mtime_ns'], entry['mtime_ns']))
        print(json.dumps(dict(status='verified', packs=len(packs), blobs=len(verified_blobs),
                              restored_files=restored, selected_entries=len(selected))), flush=True)


if __name__ == '__main__':
    main()
