"""Exercise actual training resets at a declared range before PPO starts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from scripts import check_wuji_bridge3_hemisphere_runtime as base
from isaacgymenvs.tasks import wuji_reset_randomization as randomization
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--amplitude', type=int, choices=[1, 2], required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    configure, perturb = base.configuration, randomization.perturb_states
    checks = dict(calls=0, rows=0, joint_max=0., position_max=0., rotation_vector_max=0.)
    limits = dict(joint_max=.01*args.amplitude, position_max=.0005*args.amplitude,
                  rotation_vector_max=.008726646259971648*args.amplitude)

    def configuration(task, count, overrides, **kwargs):
        overrides = list(overrides)+[
            f'task.env.initialPoseNoise.position_m={limits["position_max"]}',
            f'task.env.initialPoseNoise.joint_rad={limits["joint_max"]}',
            f'task.env.initialPoseNoise.rotation_vector_rad={limits["rotation_vector_max"]}',
            'task.env.initialPoseNoise.ramp_epochs=0']
        return configure(task, count, overrides, **kwargs)

    def checked(states, lower, upper, delta, translation, rotvec, fk):
        for name, tensor in [('joint_max', delta), ('position_max', translation), ('rotation_vector_max', rotvec)]:
            actual = float(tensor.abs().max())
            assert actual <= limits[name]+1e-8
            checks[name] = max(checks[name], actual)
        result = perturb(states, lower, upper, delta, translation, rotvec, fk)
        assert torch.isfinite(result).all() and result.shape == states.shape
        assert torch.allclose(result[:, 40:43]-states[:, 40:43], translation, atol=1e-7, rtol=0)
        expected = torch.maximum(torch.minimum(states[:, :20]+delta, upper), lower)
        assert torch.equal(result[:, :20], expected)
        checks['calls'] += 1
        checks['rows'] += len(states)
        return result

    base.configuration, randomization.perturb_states = configuration, checked
    oldargv = sys.argv
    try:
        sys.argv = [oldargv[0], '--output', str(args.output)]
        base.main()
        assert checks['calls'] > 0 and checks['rows'] >= 80
        assert all(checks[key] > .9*limit for key, limit in limits.items())
        path = args.output/'report.json'
        report = json.loads(path.read_text())
        report.update(reset_range_amplitude=args.amplitude, reset_range_checks=checks, reset_range_limits=limits)
        report['sources'].update({name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                                 ['scripts/check_wuji_reset_training_range.py', 'isaacgymenvs/tasks/wuji_reset_randomization.py']})
        path.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(dict(status='passed', reset_range_amplitude=args.amplitude, checks=checks)), flush=True)
    finally:
        sys.argv = oldargv
        base.configuration, randomization.perturb_states = configure, perturb


if __name__ == '__main__':
    main()
