"""Evaluate the existing paired checkpoints with copied custom-TCN weights.

Waits for the specified Sharpa student to finish; never interrupts it. All
evaluations use one GPU sequentially and are separate from the original
cross-GPU Conv1d run. This script performs no fitting or checkpoint selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    root = Path(spec['root'])
    pin = Path(__file__).resolve().parents[1]
    out = root/spec['output']
    source = root/spec['source_run']
    assert out.exists() and not (out/'status.json').exists()
    state = dict(status='waiting_for_sharpa_student', started=now(), spec=spec, stages=[],
        no_new_training=True, backend='custom_tcn', physical_gpus=[spec['gpu']])
    atomic_json(out/'status.json', state)

    def run(arm, update, seconds, runtime):
        prefix, batch = ('gate', 'runtime3') if runtime else ('formal', 'mixed332')
        name = f'{prefix}-{arm}-cp{update}-{batch}-{seconds}s'
        artifact = source/'fitting'/f'{arm}-update{update:04d}.pth'
        expected = spec['artifact_sha256'][artifact.name]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == expected
        row = dict(name=name, status='waiting_for_gpu', artifact_sha256=expected)
        stage = out/(name+'-process.json')
        atomic_json(stage, row)
        lease = None
        while lease is None:
            lease = acquire_evaluation_gpu(spec['gpu'])
            if lease is None:
                time.sleep(5)
        try:
            used = int(subprocess.check_output(['nvidia-smi', '-i', str(spec['gpu']),
                '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True).strip())
            assert used < 8000, used
            cmd = [sys.executable, '-m', 'scripts.eval_wuji_fitted_state_encoder',
                '--artifact', str(artifact), '--output', str(out/name), '--seconds', str(seconds),
                '--custom-command-tcn']
            if runtime:
                cmd.append('--runtime-check')
            with (out/(name+'.log')).open('w') as log:
                child = subprocess.Popen(cmd, cwd=pin,
                    env=runtime_environment(dict(project=str(pin), python=sys.executable), spec['gpu']),
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    pass_fds=(lease.fileno(),))
                row.update(status='running', pid=child.pid, started=now(), command=cmd)
                atomic_json(stage, row)
                code = child.wait()
            row.update(status='completed' if code == 0 else 'failed', returncode=code, finished=now())
            atomic_json(stage, row)
            assert code == 0, row
            audit = json.loads((out/name/'state-estimation-audit.json').read_text())
            assert audit['status'] == 'passed' and audit['state_encoder_backend'] == 'custom_tcn'
            assert audit['teacher_unchanged'] and audit['encoder_unchanged']
            assert not audit['current_privileged_actor_input']
            checks = audit['checks']
            assert checks['command_update_rows'] == checks['physics_transitions']
            if runtime:
                assert checks['privileged_invariance'] == checks['controller_input_checked_rows'] == 1800
            if update == 0:
                assert checks['zero_residual_rows'] == checks['physics_transitions']
            if arm == 'masked':
                assert checks['controller_input_changed_rows'] == 0
            elif update > 0:
                assert checks['controller_input_changed_rows'] > 0
            state['stages'].append(row)
            state['heartbeat'] = now()
            atomic_json(out/'status.json', state)
        finally:
            lease.close()

    def compare_initial(prefix, batch):
        comparisons = []
        for seconds in [2, 5]:
            paths = [out/f'{prefix}-{arm}-cp0-{batch}-{seconds}s' for arm in ['provided', 'masked']]
            for name in ['trace.npz', 'estimation-trace.npz']:
                with np.load(paths[0]/name) as a, np.load(paths[1]/name) as b:
                    assert a.files == b.files
                    for key in a.files:
                        assert np.array_equal(a[key], b[key]), (prefix, seconds, name, key)
                    comparisons.append(dict(seconds=seconds, file=name, keys=a.files, exact=True))
        atomic_json(out/(prefix+'-cp0-exact.json'), dict(comparisons=comparisons,
            scope='Same GPU, separate processes, unchanged initial weights; not cross-GPU validation.'))

    try:
        deadline = time.monotonic()+21600
        while True:
            predecessor = json.loads((root/spec['after_run']/'pipeline-status.json').read_text())
            assert predecessor['status'] != 'failed', predecessor.get('error')
            if predecessor['status'] == 'completed':
                break
            assert time.monotonic() < deadline
            state['heartbeat'] = now()
            atomic_json(out/'status.json', state)
            time.sleep(15)
        fitting = json.loads((source/'fitting/status.json').read_text())
        assert fitting['status'] == 'completed' and fitting['updates_completed'] == 1000
        state['source_fitting'] = fitting
        state['status'] = 'runtime_gates'
        atomic_json(out/'status.json', state)
        for update in [0, 1000]:
            for seconds in [2, 5]:
                for arm in ['provided', 'masked']:
                    run(arm, update, seconds, True)
        compare_initial('gate', 'runtime3')
        state['status'] = 'formal_evaluations'
        atomic_json(out/'status.json', state)
        for update in [0, 250, 1000]:
            for seconds in [2, 5]:
                for arm in ['provided', 'masked']:
                    run(arm, update, seconds, False)
            if update == 0:
                compare_initial('formal', 'mixed332')
        state.update(status='completed', finished=now(), all_initial_paired_traces_exact=True)
        atomic_json(out/'status.json', state)
    except BaseException as error:
        state.update(status='failed', error=repr(error), finished=now())
        atomic_json(out/'status.json', state)
        raise


if __name__ == '__main__':
    main()
