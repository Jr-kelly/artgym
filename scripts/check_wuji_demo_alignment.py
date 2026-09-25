"""Replay the known motion through the RL action interface before training.

The trajectory is read only by this diagnostic, never by the RL environment.
"""
import argparse
import json
from pathlib import Path

import isaacgym  # noqa: F401: must precede torch
import numpy as np
import torch
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
import yaml

import isaacgymenvs
from scripts.wuji_kinematics import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', choices=['replay', 'hold'], default='replay')
    parser.add_argument('--task', default='wuji_demo_aligned')
    parser.add_argument('--num-envs', type=int, default=1)
    parser.add_argument('--pipeline', choices=['cpu', 'gpu'], default='gpu')
    parser.add_argument('--seconds', type=float, default=12.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    isaacgymenvs.register_omegaconf_resolvers()
    with initialize_config_dir(version_base='1.1', config_dir=str(ROOT / 'isaacgymenvs/cfg')):
        cfg = compose(config_name='config', overrides=[
            f'task={args.task}', 'hand=wuji_paper', 'object=knife_wuji_demo_aligned',
            'train=wujiDemoAlignedSAPG', f'num_envs={args.num_envs}', 'headless=True',
            f'pipeline={args.pipeline}', 'graphics_device_id=-1', 'force_render=False',
            'num_subscenes=0', 'seed=20260921',
            # Keep the full reference motion visible after the first open/close.
            'task.env.maxConsecutiveSuccesses=20',
            f'task.env.episodeLength={round(args.seconds*120)+1}',
            f'task.env.goalSwitchTimeoutSec={args.seconds+0.1}',
        ])
    (args.output / 'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env = isaacgymenvs.make(seed=cfg.seed, task=cfg.task.name, num_envs=args.num_envs,
                          sim_device=cfg.sim_device, rl_device=cfg.rl_device,
                          graphics_device_id=-1, headless=True, force_render=False, cfg=cfg)
    try:
        env.reset()
        preset = yaml.safe_load((ROOT / 'assets/demo/wuji_knife/fingertip_preset.yaml').read_text())
        waypoints = np.asarray(preset['joint_waypoints_rad'])
        zero = torch.zeros((args.num_envs, 20), device=env.device)
        torch.testing.assert_close(env.actions_to_targets(zero), env.init_targets[:, :20])
        for q in [env.hand_dof_lower_limits, env.hand_dof_upper_limits,
                  torch.as_tensor(waypoints[20, 1:], device=env.device, dtype=torch.float32)]:
            q = q.expand(args.num_envs, -1)
            a = env.targets_to_actions(q)
            if torch.any(a.abs() > 1.00001):
                raise ValueError('Reference action exceeds the policy action range')
            torch.testing.assert_close(env.actions_to_targets(a), q, atol=1e-6, rtol=0)
        max_drift = torch.zeros(args.num_envs, device=env.device)
        max_slider = torch.zeros_like(max_drift)
        reward_sum = torch.zeros_like(max_drift)
        stages = torch.zeros_like(max_drift)
        resets = torch.zeros_like(max_drift)
        samples = []
        terms = {}
        for step in range(round(args.seconds * 120)):
            t = step / 120.0
            actions = zero
            if args.controller == 'replay':
                q = np.array([np.interp(t, waypoints[:, 0], waypoints[:, j+1]) for j in range(20)])
                q = torch.as_tensor(q, device=env.device, dtype=torch.float32).expand(args.num_envs, -1)
                actions = env.targets_to_actions(q)
            obs, reward, done, info = env.step(actions)
            if not torch.isfinite(obs['obs']).all() or not torch.isfinite(reward).all():
                raise ValueError('Non-finite observations or rewards')
            slider = env.obj_dof_pos[:, 0]
            drift = torch.norm(env.object_pos - env.init_object_pos, dim=-1)
            max_drift = torch.maximum(max_drift, drift)
            max_slider = torch.maximum(max_slider, slider)
            reward_sum += reward.to(env.device)
            stages += env.goal_achieved_step
            resets += done.to(env.device)
            for key in env.reward_scales:
                terms[key] = terms.get(key, 0.0) + float(info[key])
            if step % 12 == 0:
                samples.append(torch.stack([slider, drift], dim=-1).cpu().numpy())
        rows = []
        final_slider = env.obj_dof_pos[:, 0].cpu().numpy()
        for i in range(args.num_envs):
            rows.append(dict(env=i, max_slider_m=float(max_slider[i]), final_slider_m=float(final_slider[i]),
                             max_drift_m=float(max_drift[i]), stage_completions=int(stages[i]),
                             reset_count=int(resets[i]), episode_reward=float(reward_sum[i]),
                             passed=bool(max_slider[i] >= .035 and final_slider[i] <= .005
                                         and max_drift[i] <= .015 and resets[i] == 0 and stages[i] >= 2)))
        object_props = env.gym.get_actor_dof_properties(env.envs[0], env.object_handles[0])
        result = dict(controller=args.controller, unique_initial_grasps=1, num_envs=args.num_envs,
                      pipeline=args.pipeline, physics_device='GPU PhysX', control_hz=120,
                      absolute_position_targets=True, hand_joints_controlled=20,
                      randomization=env.randomize, force_scale=env.force_scale, joint_noise=env.joint_noise,
                      object_dof_props={k:object_props[k].tolist() for k in ['stiffness','damping','friction','armature']},
                      reward_term_sums_mean=terms, environments=rows,
                      passed_environments=sum(row['passed'] for row in rows),
                      validation_overrides='Longer termination budget only, to observe the full 12 s reference')
        (args.output / 'report.json').write_text(json.dumps(result, indent=2))
        np.savez_compressed(args.output / 'rollout.npz', slider_and_drift=np.asarray(samples))
        print(json.dumps(result, indent=2))
        if args.controller == 'replay' and not all(row['passed'] for row in rows):
            raise SystemExit('Reference replay failed: do not launch training before resolving alignment')
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
