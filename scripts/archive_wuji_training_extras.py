"""Preserve completed runs' additional weights, initialization and TensorBoard logs."""
import argparse
import datetime
import hashlib
import json
import shlex
import subprocess
import tarfile
from pathlib import Path

from scripts.monitor_wuji_multigrasp_round import SSH, REMOTE

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='+', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    entries = []
    for name in args.names:
        assert Path(name).name == name and name not in ('.', '..')
        target = ROOT / 'runs' / name
        target.mkdir(exist_ok=True)
        code = f"import pathlib,json,hashlib; r=pathlib.Path({REMOTE!r}); assert json.loads((r/'runs/multigrasp-20260928'/{name!r}/'status.json').read_text())['status']=='completed'; print(json.dumps([dict(path=str(p.relative_to(r)),sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()) for p in (r/'runs'/{name!r}).rglob('*') if p.is_file() and 'checkpoints' not in p.relative_to(r/'runs'/{name!r}).parts]))"
        # Remote Python may predate hashlib.file_digest.
        code = code.replace("hashlib.file_digest(p.open('rb'),'sha256').hexdigest()", "hashlib.sha256(p.read_bytes()).hexdigest()")
        remote = json.loads(subprocess.check_output(SSH + ['python3 -c ' + shlex.quote(code)], text=True, timeout=180))
        subprocess.run(['rsync', '-a', '--exclude=checkpoints', '-e', shlex.join(SSH[:-1]),
                        SSH[-1] + ':' + REMOTE + '/runs/' + name + '/', str(target) + '/'], check=True, timeout=600)
        for entry in remote:
            assert sha(ROOT / entry['path']) == entry['sha256']
            entry['bytes'] = (ROOT / entry['path']).stat().st_size
        entries.extend(remote)
    receipt = ROOT / 'research/multigrasp-20260928/receipts' / (args.label + '-training-extras.json')
    assert not receipt.exists()
    receipt.write_text(json.dumps(dict(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), entries=entries,
                                      scope='Additional trainer-saved weights and logs, all remote/local SHA verified. Not used for checkpoint selection or new evaluation claims.'), indent=2) + '\n')
    archive = ROOT / 'runs/multigrasp-20260928/delivery' / ('wuji-' + args.label + '-training-extras.tar.gz')
    with tarfile.open(archive, 'x:gz', compresslevel=1) as tar:
        tar.add(receipt, arcname=receipt.name)
        for entry in entries:
            tar.add(ROOT / entry['path'], arcname=entry['path'])
    print(json.dumps(dict(archive=str(archive), bytes=archive.stat().st_size, sha256=sha(archive), files=len(entries))))


if __name__ == '__main__':
    main()
