"""Exercise actual training timeout and clock boundaries at 20s and 60s.

The progress counter is explicitly advanced near each boundary for this wiring
check. It is not a long-trajectory success test. The independent 60s evaluator
records real uninterrupted physics separately.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maximum', type=int, choices=[600, 1800], required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    root = Path(__file__).resolve().parents[1]
    records = []
    for maximum in [args.maximum]:
        cfg = configuration('wuji_acquisition_bridge_hemisphere', 12,
            ['hand=wuji_paper_official_actuator', 'object=knife_wuji_bridge2_20260922',
             'test=False', 'object.reward.GoalDistance2=5.0',
             'task.env.episodeLength=' + str(maximum)], train='wujiAcquisitionSAPG', seed=20261043)
        (args.output / ('config' + str(maximum) + '.yaml')).write_text(OmegaConf.to_yaml(cfg, resolve=True))
        env = make_env(cfg)
        original = env.compute_reward
        captured = []

        def reward(actions):
            expected_timeout = env.progress_buf >= maximum
            assert torch.equal(env.debug_reset_cause_timeout, expected_timeout)
            goals, deadlines = env.goal_obj_dof_pos.clone(), env.command_deadline.clone()
            original(actions)
            due = (env.progress_buf >= deadlines) & (env.reset_buf == 0)
            assert torch.equal((goals != env.goal_obj_dof_pos).any(-1), due)
            captured.append(dict(progress=env.progress_buf.cpu().tolist(), timeout=expected_timeout.cpu().tolist(),
                                 switch=due.cpu().tolist(), fall=env.debug_reset_cause_fall.cpu().tolist()))

        env.compute_reward = reward
        try:
            assert not env.eval_mode and env.max_episode_length == maximum
            assert cfg.task.env.initialPoseNoise.ramp_epochs == 0
            for handle, actor in zip(env.envs, env.object_handles):
                prop = env.gym.get_actor_dof_properties(handle, actor)
                assert np.allclose(prop['damping'], .3) and np.all(prop['stiffness'] == 0)
                hand = env.gym.find_actor_handle(handle, 'hand')
                prop = env.gym.get_actor_dof_properties(handle, hand)
                for key in ['stiffness', 'damping', 'armature']:
                    assert np.allclose(prop[key], cfg.hand.dof_props[key], rtol=1e-6, atol=1e-7)
            env.reset()
            for _ in range(50):
                env.step(env.zero_actions())
                assert torch.isfinite(env.obs_buf).all() and torch.isfinite(env.rew_buf).all()
            env.progress_buf[:] = torch.tensor([598, 599, 1799], device=env.device).repeat_interleave(4)
            env.command_deadline[:] = env.progress_buf + 1
            env.step(env.zero_actions())
            boundary = captured[-1]
            assert boundary['progress'] == [599] * 4 + [600] * 4 + [1800] * 4
            expected = [False] * 4 + [maximum == 600] * 4 + [True] * 4
            assert boundary['timeout'] == expected
            assert sum(boundary['fall']) == 0
            assert boundary['switch'] == [not value for value in expected]
            assert torch.equal(env.progress_buf == 0, torch.tensor(expected, device=env.device))
            records.append(dict(maximum=maximum, physical_transitions=51 * 12, boundary=boundary))
        finally:
            env.gym.destroy_sim(env.sim)
    files = ['scripts/check_wuji_bridge_episode_duration.py', 'isaacgymenvs/tasks/wuji_bridge_hemisphere.py', 'isaacgymenvs/cfg/task/wuji_acquisition_bridge_hemisphere.yaml', 'isaacgymenvs/tasks/artmanip.py',
             'isaacgymenvs/tasks/wuji_acquisition.py', 'isaacgymenvs/tasks/wuji_variable_timed_acquisition.py',
             'isaacgymenvs/cfg/task/wuji_acquisition_official_variable_timed.yaml']
    report = dict(status='passed', scope=__doc__, records=records,
                  sources={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files})
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
