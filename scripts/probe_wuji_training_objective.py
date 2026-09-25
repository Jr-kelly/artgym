"""Frozen policies under the actual training reset/command distribution.

This diagnostic reports random-command endpoints separately from the existing
fixed-clock development scorer. It neither trains nor changes reward/control.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch
from omegaconf import OmegaConf
from scripts.train_wuji_student_actor import register
from scripts.check_wuji_student_actor_runtime import overrides
from scripts.audit_distillation_runtime import tensor_digest
from isaacgymenvs.distill import reset_done_rnn_states
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['mean', 'sample'], required=True)
    parser.add_argument('--num-envs', type=int, default=5120)
    parser.add_argument('--seed', type=int, default=20261066)
    args = parser.parse_args()
    assert args.num_envs % 5 == 0
    args.output.mkdir(parents=True, exist_ok=False)
    register()
    requested = overrides() + ['test=False', 'task.env.episodeLength=600',
        'task.env.absolutePoseObjective.ramp_epochs=0',
        'task.env.broadGoalReward.coefficient=0.0']
    cfg = configuration('wuji_fixed_student_actor', args.num_envs, requested,
                        train='wujiFixedStudentActorSAPG', seed=args.seed)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, args.checkpoint)
    assert not env.eval_mode
    assert list(cfg.task.env.trainingCommandDurationsSec) == [2.0, 5.0]
    player.model.eval()
    model_before = tensor_digest(player.model.state_dict())
    encoder_before = tensor_digest(env.fixed_student_encoder.state_dict())
    group_size = args.num_envs // 5
    group_ids = torch.linspace(50., 0., 5, device=player.device).repeat_interleave(group_size)
    player.intr_reward_coef_embd[:, 0] = group_ids
    observation = player.env_reset(player.env)
    assert torch.equal(observation[:, -1], group_ids)
    device = env.device
    active = torch.ones(args.num_envs, dtype=torch.bool, device=device)
    stable = active.clone()
    all_tails = active.clone()
    streak = torch.zeros(args.num_envs, dtype=torch.long, device=device)
    commands = torch.zeros_like(streak)
    endpoint_counts = torch.zeros((2, 5, 2), dtype=torch.long, device=device)
    max_drift = torch.zeros(args.num_envs, device=device)
    max_rotation = max_drift.clone()
    total_reward = torch.zeros((600, 5), device=device)
    cohort_reward = torch.zeros((600, 5), device=device)
    component_rows = []
    physics = hashlib.sha256()
    original_reward = env.compute_reward
    step = 0
    reward_error = 0.
    reward_names = ['ObjPosDeviation', 'ObjRotDeviation', 'HandQposDeviation',
        'StableContact', 'GoalDistance1', 'GoalDistance2', 'Smooth', 'Drop',
        'Success', 'Alive', 'AbsolutePoseCost']
    reset_state_before = torch.cat([env.hand_dof_pos, env.object_pos, env.object_rot,
                                    env.obj_dof_pos], dim=1).detach().cpu().numpy()
    np.save(args.output/'initial-physical-state.npy', reset_state_before)
    initial_goal_delta = (env.goal_obj_dof_pos-env.init_obj_dof_pos).detach().cpu().numpy()
    np.save(args.output/'initial-goal-delta.npy', initial_goal_delta)

    def observe_reward(actions):
        nonlocal reward_error
        # These tensors are read after physics, before the inherited command
        # scheduler updates goals. Diagnostic state is independent of the task.
        old_goal = env.goal_obj_dof_pos[:, 0].clone()
        due = env.progress_buf >= env.command_deadline
        opening = old_goal-env.init_obj_dof_pos[:, 0] > .02
        original_reward(actions)
        valid = ~env.debug_reset_cause_fall & ~env.debug_reset_cause_invalid
        error = (env.obj_dof_pos[:, 0]-old_goal).abs()
        reached = valid & torch.isfinite(error) & (error < .002)
        streak.copy_(torch.where(reached, streak+1, torch.zeros_like(streak)))
        drift = torch.linalg.vector_norm(env.object_pos-env.init_object_pos, dim=-1)
        rotation = 2*torch.asin(torch.linalg.vector_norm(
            quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))[:, :3], dim=-1).clamp(0, 1))
        stable.logical_and_(~active | (torch.isfinite(drift) & torch.isfinite(rotation)
                                      & (drift < .01) & (rotation < .25)))
        max_drift.copy_(torch.maximum(max_drift, torch.where(active, drift, 0.)))
        max_rotation.copy_(torch.maximum(max_rotation, torch.where(active, rotation, 0.)))
        complete = due & active & valid
        # A dropped cohort member cannot recover by resetting. Rewards below
        # still include all real training transitions, including later resets.
        all_tails.logical_and_(~complete | (streak >= 9))
        commands.add_(complete.long())
        for kind in range(2):
            selected = complete & (opening == bool(kind))
            endpoint_counts[kind, :, 0].add_(selected.reshape(5, group_size).sum(1))
            endpoint_counts[kind, :, 1].add_((selected & (streak >= 9)).reshape(5, group_size).sum(1))
        total_reward[step] = env.rew_buf.reshape(5, group_size).mean(1)
        cohort_reward[step] = (env.rew_buf*active).reshape(5, group_size).mean(1)
        values = {name:float(env.extras[name]) for name in reward_names}
        delta = abs(sum(values.values())-float(env.rew_buf.mean()))
        reward_error = max(reward_error, delta)
        assert delta < 5e-5, (step, delta, values)
        component_rows.append(values)
        active.logical_and_(valid)
        # Episode length ends exactly at step600. An earlier reset invalidates
        # full-cohort survival rather than replacing the initial trial.
        if step < 599:
            active.logical_and_(env.reset_buf == 0)
        streak.masked_fill_(due | (env.reset_buf != 0), 0)

    env.compute_reward = observe_reward
    try:
        for step in range(600):
            assert torch.equal(observation[:, -1], group_ids)
            action = player.get_action(observation, is_deterministic=args.mode == 'mean')
            assert torch.isfinite(action).all()
            observation, _, done, _ = player.env_step(player.env, action)
            for value in [action, env.hand_dof_pos, env.obj_dof_pos, env.object_pos, env.object_rot]:
                physics.update(value.detach().cpu().contiguous().numpy().tobytes())
            reset_done_rnn_states(player, done)
            if (step+1) % 100 == 0:
                print(json.dumps(dict(step=step+1, active=int(active.sum()))), flush=True)
        model_after = tensor_digest(player.model.state_dict())
        encoder_after = tensor_digest(env.fixed_student_encoder.state_dict())
        assert model_after == model_before and encoder_after == encoder_before
        assert len(component_rows) == 600 and int(commands.max()) > 0
        joint = active & stable & all_tails & (commands > 0)
        report = dict(status='completed', mode=args.mode, seed=args.seed,
            physics_transitions=600*args.num_envs, num_envs=args.num_envs,
            checkpoint=str(args.checkpoint), checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
            model_unchanged=True, encoder_unchanged=True, group_ids=[50., 37.5, 25., 12.5, 0.],
            full_cohort_alive=active.reshape(5, group_size).sum(1).tolist(),
            full_cohort_body_stable=(active & stable).reshape(5, group_size).sum(1).tolist(),
            full_cohort_all_complete_command_tails=joint.reshape(5, group_size).sum(1).tolist(),
            reward_per_transition=total_reward.mean(0).tolist(),
            reward_per_initial_cohort_transition=cohort_reward.mean(0).tolist(),
            weighted_component_mean={key:float(np.mean([r[key] for r in component_rows])) for key in reward_names},
            maximum_reward_component_sum_error=reward_error,
            endpoint_counts_closed_open_group_total_held=endpoint_counts.tolist(),
            physics_action_sha256=physics.hexdigest(),
            scope='Training distribution diagnostic: three training grasps, randomized2/5s durations, all five groups, frozen weights, fullposecost. Completed command tails only; final partial command excluded. Different protocol from fixed20s332 scorer. Not a new blind validation or hardware success.')
        np.savez_compressed(args.output/'metrics.npz', total_reward=total_reward.cpu().numpy(),
            cohort_reward=cohort_reward.cpu().numpy(), commands=commands.cpu().numpy(),
            active=active.cpu().numpy(), stable=stable.cpu().numpy(), all_tails=all_tails.cpu().numpy(),
            max_drift=max_drift.cpu().numpy(), max_rotation=max_rotation.cpu().numpy())
        (args.output/'reward-components.json').write_text(json.dumps(component_rows)+'\n')
        (args.output/'source.py').write_bytes(Path(__file__).read_bytes())
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report), flush=True)
    finally:
        env.compute_reward = original_reward
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
