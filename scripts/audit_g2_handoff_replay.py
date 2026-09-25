"""Replay frozen B/C policy inference on recorded continuous physical states.

This is an offline interface audit, never a new physical success trial. It checks
the actual 50-frame history, one RNN reset, fixed initialization, action mapping,
and (for C) independence from live object truth after ideal initialization.
"""
import argparse
import hashlib
import json
from pathlib import Path

from isaacgym import gymapi  # Isaac Gym must be imported before torch.
import numpy as np
from omegaconf import OmegaConf

from scripts.g2_frozen_policy import FrozenPolicy
from scripts.g2_kinematics import transform


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path(__file__).resolve().parents[1]
    report = json.loads((args.trial / 'report.json').read_text())
    takeover = json.loads((args.trial / 'takeover.json').read_text())
    physics = json.loads((args.trial / 'physics.json').read_text())
    process = json.loads(args.trial.with_name(args.trial.name + '-process.json').read_text())
    source = json.loads((Path(process['pin']) / 'SOURCE_SHA256.json').read_text())
    checked = {}
    for name in ['scripts/g2_frozen_policy.py', 'scripts/g2_kinematics.py',
                 'scripts/wuji_kinematics.py', 'scripts/wuji_knife_frame.py',
                 'scripts/wuji_quaternion_hemisphere.py',
                 'isaacgymenvs/deploy/wuji/acquisition_control.py']:
        checked[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert checked[name] == source[name], ('Audit source differs from trial', name)
    assert report['group'] in ['B', 'C']
    trace = np.load(args.trial / 'trace.npz')
    operation = np.flatnonzero(trace['phase'] == 'operate')
    assert len(operation) and operation[0] == takeover['step']
    first = int(operation[0])
    assert first >= 50
    cfg = OmegaConf.load(args.trial / 'frozen-config.yaml')
    policy = FrozenPolicy(cfg, Path(report['args']['teacher']),
                          Path(report['args']['student']) if report['group'] == 'C' else None)
    for i in range(first - 50, first):
        policy.record(trace['q'][i], trace['action'][i])
    def state(i):
        return (trace['q'][i],
                transform(trace['wrist'][i, :3], trace['wrist'][i, 3:]),
                transform(trace['object'][i, :3], trace['object'][i, 3:]),
                transform(trace['slider_pose'][i, :3], trace['slider_pose'][i, 3:]),
                float(trace['slider'][i]))
    q, wrist, obj, link, slider = state(first - 1)
    assert np.max(np.abs(q - takeover['q'])) < 1e-7
    assert np.max(np.abs(trace['targets'][first - 1, physics['hand_indices']] - takeover['targets'])) < 1e-7
    policy.takeover(q, takeover['targets'], wrist, obj, link, takeover['slider_command_origin'])
    policy.previous_slider = slider
    fixed_init = policy.init.copy()
    fixed_targets = policy.control.initial_targets.copy()
    errors = dict(action=0., observation=0., hand_motor_target=0., live_truth_invariance=0.)
    for frame, i in enumerate(operation):
        q, wrist, obj, link, slider = state(i - 1)
        goal = .04 if (frame // 150) % 2 == 0 else 0.
        assert abs(trace['goal'][i] - (takeover['slider_command_origin'] + goal)) < 1e-7
        if policy.student:
            expected = policy.observation(q, wrist, obj, link, slider, goal).clone()
            encoder = policy.player.model.a2c_network.actor_encoder_obs_override.clone()
            false_obj = obj.copy()
            false_obj[:3, 3] += [10., -20., 30.]
            perturbed = policy.observation(q, wrist, false_obj, false_obj, 123., goal)
            errors['live_truth_invariance'] = max(errors['live_truth_invariance'],
                float((expected - perturbed).abs().max()),
                float((encoder - policy.player.model.a2c_network.actor_encoder_obs_override).abs().max()))
        target, action, observation = policy.step(q, wrist, obj, link, slider, goal)
        errors['action'] = max(errors['action'], float(np.max(np.abs(action - trace['action'][i]))))
        errors['observation'] = max(errors['observation'], float(np.max(np.abs(observation - trace['observation'][i]))))
        errors['hand_motor_target'] = max(errors['hand_motor_target'],
            float(np.max(np.abs(target - trace['targets'][i, physics['hand_indices']]))))
        policy.record(trace['q'][i], action)
        assert np.array_equal(policy.init, fixed_init)
        assert np.array_equal(policy.control.initial_targets, fixed_targets)
    result = dict(trial=args.trial.name, audit='offline frozen-policy replay, not a physical trial',
        trace_sha256=hashlib.sha256((args.trial / 'trace.npz').read_bytes()).hexdigest(),
        inference_frames=len(operation), max_absolute_errors=errors,
        history_frames=50, history_phases=list(dict.fromkeys(trace['phase'][first - 50:first].tolist())),
        history_actions_zero=bool((trace['action'][first - 50:first] == 0).all()),
        rnn_resets=1, initial_observation_fixed=True, motor_reference_fixed=True,
        external_clock_seconds=5, student_initialization=takeover['student_initialization'],
        audit_source_sha256=checked,
        passed=bool(errors['action'] < 1e-5 and errors['observation'] < 1e-5 and
                    errors['hand_motor_target'] < 1e-5 and errors['live_truth_invariance'] == 0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert result['passed'], errors


if __name__ == '__main__':
    main()
