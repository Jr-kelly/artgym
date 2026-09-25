"""Evaluate one declared paired queue on one GPU, retaining a kernel lease."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import legacy_evaluators


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    assert os.uname().nodename == spec['hostname']
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    jobs = json.loads((root/spec['queue']).read_text())
    assert len(jobs) == 44 and len({j['name'] for j in jobs}) == 44
    gpu = spec['gpu']
    lease, child = None, None
    state = dict(status='waiting_for_gpu_lease', pid=os.getpid(), started=now(), spec=spec,
                 stages=[], queue_sha256=hashlib.sha256((root/spec['queue']).read_bytes()).hexdigest())

    def save():
        state['heartbeat'] = now()
        atomic_json(out/'status.json', state)

    save()
    try:
        ready = queue.Queue()

        def acquire():
            stream = (Path('/tmp')/f'artgym-evaluation-gpu-{os.getuid()}-{gpu}.lock').open('a+')
            fcntl.flock(stream, fcntl.LOCK_EX)
            while legacy_evaluators(gpu):
                time.sleep(1)
            ready.put(stream)

        threading.Thread(target=acquire, daemon=True).start()
        deadline = time.monotonic()+86400
        while lease is None:
            assert time.monotonic() < deadline
            try:
                lease = ready.get(timeout=10)
            except queue.Empty:
                save()
        used = int(subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=memory.used',
                                           '--format=csv,noheader,nounits'], text=True).strip())
        assert used < 1000, used
        for job in jobs:
            folder = root/'runs/wuji-goal/verification'/job['name']
            folder.mkdir(parents=True, exist_ok=True)
            assert not (folder/'status.json').exists(), folder
            checkpoint = root/job['checkpoint']
            required = [checkpoint]+[root/p for p in job.get('required_artifacts', [])]
            until = time.monotonic()+21600
            while not all(p.exists() for p in required):
                assert time.monotonic() < until, required
                if 'evaluation/inbox/' in job['checkpoint']:
                    pipeline = root/'runs'/Path(job['checkpoint']).parts[1]/'pipeline-status.json'
                    if pipeline.exists():
                        status = json.loads(pipeline.read_text())
                        assert status['status'] not in ('failed', 'completed'), status
                state['status'] = 'waiting_for_checkpoint'
                state['waiting_for'] = job['name']
                save()
                time.sleep(15)
            state.pop('waiting_for', None)
            assert job['module'] == 'scripts.audit_wuji_timed_commands'
            command = [sys.executable, '-m', job['module'], '--checkpoint', str(checkpoint),
                       '--output', str(folder)]+job['args']
            with (folder/'worker.log').open('w') as log:
                child = subprocess.Popen(command, cwd=pin,
                    env=runtime_environment(dict(project=str(pin), python=sys.executable), gpu),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    pass_fds=(lease.fileno(),), start_new_session=True)
            entry = dict(name=job['name'], status='running', pid=child.pid, started=now(), gpu=gpu,
                         command=command, checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
            state['stages'].append(entry)
            state['status'] = job['name']
            atomic_json(folder/'status.json', entry)
            until = time.monotonic()+1800
            while child.poll() is None:
                assert time.monotonic() < until, job['name']
                save()
                time.sleep(10)
            entry.update(status='completed' if child.returncode == 0 else 'failed',
                         returncode=child.returncode, finished=now())
            atomic_json(folder/'status.json', entry)
            save()
            assert child.returncode == 0, entry
        state.update(status='completed', finished=now())
    except BaseException as exc:
        state.update(status='failed', error=repr(exc), finished=now())
        raise
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if lease:
            lease.close()
        save()


if __name__ == '__main__':
    main()
