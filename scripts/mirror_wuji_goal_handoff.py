"""Mirror locally owned handoff/status documents to the shared remote filesystem.

No remote-owned training, GPU pools, experiment status, or checkpoint is copied
over. Raw results and source archives retain their separate verified workflows.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    root = Path(spec['root'])
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = dict(status='mirroring', pid=os.getpid(), started=now(), cycles=0,
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), spec=spec)

    def save():
        state['heartbeat'] = now()
        temp = out/'status.tmp'
        temp.write_text(json.dumps(state, indent=2)+'\n')
        temp.replace(out/'status.json')

    save()
    while True:
        try:
            names = set(spec['files'])
            directories = set(spec['local_status_directories'])
            if spec.get('registry_path'):
                # Only the explicitly local-owned registry entries may be
                # mirrored outward; remote run statuses stay remote-owned.
                registry = json.loads((root/spec['registry_path']).read_text())
                directories.update(registry.get('local_runs', []))
            for relative in sorted(directories):
                directory = root/relative
                for filename in ['status.json', 'LATEST.md']:
                    if (directory/filename).is_file():
                        names.add(str((directory/filename).relative_to(root)))
                status = directory/'status.json'
                if status.exists():
                    value = json.loads(status.read_text())
                    for field in ['last_audit', 'audit', 'verification']:
                        if value.get(field) and (root/value[field]).is_file():
                            names.add(str((root/value[field]).relative_to(root)))
            with tempfile.TemporaryDirectory(prefix='wuji-handoff-mirror-') as temporary:
                staging = Path(temporary)
                hashes = {}
                for name in sorted(names):
                    source = root/name
                    assert source.is_file() and not Path(name).is_absolute() and '..' not in Path(name).parts
                    before = source.stat()
                    data = source.read_bytes()
                    after = source.stat()
                    assert before.st_mtime_ns == after.st_mtime_ns and before.st_size == after.st_size == len(data), name
                    if source.suffix == '.json':
                        json.loads(data)
                    destination = staging/name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)
                    hashes[name] = hashlib.sha256(data).hexdigest()
                command = ['rsync', '-a', '-e', shlex.join(spec['ssh'][:-1]), str(staging)+'/',
                           spec['ssh'][-1]+':'+spec['remote_root']+'/']
                subprocess.run(command, check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # Read back remote content hashes; successful rsync alone is not
                # recorded as a verified mirror.
                program = ('from pathlib import Path\nimport hashlib,json\nr=Path('+repr(spec['remote_root'])+')\n'
                           'names='+repr(sorted(hashes))+'\nprint(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in names}))\n')
                result = subprocess.run(spec['ssh']+['python3 -'], input=program, text=True,
                                        capture_output=True, check=True, timeout=30)
                assert json.loads(result.stdout) == hashes
            state.update(status='mirroring', last_success=now(), files=len(hashes), hashes=hashes, cycles=state['cycles']+1)
            state.pop('last_error', None)
        except Exception as error:
            state.update(status='retrying', last_error=repr(error), error_time=now())
        save()
        time.sleep(300)


if __name__ == '__main__':
    main()
