#!/usr/bin/env python3
"""Upload immutable backup assets to a user-authorized GitHub draft, with SHA256 verification."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import quote


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(data)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--release-id', type=int, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--include-metadata', action='store_true')
    args = parser.parse_args()
    env = os.environ.copy()
    for key in ('LD_LIBRARY_PATH', 'LD_PRELOAD'):
        env.pop(key, None)
    env['PATH'] = '/usr/bin:/bin:/usr/local/bin:' + env.get('PATH', '')
    token = subprocess.check_output(['gh', 'auth', 'token'], env=env, text=True).strip()
    assert token and not any(c in token for c in '\n\r"')
    receipts = args.folder / 'upload-receipts'
    receipts.mkdir(exist_ok=True)

    def remote_assets():
        pages = json.loads(subprocess.check_output([
            'gh', 'api', f'repos/Jr-kelly/artgym/releases/{args.release_id}/assets?per_page=100',
            '--paginate', '--slurp'], env=env, text=True))
        return {a['name']: a for page in pages for a in page}

    def upload(path):
        expected = sha(path)
        receipt = receipts / (path.name + '.json')
        if receipt.exists():
            value = json.loads(receipt.read_text())
            assert value['sha256'] == expected and value['size'] == path.stat().st_size
            return value
        asset = None
        for attempt in range(5):
            if attempt:
                existing = remote_assets().get(path.name)
                if existing:
                    asset = existing
                    break
            response = receipts / (path.name + '.response.tmp')
            command = ['curl', '-4', '--silent', '--show-error', '--fail-with-body', '--http1.1',
                       '--connect-timeout', '10', '--max-time', '1800', '--config', '-',
                       '--header', 'Content-Type: application/octet-stream',
                       '--data-binary', '@' + str(path.resolve()), '-o', str(response),
                       f'https://uploads.github.com/repos/Jr-kelly/artgym/releases/{args.release_id}/assets?name=' + quote(path.name)]
            process = subprocess.run(command, input='header = "Authorization: Bearer ' + token + '"\n',
                                     text=True, capture_output=True, env=env)
            if process.returncode == 0:
                asset = json.loads(response.read_text())
                break
            atomic(receipts / (path.name + f'.attempt-{attempt}.json'),
                   dict(time=now(), returncode=process.returncode, stderr=process.stderr,
                        response=response.read_text()[:2000] if response.exists() else ''))
            time.sleep(3)
        if asset is None:
            raise RuntimeError('Upload failed: ' + path.name)
        assert asset['name'] == path.name and asset['size'] == path.stat().st_size
        assert asset.get('digest') == 'sha256:' + expected and asset['state'] == 'uploaded'
        value = dict(name=path.name, sha256=expected, size=asset['size'],
                     release_id=args.release_id, asset_id=asset['id'],
                     url=asset['browser_download_url'], verified=now())
        atomic(receipt, value)
        print(json.dumps(value), flush=True)
        return value

    known = remote_assets()
    for a in known.values():
        if a.get('state') == 'uploaded' and a.get('digest', '').startswith('sha256:'):
            atomic(receipts / (a['name'] + '.json'),
                   dict(name=a['name'], sha256=a['digest'][7:], size=a['size'], release_id=args.release_id,
                        asset_id=a['id'], url=a['browser_download_url'], verified=now()))
    pending = {}
    done_names = set(known)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        while True:
            findings_path = args.folder / 'credential-findings.json'
            findings = json.loads(findings_path.read_text()) if findings_path.exists() else []
            resolutions_path = args.folder / 'credential-review.json'
            resolutions = json.loads(resolutions_path.read_text()) if resolutions_path.exists() else {}
            unresolved = [f for f in findings if resolutions.get(f['value_sha256']) != 'public_fixture_or_nonsecret']
            candidates = []
            if not unresolved:
                for record in sorted((args.folder / 'packs').glob('*.json')):
                    data = json.loads(record.read_text())
                    candidates.append(args.folder / 'packs' / data['name'])
                if args.include_metadata:
                    candidates.extend(sorted((args.folder / 'delivery').glob('*')))
            for future in list(pending):
                if future.done():
                    name = pending.pop(future)
                    future.result()
                    done_names.add(name)
            queued = set(pending.values())
            for path in candidates:
                if path.name not in done_names and path.name not in queued and len(pending) < args.workers:
                    pending[pool.submit(upload, path)] = path.name
            values = []
            for path in receipts.glob('*.json'):
                if '.attempt-' not in path.name:
                    value = json.loads(path.read_text())
                    if 'asset_id' in value:
                        values.append(value)
            atomic(args.folder / 'upload-status.json', dict(updated=now(), stage='credential_review_pending' if unresolved else 'uploading',
                   uploaded_assets=len(values), uploaded_bytes=sum(v['size'] for v in values),
                   inflight=list(pending.values()), candidates=len(candidates), unresolved_credential_findings=len(unresolved)))
            snapshot = args.folder / 'status.json'
            stage = json.loads(snapshot.read_text()).get('stage') if snapshot.exists() else ''
            all_done = not pending and all(p.name in done_names for p in candidates)
            if all_done and not unresolved and (args.once or stage == 'snapshot_complete'):
                break
            if args.once and unresolved:
                raise RuntimeError('Unreviewed credential-like content; see local findings')
            time.sleep(5)
    atomic(args.folder / ('upload-metadata-complete.json' if args.include_metadata else 'upload-packs-complete.json'),
           dict(finished=now(), release_id=args.release_id, uploaded_assets=len(done_names)))


if __name__ == '__main__':
    main()
