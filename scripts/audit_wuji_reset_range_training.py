"""Audit both completed reset-range training budgets, snapshots and statistics."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--training-spec', type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    goal = args.root/'runs/wuji-goal'
    source = goal/'frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth'
    original = torch.load(source, map_location='cpu')[0]['model']
    records = {}
    spec = json.loads(args.training_spec.read_text()) if args.training_spec else None
    arms = spec['arms'] if spec else [dict(amplitude=a, name=f'wuji_bridge3_reset{a}x_cp25_seed20261124_v2',
            gate=f'runs/wuji-goal/diagnostics/reset-range{a}x-training-gate-20260923-v2') for a in [1, 2]]
    for arm in arms:
        amplitude = arm['amplitude']
        folder = args.root/'runs'/arm['name']
        pipeline = json.loads((folder/'pipeline-status.json').read_text())
        assert pipeline['status'] == 'completed'
        assert [s['name'] for s in pipeline['stages']] == ['preflight', 'teacher']
        assert all(s['status'] == 'completed' and s['returncode'] == 0 for s in pipeline['stages'])
        assert pipeline['spec']['epochs'] == 100 and pipeline['spec']['envs_per_rank'] == 5120
        assert pipeline['spec']['source_checkpoint_sha256'] == sha(source)
        preflight_command = pipeline['stages'][0]['command']
        assert 'max_iterations=3' in preflight_command and 'num_envs=5120' in preflight_command
        gate_folder = args.root/arm['gate']
        gate = json.loads((gate_folder/'report.json').read_text())
        gate_status = json.loads((gate_folder/'status.json').read_text())
        assert gate_status['status'] == 'completed' and gate_status['returncode'] == 0
        assert gate['status'] == 'passed' and gate['reset_range_amplitude'] == amplitude
        assert gate['train'] == 3 and gate['test'] == 1 and gate['checks']['loaded_test_rows'] == 0
        assert gate['checks']['transitions'] == 10000 and all(n > 0 for n in gate['checks']['sampled_rows'])
        if pipeline['spec'].get('termination_limits'):
            limits = pipeline['spec']['termination_limits']
            assert gate['termination_limits'] == limits
            assert gate['termination_checks']['environment_steps_checked'] >= 10000
            assert gate['termination_checks']['unexpected_mask_elements'] == 0
            for filename in ['preflight.log', 'teacher.log']:
                log = (folder/filename).read_text()
                for key, value in limits.items():
                    recorded = re.findall(r'^\s*'+re.escape(key)+r':\s*([0-9.eE+-]+)\s*$', log, re.M)
                    assert len(recorded) == 1 and float(recorded[0]) == value, (filename, key, recorded)
        events = EventAccumulator(str(folder/'summaries'), size_guidance={'scalars': 0})
        events.Reload()
        epochs, rates = events.Scalars('info/epochs'), events.Scalars('info/last_lr')
        assert len(epochs) == len(rates) == 100
        assert [e.step for e in epochs] == [i*5120*32 for i in range(1, 101)]
        assert [e.value for e in epochs] == list(range(1, 101))
        assert all(abs(e.value-1e-5) < 1e-10 for e in rates)
        metrics = {k: [dict(step=e.step, value=e.value, wall_time=e.wall_time) for e in events.Scalars(k)]
                   for k in events.Tags()['scalars']}
        assert all(np.isfinite(e['value']) for series in metrics.values() for e in series)
        snapshots = {}
        for cp in [10, 25, 50, 75, 100]:
            path = folder/f'evaluation/inbox/epoch_{cp:06d}.pth'
            snapshot = torch.load(path, map_location='cpu')
            snapshot = snapshot[0] if 0 in snapshot else snapshot
            assert snapshot['epoch'] == cp and snapshot['frame'] == cp*5120*32
            model = snapshot['model']
            assert model.keys() == original.keys()
            assert all(v.shape == original[k].shape and torch.isfinite(v).all() for k, v in model.items())
            mode = pipeline['spec'].get('input_normalizer_mode_preflight')
            if mode == 'frozen':
                assert all(torch.equal(model[k], original[k]) for k in model if k.startswith('running_mean_std.'))
            elif mode == 'adaptive':
                assert model['running_mean_std.count'] > original['running_mean_std.count']
            mean_shift = (model['running_mean_std.running_mean']-original['running_mean_std.running_mean'])
            mean_shift /= original['running_mean_std.running_var'].sqrt()+1e-8
            ratio = (model['running_mean_std.running_var']/original['running_mean_std.running_var']).sqrt()
            keys = [k for k in model if k.startswith('a2c_network.') and 'sigma' not in k]
            parameter_change = sum(float((model[k]-original[k]).double().square().sum()) for k in keys)**.5
            snapshots[str(cp)] = dict(sha256=sha(path), frame=snapshot['frame'], epoch=cp, input_normalizer_mode=mode,
                                     input_normalizer_count=float(model['running_mean_std.count']),
                                     normalized_mean_shift_max=float(mean_shift.abs().max()),
                                     input_std_ratio_min_median_max=torch.quantile(ratio.float(), torch.tensor([0., .5, 1.])).tolist(),
                                     parameter_change_l2=parameter_change,
                                     policy_std_all_groups=model['a2c_network.sigma'].exp().tolist())
        records[arm.get('label', str(amplitude))] = dict(run=arm['name'], reset_range_amplitude=amplitude,
                                       status_sha256=sha(folder/'pipeline-status.json'),
                                       formal_epochs=100, formal_physics_transitions=16384000,
                                       preflight_epochs=3, preflight_physics_transitions=491520,
                                       runtime_gate_physics_transitions=gate['checks']['transitions'],
                                       runtime_gate_report_sha256=sha(gate_folder/'report.json'),
                                       snapshots=snapshots, metrics=metrics,
                                       event_files={p.name: sha(p) for p in (folder/'summaries').glob('*') if p.is_file()})
    result = dict(status='verified_both_training_complete', source_sha256=sha(Path(__file__)),
                  training_spec=str(args.training_spec) if spec else None,
                  original_teacher_sha256=sha(source), arms=records,
                  formal_transitions_total=32768000,
                  scope='Training budgets and finite logs/weights only. Reward and aggregated SAPG KL are not task success or same-policy KL. Normalizer changes are descriptive; frozen counterfactual diagnosis is separate.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], formal_transitions_total=result['formal_transitions_total'])))


if __name__ == '__main__':
    main()
