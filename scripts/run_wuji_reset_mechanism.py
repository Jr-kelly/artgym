"""Run a bounded, gated frozen-controller diagnosis after paired training ends."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    root, pin = Path(spec['root']), Path(__file__).resolve().parents[1]
    gpu = int(spec.get('gpu', 1))
    assert gpu in [1, 2]
    reserved_pool = [g for g in [2, 1] if g != gpu]
    assert os.uname().nodename == 'd-20260920124121-d9ns7'
    out = root/spec['output']
    out.mkdir(exist_ok=False)
    state = dict(status='waiting_for_paired_training', pid=os.getpid(), started=now(), spec=spec, stages=[])
    lease, reserved, child = None, False, None
    cfgpath = root/'sharpa_corrected_recovery_monitor.json'

    def save():
        state['heartbeat'] = now()
        atomic_json(out/'status.json', state)

    def pool(gpus):
        cfg = json.loads(cfgpath.read_text())
        previous = cfg['evaluation_gpus']
        assert previous == ([2, 1] if gpus == reserved_pool else reserved_pool), previous
        pid = int((Path(cfg['state_dir'])/'monitor.pid').read_text())
        command = (Path('/proc')/str(pid)/'cmdline').read_bytes()
        assert b'--worker' not in command and str(cfgpath).encode() in command
        cfg['evaluation_gpus'] = gpus
        atomic_json(cfgpath, cfg)
        os.kill(pid, signal.SIGTERM)
        time.sleep(.5)
        with (out/('scheduler-'+('-'.join(map(str, gpus)))+'.log')).open('w') as log:
            proc = subprocess.Popen([cfg['python'], str(root/'scripts/monitor_wuji_checkpoints.py'), '--config', str(cfgpath)],
                                    cwd=root, env=runtime_environment(cfg), stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        state.setdefault('scheduler_changes', []).append(dict(old_pid=pid, new_pid=proc.pid,
                                                              before=previous, after=gpus, time=now()))
        save()

    def run(stage):
        nonlocal child
        folder = out/stage['name']
        folder.mkdir(exist_ok=False)
        command = [sys.executable, '-m', stage['module'], '--output', str(folder)]+stage['args']
        with (folder/'worker.log').open('w') as log:
            child = subprocess.Popen(command, cwd=pin, env=runtime_environment(dict(project=str(pin), python=sys.executable), gpu),
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                     pass_fds=(lease.fileno(),), start_new_session=True)
        row = dict(name=stage['name'], status='running', pid=child.pid, started=now(), command=command)
        state['stages'].append(row)
        state['status'] = stage['name']
        save()
        deadline = time.monotonic()+1800
        while child.poll() is None:
            assert time.monotonic() < deadline, ('stage timeout', stage['name'])
            save()
            time.sleep(10)
        row.update(status='completed' if child.returncode == 0 else 'failed', returncode=child.returncode, finished=now())
        save()
        assert child.returncode == 0, row
        report = json.loads((folder/'report.json').read_text())
        assert report['recorded_steps'] == 600
        with np.load(folder/'trace.npz') as trace:
            assert trace['active'].shape == (600, stage['rows'])
        if 'reset_mechanism' in stage['module']:
            intervention = json.loads((folder/'intervention.json').read_text())
            assert intervention['frozen_tensors_verified_after_physics']
            assert intervention['transitions'] == 600*stage['rows']
        if stage.get('identical_to'):
            reference = out/stage['identical_to']
            with np.load(folder/'trace.npz') as one, np.load(reference/'trace.npz') as two:
                assert set(one.files) == set(two.files)
                assert all(np.array_equal(one[k], two[k]) for k in one.files), 'No-op wrapper changed the trace'
            assert json.loads((folder/'intervention.json').read_text())['changed_normalizer_tensors'] == []
            row['all_trace_arrays_identical'] = True
            save()

    save()
    try:
        deadline = time.monotonic()+86400
        while True:
            assert time.monotonic() < deadline
            previous = json.loads((root/spec['after_status']).read_text())
            if previous['status'] == 'completed':
                break
            assert previous['status'] != 'failed', 'Paired training failed'
            save()
            time.sleep(15)
        # Validate all frozen input digests before reserving any GPU capacity.
        for name, expected in spec['inputs'].items():
            assert hashlib.sha256((root/name).read_bytes()).hexdigest() == expected, name
        pool(reserved_pool)
        reserved = True
        state['status'] = f'waiting_for_gpu{gpu}_lease'
        save()
        while lease is None:
            assert time.monotonic() < deadline
            lease = acquire_evaluation_gpu(gpu)
            if lease is None:
                save()
                time.sleep(10)
        memory = int(subprocess.check_output(['nvidia-smi', '-i', str(gpu), '--query-gpu=memory.used',
                                             '--format=csv,noheader,nounits'], text=True).strip())
        assert memory < 1000, memory
        for stage in spec['stages']:
            run(stage)
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
        save()


if __name__ == '__main__':
    main()
