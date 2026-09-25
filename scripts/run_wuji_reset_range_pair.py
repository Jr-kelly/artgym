"""Reserve one four-host GPU after full diagnosis, run two gated PPO arms, restore CP pool."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--spec', type=Path, required=True)
    args = p.parse_args()
    spec = json.loads(args.spec.read_text())
    gpu = int(spec['training_gpu'])
    assert gpu in [1, 2]
    reserved_pool = [g for g in [2, 1] if g != gpu]
    assert os.uname().nodename == 'd-20260920124121-d9ns7'
    pin, root = Path(__file__).resolve().parents[1], Path(spec['root'])
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    state = dict(status='waiting_for_diagnosis', started=now(), pid=os.getpid(), spec=spec, stages=[])
    atomic_json(out/'status.json', state)
    lease, child, reserved = None, None, False
    cfgpath = root/'sharpa_corrected_recovery_monitor.json'

    def pool(gpus):
        cfg = json.loads(cfgpath.read_text())
        pid = int((Path(cfg['state_dir'])/'monitor.pid').read_text())
        cmd = (Path('/proc')/str(pid)/'cmdline').read_bytes()
        assert b'--worker' not in cmd and str(cfgpath).encode() in cmd
        before = cfg['evaluation_gpus']
        assert before == ([2, 1] if gpus == reserved_pool else reserved_pool)
        cfg['evaluation_gpus'] = gpus
        atomic_json(cfgpath, cfg)
        os.kill(pid, signal.SIGTERM)
        time.sleep(.5)
        with (out/('scheduler-'+('-'.join(map(str, gpus)))+'.log')).open('w') as log:
            proc = subprocess.Popen([cfg['python'], str(root/'scripts/monitor_wuji_checkpoints.py'), '--config', str(cfgpath)],
                                    cwd=root, env=runtime_environment(cfg), stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        state.setdefault('scheduler_changes', []).append(dict(time=now(), old_pid=pid, new_pid=proc.pid, before=before, after=gpus))
        atomic_json(out/'status.json', state)

    def run(name, command):
        nonlocal child
        with (out/(name+'.log')).open('w') as log:
            child = subprocess.Popen(command, cwd=pin,
                                     env=runtime_environment(dict(project=str(pin), python=sys.executable), gpu),
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     pass_fds=(lease.fileno(),), start_new_session=True)
        row = dict(name=name, status='running', pid=child.pid, command=command, started=now())
        state['stages'].append(row)
        state.update(status=name, heartbeat=now())
        atomic_json(out/'status.json', state)
        code = child.wait()
        row.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
        atomic_json(out/'status.json', state)
        assert code == 0, row

    try:
        deadline = time.monotonic()+86400
        evidence = root/spec['diagnosis']
        while not evidence.exists():
            assert time.monotonic() < deadline, 'Diagnosis wait exceeded 24 hours'
            state.update(heartbeat=now())
            atomic_json(out/'status.json', state)
            time.sleep(15)
        diagnosis = json.loads(evidence.read_text())
        assert diagnosis['status'] == 'verified_teacher_complete' and diagnosis['physics_transitions'] == 398400
        # Training targets a measured teacher robustness gap, not just vision error.
        assert any(diagnosis['conditions'][f'teacher-{s}s']['success'] < 285 for s in [2, 5])
        state['diagnosis_sha256'] = hashlib.sha256(evidence.read_bytes()).hexdigest()
        pool(reserved_pool)
        reserved = True
        state.update(status=f'waiting_for_gpu{gpu}_lease')
        atomic_json(out/'status.json', state)
        while lease is None:
            lease = acquire_evaluation_gpu(gpu)
            if lease is None:
                state.update(heartbeat=now())
                atomic_json(out/'status.json', state)
                time.sleep(10)
        used = int(subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True).strip())
        assert used < 1000, used
        manifest = pin/spec['suite']
        suites = json.loads(manifest.read_text())['experiments']
        for arm in spec['arms']:
            name, amplitude = arm['name'], arm['amplitude']
            gate = root/arm['gate']
            gate.mkdir(exist_ok=False)
            atomic_json(gate/'status.json', dict(status='running', started=now()))
            run('range-gate-'+str(amplitude), [sys.executable, '-m', 'scripts.check_wuji_reset_training_range',
                                             '--amplitude', str(amplitude), '--output', str(gate)])
            report = json.loads((gate/'report.json').read_text())
            assert report['status'] == 'passed' and report['reset_range_amplitude'] == amplitude
            atomic_json(gate/'status.json', dict(status='completed', returncode=0, finished=now()))
            assert suites[name]['gpus'] == [gpu]
            run(name, [sys.executable, '-m', 'scripts.run_reference_experiment', '--manifest', str(manifest), '--name', name])
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
        if reserved:
            pool([2, 1])
        atomic_json(out/'status.json', state)


if __name__ == '__main__':
    main()
