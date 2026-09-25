"""Replicate the fixed paired reset-range training seed using an exclusive lease.

Do not change the shared checkpoint scheduler pool: another diagnostic currently
owns GPU2. The inherited lease prevents competing schedulers from using GPU1.
"""
import argparse
import fcntl
import hashlib
import json
import os
import queue
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import legacy_evaluators


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    assert os.uname().nodename == 'd-20260920124121-d9ns7'
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    gpu = int(spec.get('training_gpu', 1))
    assert gpu in (1, 2)
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    state = dict(status=f'waiting_for_gpu{gpu}_lease', pid=os.getpid(), started=now(), spec=spec, stages=[])
    lease, child = None, None

    def save():
        state['heartbeat'] = now()
        atomic_json(out/'status.json', state)

    def run(name, command):
        nonlocal child
        with (out/(name+'.log')).open('w') as log:
            child = subprocess.Popen(command, cwd=pin,
                                     env=runtime_environment(dict(project=str(pin), python=sys.executable), gpu),
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     pass_fds=(lease.fileno(),), start_new_session=True)
        item = dict(name=name, status='running', pid=child.pid, command=command, started=now())
        state['stages'].append(item)
        state['status'] = name
        save()
        deadline = time.monotonic()+7200
        while child.poll() is None:
            assert time.monotonic() < deadline, name
            save()
            time.sleep(15)
        item.update(status='completed' if child.returncode == 0 else 'failed', returncode=child.returncode, finished=now())
        save()
        assert child.returncode == 0, item

    save()
    try:
        source = root/spec['original_teacher']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == spec['original_teacher_sha256']
        first = json.loads((root/spec['first_seed_status']).read_text())
        assert first['status'] == 'completed'
        deadline = time.monotonic()+86400
        ready = queue.Queue()

        def await_lease():
            stream = (Path('/tmp')/f'artgym-evaluation-gpu-{os.getuid()}-{gpu}.lock').open('a+')
            try:
                # Queue in the kernel while the existing evaluation finishes,
                # so a faster polling scheduler cannot repeatedly overtake us.
                fcntl.flock(stream, fcntl.LOCK_EX)
                while legacy_evaluators(gpu):
                    time.sleep(1)
                ready.put(stream)
            except BaseException as error:
                stream.close()
                ready.put(error)

        threading.Thread(target=await_lease, daemon=True).start()
        while lease is None:
            assert time.monotonic() < deadline
            try:
                result = ready.get(timeout=10)
            except queue.Empty:
                save()
                continue
            if isinstance(result, BaseException):
                raise result
            lease = result
        memory = int(subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=memory.used',
                                             '--format=csv,noheader,nounits'], text=True).strip())
        assert memory < 1000, memory
        for relative in spec.get('required_audit_monitors', []):
            state['status'] = 'waiting_for_required_audit'
            while True:
                assert time.monotonic() < deadline
                path = root/relative
                monitor = json.loads(path.read_text()) if path.exists() else {}
                assert monitor.get('status') not in ('failed', 'source_failed', 'evaluation_failed'), monitor
                if monitor.get('status') == 'completed':
                    audit_path = root/monitor['last_audit']
                    audit = json.loads(audit_path.read_text())
                    assert audit['status'] == 'verified_complete'
                    state.setdefault('required_audits', []).append(dict(
                        path=str(audit_path), sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest()))
                    break
                save()
                time.sleep(15)
        for arm in spec['arms']:
            gate = root/arm['gate']
            gate.mkdir(exist_ok=False)
            atomic_json(gate/'status.json', dict(status='running', started=now()))
            run('range-gate-'+arm.get('label', str(arm['amplitude'])), [sys.executable, '-m',
                spec.get('gate_module', 'scripts.check_wuji_reset_training_range'),
                '--amplitude', str(arm['amplitude']), '--output', str(gate)]+arm.get('gate_args', []))
            result = json.loads((gate/'report.json').read_text())
            assert result['status'] == 'passed' and result['reset_range_amplitude'] == arm['amplitude']
            atomic_json(gate/'status.json', dict(status='completed', returncode=0, finished=now()))
            run(arm['name'], [sys.executable, '-m', 'scripts.run_reference_experiment',
                             '--manifest', str(pin/spec['suite']), '--name', arm['name']])
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
