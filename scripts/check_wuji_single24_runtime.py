"""Check training-only resets and legal actions for the new five-second case."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
from isaacgymenvs.tasks.artmanip import ArtManip
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    name = 'knife_wuji_functional_single24_20260922'
    manifest_path = root / 'runs/wuji-goal/functional-single24-dataset-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for path, digest in manifest['artifact_sha256'].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
    train = np.load(root / 'caches/initial_grasp/wuji' / name / '000/train/valid_grasps.npy')
    cfg = configuration('wuji_acquisition_official_timed5', 50,
        ['object=' + name, 'hand=wuji_paper_official_actuator', 'test=False', 'object.reward.GoalDistance2=5.0'],
        train='wujiAcquisitionSAPG', seed=20261027)
    (args.output / 'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    original_sample = ArtManip.sample_grasps
    checks = dict(sampled_rows=[0], transitions=0, clock_switches=0, action_mapping_calls=0)

    def sample(env, ids):
        rows = original_sample(env, ids)
        assert torch.equal(rows, torch.as_tensor(train, device=rows.device).expand(len(rows), -1))
        checks['sampled_rows'][0] += len(rows)
        return rows

    ArtManip.sample_grasps = sample
    env = make_env(cfg)
    original_mapping = env.actions_to_targets
    original_reward = env.compute_reward

    def mapping(actions):
        targets = original_mapping(actions)
        expected = env.init_targets[:, :20] + actions * .04
        expected[:, 16:] = env.prev_targets[:, 16:20] + .025 * actions[:, 16:]
        expected = torch.maximum(torch.minimum(expected, env.hand_dof_upper_limits), env.hand_dof_lower_limits)
        assert torch.equal(targets, expected)
        checks['action_mapping_calls'] += 1
        return targets

    def reward(actions):
        goals = env.goal_obj_dof_pos.clone()
        original_reward(actions)
        due = (env.progress_buf > 0) & (env.progress_buf % 150 == 0) & (env.reset_buf == 0)
        assert torch.equal((goals != env.goal_obj_dof_pos).any(-1), due)
        checks['clock_switches'] += int(due.sum())

    env.actions_to_targets = mapping
    env.compute_reward = reward
    try:
        assert not env.eval_mode and env.runtime_grasp_split == 'train'
        assert np.isclose(env.dt * env.control_freq_inv, 1 / 30)
        assert len(env.all_valid_states) == 1 and len(env.all_test_valid_states) in [0, 2]
        assert cfg.task.env.commandPeriodSec == 5 and cfg.object.reward.GoalDistance2 == 5
        assert not cfg.task.task.randomize and not cfg.object.randomization.randomize
        for handle, actor in zip(env.envs, env.object_handles):
            hand = env.gym.find_actor_handle(handle, 'hand')
            props = env.gym.get_actor_dof_properties(handle, hand)
            for key in ['stiffness', 'damping', 'armature']:
                assert np.allclose(props[key], cfg.hand.dof_props[key], rtol=1e-6, atol=1e-7)
            props = env.gym.get_actor_dof_properties(handle, actor)
            assert np.allclose(props['damping'], .3) and np.all(props['stiffness'] == 0)
        env.reset()
        for step in range(200):
            actions = env.zero_actions() if step < 175 else (torch.rand((50, 20), device=env.device) * 2 - 1) * .1
            env.step(actions)
            assert torch.isfinite(env.obs_buf).all() and torch.isfinite(env.rew_buf).all()
            checks['transitions'] += 50
        assert checks['transitions'] == 10000 and checks['clock_switches'] > 0
        sources = ['scripts/check_wuji_single24_runtime.py', 'isaacgymenvs/tasks/artmanip.py',
                   'isaacgymenvs/tasks/wuji_acquisition.py', 'isaacgymenvs/tasks/wuji_timed_acquisition.py',
                   'isaacgymenvs/cfg/task/wuji_acquisition_official_timed5.yaml',
                   'isaacgymenvs/cfg/object/' + name + '.yaml', str(manifest_path.relative_to(root))]
        sources += list(manifest['artifact_sha256'])
        result = dict(status='passed', scope=__doc__, dataset=name, train=1, test=2, checks=checks,
                      full_reset_noise=OmegaConf.to_container(cfg.task.env.initialPoseNoise),
                      sources={path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in sources})
        (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        ArtManip.sample_grasps = original_sample
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
