"""Check declared termination masks during the real 10,000-transition reset gate."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import check_wuji_reset_training_range as base
from isaacgymenvs.tasks.artmanip import ArtManip
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--amplitude', type=int, choices=[2], required=True)
    parser.add_argument('--termination', choices=['native', 'strict'], required=True)
    args = parser.parse_args()
    limits = dict(pos_devia_threshold=.05 if args.termination == 'native' else .01,
                  rot_devia_threshold=1.57 if args.termination == 'native' else .25)
    configure, get_dones = base.base.configuration, ArtManip._get_dones
    checks = dict(calls=0, environment_steps_checked=0, native_fall_elements=0,
                  strict_pose_violation_elements=0, unexpected_mask_elements=0)

    def configuration(task, count, overrides, **kwargs):
        return configure(task, count, list(overrides)+[
            'object.task.'+key+'='+str(value) for key, value in limits.items()], **kwargs)

    def checked(env):
        assert not env.eval_mode
        assert all(env.object_cfg['task'][key] == value for key, value in limits.items())
        get_dones(env)
        displacement = torch.linalg.vector_norm(env.object_pos-env.init_object_pos, dim=-1)
        relative = quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))
        angle = 2 * torch.asin(torch.linalg.vector_norm(relative[:, :3], dim=-1).clamp(max=1))
        expected = (displacement > limits['pos_devia_threshold']) | (angle > limits['rot_devia_threshold'])
        mismatch = (env.debug_reset_cause_fall != expected).sum()
        checks['unexpected_mask_elements'] += int(mismatch)
        assert not mismatch
        assert torch.equal(env.truncated_envs, expected | env.debug_reset_cause_invalid)
        checks['calls'] += 1
        checks['environment_steps_checked'] += env.num_envs
        checks['native_fall_elements'] += int(expected.sum())
        checks['strict_pose_violation_elements'] += int(((displacement >= .01) | (angle >= .25)).sum())

    base.base.configuration, ArtManip._get_dones = configuration, checked
    argv = sys.argv
    try:
        sys.argv = [argv[0], '--output', str(args.output), '--amplitude', str(args.amplitude)]
        base.main()
        assert checks['environment_steps_checked'] >= 10000
        path = args.output/'report.json'
        report = json.loads(path.read_text())
        report.update(termination_limits=limits, termination_checks=checks,
                      termination_scope='Training only. Native comparator remains >; evaluation remains '
                      'unchanged, scoring strict <. Boundary equality has zero width under continuous noise.')
        report['sources']['scripts/check_wuji_termination_training.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        path.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(dict(status='passed', limits=limits, checks=checks)), flush=True)
    finally:
        sys.argv = argv
        base.base.configuration, ArtManip._get_dones = configure, get_dones


if __name__ == '__main__':
    main()
