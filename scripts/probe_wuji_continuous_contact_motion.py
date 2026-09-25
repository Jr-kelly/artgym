"""Test training-grasp IK paths with free-object physics and legal hand commands.

This is a scripted contact-feasibility diagnostic, never an RL policy result.
Use all training rows with a complete path in the frozen continuity report;
report unattempted rows separately. No held-out rows are executed. Keep the
actual initial joint target preload, add continuous thumb joint displacements,
and pass rate-limited actions through the existing learned-action control path.
The knife receives no commanded motion, mid-rollout reset or stabilizing force;
its zero-stiffness passive damping stays unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
from scripts.wuji_timed_command_metrics import score_timed_trace
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output / 'report.json').exists()
    root = Path(__file__).resolve().parents[1]
    name = 'knife_wuji_lowgain_functional27_20260922'
    source = root / 'runs/wuji-goal/diagnostics/functional27-continuity.json'
    continuity = json.loads(source.read_text())
    state_file = root / 'caches/initial_grasp/wuji' / name / '000/train/valid_grasps.npy'
    assert hashlib.sha256(state_file.read_bytes()).hexdigest() == continuity['sources'][str(state_file.relative_to(root))]
    candidates = [row for row in continuity['records'] if row['split'] == 'train']
    chosen = [row for row in candidates if row['continuous']['passed']]
    states = np.load(state_file)[[row['dataset_row'] for row in chosen]]
    paths = np.asarray([row['continuous']['thumb_path_rad'] for row in chosen], dtype=np.float32)
    assert paths.shape == (23, 81, 4)
    assert np.allclose(paths[:, 0], states[:, 16:20], rtol=0, atol=1e-7)
    cfg = configuration('wuji_acquisition_official_timed2', len(states),
                        ['hand=wuji_paper_official_actuator', 'object=' + name,
                         'test=True', 'task.env.episodeLength=600'],
                        train='wujiAcquisitionSAPG', seed=20261024)
    (args.output / 'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env = make_env(cfg)
    frames = []
    try:
        assert not env.randomize and not cfg.object.randomization.randomize
        assert cfg.task.env.actionsMovingAverage == 1. and not cfg.task.env.useRelativeControl
        assert np.isclose(env.dt * env.control_freq_inv, 1 / 30)
        assert cfg.task.env.thumbActionStep == .025
        for handle, actor in zip(env.envs, env.object_handles):
            props = env.gym.get_actor_dof_properties(handle, actor)
            assert np.all(props['stiffness'] == 0), 'Knife must remain passive'
            assert np.allclose(props['damping'], .3)
            hand = env.gym.find_actor_handle(handle, 'hand')
            props = env.gym.get_actor_dof_properties(handle, hand)
            for key in ['stiffness', 'damping', 'armature']:
                assert np.allclose(props[key], cfg.hand.dof_props[key], rtol=1e-6, atol=1e-7)
        env.configure_fixed_grasp_consecutive_evaluation('000', states[0],
            goal_sequence=tuple(cfg.object.task.goals), episodes_per_grasp=len(states))
        env.eval_grasp_states[:] = torch.as_tensor(states, device=env.device)
        env.success_hold_duration = 1e9
        env.eval_goal_timeout = 0.
        original = env.compute_reward

        def capture(actions):
            active = env.eval_active_mask.clone()
            goal = env.goal_obj_dof_pos[:, 0].clone()
            expected = env.init_obj_dof_pos[:, 0] + env.eval_goal_sequence[(len(frames) // 150) % 2, 0]
            assert torch.equal(goal[active], expected[active])
            original(actions)
            assert not env.goal_achieved_step.any()
            angle = 2 * torch.asin(torch.norm(quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))[:, :3], dim=-1).clamp(0, 1))
            row = dict(active=active, goal=goal, slider=env.obj_dof_pos[:, 0],
                       drift=torch.norm(env.object_pos - env.init_object_pos, dim=-1), rotation=angle,
                       fall=env.debug_reset_cause_fall, invalid=env.debug_reset_cause_invalid,
                       q=env.hand_dof_pos, target=env.cur_targets[:, :20], action=env.actions,
                       contact=env.contact_info)
            frames.append({key: value.detach().cpu().numpy().copy() for key, value in row.items()})
            if len(frames) % 150 == 0 and len(frames) < 600:
                ids = active.nonzero(as_tuple=False).squeeze(-1)
                env._set_eval_goal_targets(ids, (len(frames) // 150) % 2)

        env.compute_reward = capture
        env.reset()
        path = torch.as_tensor(paths, device=env.device)
        initial_targets = env.init_targets[:, :20].clone()
        largest_requested_action = 0.
        for step in range(600):
            if env.is_grasp_evaluation_complete():
                break
            phase = (step // 150) % 2
            progress = min((step % 150 + 1) / 90., 1.) * 40
            low = min(int(progress), 40)
            high = min(low + 1, 40)
            fraction = progress - low
            offset = 40 * phase
            nominal = path[:, offset + low] * (1 - fraction) + path[:, offset + high] * fraction
            targets = initial_targets.clone()
            targets[:, 16:] += nominal - path[:, 0]
            raw_actions = env.targets_to_actions(targets)
            largest_requested_action = max(largest_requested_action, float(raw_actions.abs().max()))
            actions = raw_actions.clamp(-1, 1)
            assert torch.count_nonzero(actions[:, :16]) == 0
            env.step(actions)
            if (step + 1) % 150 == 0:
                print(json.dumps(dict(step=step+1, active=int(env.eval_active_mask.sum()))), flush=True)
        trace = {key: np.stack([row[key] for row in frames]) for key in frames[0]}
        np.savez_compressed(args.output / 'trace.npz', **trace)
        report = score_timed_trace(trace, 150, 9, 600)
        report.update(scope=__doc__, source_training_rows=[row['dataset_row'] for row in chosen],
                      unattempted_training_rows=[row['dataset_row'] for row in candidates if not row['continuous']['passed']],
                      total_training_candidates=27, heldout_rows_executed=0, stage_seconds=5,
                      motion_seconds=3, hold_seconds=2, largest_requested_action=largest_requested_action,
                      actions_clipped_to_legal_range=True, initial_preload_preserved=True,
                      continuity_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      initial_states_sha256=hashlib.sha256(state_file.read_bytes()).hexdigest(),
                      source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output / 'source.py').write_bytes(Path(__file__).read_bytes())
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({key: value for key, value in report.items() if key not in ['records', 'scope']}), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
