"""Hash-verify new remote policy snapshots, then evaluate locally after the oracle run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--spec', type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.spec.read_text())
    root = Path(spec['root'])
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    queue = json.loads((root/spec['queue']).read_text())
    needed = sorted({j['checkpoint'] for j in queue if 'evaluation/inbox/' in j['checkpoint']})
    state = dict(status='waiting_for_oracle', pid=os.getpid(), started=datetime.now(timezone.utc).isoformat(),
                 spec=spec, downloads={}, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'scheduler-source.py').write_bytes(Path(__file__).read_bytes())
    child = None
    ssh = spec['ssh']

    def save():
        state['heartbeat'] = datetime.now(timezone.utc).isoformat()
        temporary = out/'status.tmp'
        temporary.write_text(json.dumps(state, indent=2)+'\n')
        temporary.replace(out/'status.json')

    try:
        save()
        deadline = time.monotonic()+86400
        while True:
            assert time.monotonic() < deadline, '24 hour coordinator deadline exceeded'
            pending = [n for n in needed if n not in state['downloads']]
            if pending:
                program = ('from pathlib import Path\nimport hashlib,json\nr=Path('+repr(spec['remote_root'])+')\n'
                           'names='+repr(pending)+'\nresult=[]\n'
                           'for name in names:\n p=r/name\n'
                           ' if p.is_file() and p.with_suffix(".json").is_file():result.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))\n'
                           'print(json.dumps(result))\n')
                response = subprocess.run(ssh+['python3 -'], input=program, text=True, capture_output=True, timeout=40)
                if response.returncode:
                    state['last_sync_error'] = dict(time=datetime.now(timezone.utc).isoformat(), error=response.stderr[-2000:])
                else:
                    for item in json.loads(response.stdout):
                        name = item['path']
                        assert name in pending
                        destination = root/name
                        buffer = out/'transfers'/name
                        buffer.parent.mkdir(parents=True, exist_ok=True)
                        remote = ssh[-1]+':'+spec['remote_root']+'/'+name
                        subprocess.run(['rsync', '-a', '-e', ' '.join(ssh[:-1]), remote, str(buffer)], check=True, timeout=90)
                        assert hashlib.sha256(buffer.read_bytes()).hexdigest() == item['sha256']
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        if destination.exists():
                            assert hashlib.sha256(destination.read_bytes()).hexdigest() == item['sha256']
                            buffer.unlink()
                        else:
                            buffer.replace(destination)
                        state['downloads'][name] = dict(item, verified=datetime.now(timezone.utc).isoformat())
                        save()
            predecessor = json.loads((root/spec['after_run']/'status.json').read_text())
            if child is None:
                assert predecessor['status'] != 'failed', predecessor.get('error')
                if predecessor['status'] == 'completed':
                    command = [spec['python'], '-m', 'scripts.run_wuji_goal_audits', '--queue', str(root/spec['queue']),
                               '--gpu', '0', '--checkpoint-wait-seconds', '21600']
                    with (out/'evaluations.log').open('w') as log:
                        child = subprocess.Popen(command, cwd=spec['pin'], stdin=subprocess.DEVNULL,
                                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    state.update(status='evaluating_and_syncing', evaluator_pid=child.pid, command=command)
            if child is not None and child.poll() is not None:
                state['evaluator_returncode'] = child.returncode
                assert child.returncode == 0
                results = {}
                for job in queue:
                    path = root/'runs/wuji-goal/verification'/job['name']/'status.json'
                    report = json.loads(path.read_text())
                    assert report['status'] == 'completed' and report['returncode'] == 0, (job['name'], report)
                    results[job['name']] = report['returncode']
                state.update(status='completed', finished=datetime.now(timezone.utc).isoformat(), results=results)
                save()
                break
            save()
            time.sleep(20)
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        save()


if __name__ == '__main__':
    main()
