"""Rescore newly completed mechanism diagnostics every five minutes."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    state = dict(status='monitoring', pid=os.getpid(), started=now(), audits=[],
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    previous = []

    def save():
        state['heartbeat'] = now()
        temp = args.output/'status.tmp'
        temp.write_text(json.dumps(state, indent=2)+'\n')
        temp.replace(args.output/'status.json')

    save()
    try:
        while True:
            run = json.loads((args.run/'status.json').read_text())
            completed = [s['name'] for s in run['stages'] if s['status'] == 'completed' and s['returncode'] == 0]
            if completed and completed != previous:
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                target = args.output/f'audit-{len(completed):02d}-{stamp}.json'
                command = [sys.executable, '-m', 'scripts.rescore_wuji_reset_mechanism', '--root', str(args.root),
                           '--run', str(args.run), '--output', str(target), '--allow-partial']
                with target.with_suffix('.log').open('w') as stream:
                    code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
                assert code == 0, target
                audit = json.loads(target.read_text())
                state['last_audit'] = str(target.relative_to(args.root))
                state['audits'].append(dict(path=state['last_audit'], completed=len(completed)))
                lines = ['# Frozen reset mechanism diagnosis', '', now(), '',
                         'Observed development rows. Normalizer swaps and holding are diagnostic controllers, not new learned policies.', '',
                         '|Condition|Success / 300|Body stable / 300|Body stable at .5s / 300|Fourth success / 32|',
                         '|---|---:|---:|---:|---:|']
                for name, result in audit['results'].items():
                    if result['formal']:
                        groups = result['groups']
                        values = [sum(g[k] for g in groups[:3]) for k in ['success', 'body', 'body_stable_half_second']]
                        lines.append('|'+name+'|'+'|'.join(map(str, values))+f"|{groups[3]['success']}|")
                (args.output/'LATEST.md').write_text('\n'.join(lines)+'\n')
                previous = completed
                save()
            if run['status'] == 'failed':
                state.update(status='source_failed', error=run.get('error'), finished=now())
                break
            if run['status'] == 'completed' and len(completed) == len(run['spec']['stages']):
                assert audit['status'] == 'verified_complete'
                state.update(status='completed', finished=now())
                break
            save()
            time.sleep(300)
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
