"""Verify fixed-student PPO wiring against the existing distilled actor in physics."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration, make_player
import torch
from omegaconf import OmegaConf
from rl_games.algos_torch import models
from isaacgymenvs.learning.a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from isaacgymenvs.distill import reset_done_rnn_states
from scripts.audit_distillation_runtime import tensor_digest
from scripts.train_wuji_student_actor import register

STUDENT = 'runs/wuji-goal/frozen-candidates/student-bridge3-replay-seed60-cp25/student.pth'
STUDENT_SHA = '0d2480657bf6176d32c379743f68402aba67aa868bea54b112bbc1bc34142b17'
TEACHER = 'runs/wuji-goal/frozen-candidates/teacher-bridge3-functionalinit-seed45-cp25/teacher.pth'


def overrides():
    return ['hand=wuji_paper_official_actuator', 'object=knife_wuji_bridge3_20260922',
            'task.env.fixedStudentArtifact=' + STUDENT, 'task.env.fixedStudentSha256=' + STUDENT_SHA,
            'object.reward.GoalDistance2=5.0', 'task.env.absolutePoseObjective.coefficient=1.0']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=600)
    parser.add_argument('--broad-goal-coefficient', type=float, default=0.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assert not (args.output/'report.json').exists()
    register()
    root = Path(__file__).resolve().parents[1]
    requested = overrides() + ['task.env.broadGoalReward.coefficient='+str(args.broad_goal_coefficient)]
    cfg = configuration('wuji_fixed_student_actor', 32, requested, train='wujiFixedStudentActorSAPG', seed=20261062)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    env, player = make_player(cfg, root/TEACHER)
    player.model.eval()
    assert player.model.running_mean_std.running_mean.shape == (137,)
    network = copy.deepcopy(player.model.a2c_network)
    network.__class__ = A2CSAPGPrivBuilder.Network
    reference = models.ModelA2CContinuousLogStd.Network(network, obs_shape=(138,), normalize_value=True,
                                                       normalize_input=True, value_size=1, extra_info_start_idx=137)
    reference.load_state_dict(player.model.state_dict())
    reference.a2c_network.priv_encoder = copy.deepcopy(env.fixed_student_encoder)
    reference.to(player.device).eval()
    ref_player = copy.copy(player)
    ref_player.model = reference
    ref_player.obs_shape = (138,)
    start_model = tensor_digest(player.model.state_dict())
    start_encoder = tensor_digest(env.fixed_student_encoder.state_dict())
    checks = dict(transitions=0, matched_actions=0, actor_privileged_invariance=0,
                  critic_changed=0, sampled_rows=[0, 0, 0], max_legacy_clip_excess=0.)
    records = []
    physical_digest = hashlib.sha256()
    reward_checks = dict(transitions=0, command_switches=0, max_error=0.0)
    from isaacgymenvs.tasks.wuji_bridge3_hemisphere import WujiBridge3Hemisphere
    original_reward = WujiBridge3Hemisphere.compute_reward
    captured = {}

    def capture_reward(self, actions):
        old_goal = self.goal_obj_dof_pos.clone()
        error = torch.norm(self.obj_dof_pos-old_goal, p=1, dim=-1)
        valid = ~self.truncated_envs & torch.isfinite(error)
        if self.eval_mode:
            valid &= self.eval_active_mask
        expected = args.broad_goal_coefficient * torch.exp(-(error/.01).square())
        expected = torch.where(valid, expected, torch.zeros_like(expected))
        original_reward(self, actions)
        captured['base'] = self.rew_buf.clone()
        captured['expected'] = expected
        reward_checks['command_switches'] += int((old_goal != self.goal_obj_dof_pos).any(-1).sum())

    WujiBridge3Hemisphere.compute_reward = capture_reward

    def forbidden(*unused):
        raise AssertionError('Unused teacher actor encoder was invoked')

    hook = player.model.a2c_network.priv_encoder.register_forward_pre_hook(forbidden)
    obs = player.env_reset(player.env)
    try:
        for step in range(args.steps):
            incoming = [x.clone() for x in player.states]
            inputs = env.get_student_encoder_observations()
            expected = torch.cat([env.proprioception_buf.reshape(32, -1), env._get_init_obs()], dim=-1)
            assert torch.equal(inputs, expected) and inputs.shape == (32, 2055)
            assert torch.equal(obs[:, 137:153], env.fixed_student_encoder(inputs))
            with torch.no_grad():
                action = player.get_action(obs, is_deterministic=True)
                outgoing = [x.clone() for x in player.states]
                with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
                    ref_player.states = [x.clone() for x in incoming]
                    reference.a2c_network.actor_encoder_obs_override = inputs
                    old_obs = torch.cat([obs[:, :137], obs[:, 153:154]], dim=1)
                    old_action = ref_player.get_action(old_obs, is_deterministic=True)
                    assert torch.equal(action, old_action), float((action-old_action).abs().max())
                    assert all(torch.equal(a, b) for a, b in zip(outgoing, ref_player.states))
                    checks['matched_actions'] += env.num_envs
                    bad_obs = obs.clone()
                    bad_obs[:, 111:137] = torch.randn_like(bad_obs[:, 111:137])*10 + 25
                    player.states = [x.clone() for x in incoming]
                    bad_action = player.get_action(bad_obs, is_deterministic=True)
                    assert torch.equal(action, bad_action)
                    assert all(torch.equal(a, b) for a, b in zip(outgoing[:2], player.states[:2]))
                    checks['critic_changed'] += int(any(not torch.equal(a, b) for a, b in zip(outgoing[2:], player.states[2:])))
                    checks['actor_privileged_invariance'] += env.num_envs
                player.states = outgoing
            distances = (env.init_hand_dof_pos[:, None, :] - env.all_valid_states[None, :, :20]).abs().amax(-1)
            best, row = distances.min(-1)
            assert (best < .011).all()
            checks['sampled_rows'] = [a+b for a, b in zip(checks['sampled_rows'], torch.bincount(row, minlength=3).tolist())]
            obs, _, done, _ = player.env_step(player.env, action)
            actual = env.rew_buf-captured['base']
            error = float((actual-captured['expected']).abs().max())
            assert torch.allclose(actual, captured['expected'], atol=2e-5, rtol=2e-5), error
            if args.broad_goal_coefficient == 0:
                assert torch.equal(env.rew_buf, captured['base'])
            reward_checks['max_error'] = max(reward_checks['max_error'], error)
            reward_checks['transitions'] += env.num_envs
            for value in [action, env.hand_dof_pos, env.object_pos, env.object_rot,
                          env.obj_dof_pos, env.cur_targets, done, *player.states[:2]]:
                physical_digest.update(value.detach().cpu().contiguous().numpy().tobytes())
            reset_done_rnn_states(player, done)
            checks['transitions'] += env.num_envs
            if step % 100 == 0:
                records.append(dict(step=step, action_error=0., current_object_actor_effect=0.))
                print(json.dumps(dict(step=step, checks=checks)), flush=True)
        assert tensor_digest(player.model.state_dict()) == start_model
        assert tensor_digest(env.fixed_student_encoder.state_dict()) == start_encoder
        assert min(checks['sampled_rows']) > 0 and checks['critic_changed'] > 0
        # PPO switches the whole model into training mode. Observation stats
        # must still be frozen, and frozen environment encoder stays in eval.
        player.model.train()
        assert not player.model.running_mean_std.training
        assert not env.fixed_student_encoder.training
        assert all(not p.requires_grad for p in env.fixed_student_encoder.parameters())
        assert all(not p.requires_grad for p in player.model.a2c_network.priv_encoder.parameters())
        files = ['scripts/check_wuji_student_actor_runtime.py', 'scripts/train_wuji_student_actor.py',
                 'isaacgymenvs/tasks/wuji_fixed_student_actor.py', 'isaacgymenvs/learning/wuji_fixed_student_actor.py',
                 'isaacgymenvs/cfg/task/wuji_fixed_student_actor.yaml', 'isaacgymenvs/cfg/train/wujiFixedStudentActorSAPG.yaml']
        report = dict(status='passed', checks=checks, frozen_encoder_sha256=STUDENT_SHA,
                      action_and_actor_rnn_equal_to_original_student=True, current_object_actor_effect=0.,
                      privileged_critic=True, sources={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files},
                      model_unchanged=True, encoder_unchanged=True, observation_normalizer_frozen=True,
                      broad_goal_coefficient=args.broad_goal_coefficient,
                      broad_goal_reward_checks=reward_checks,
                      physics_action_actor_rnn_sha256=physical_digest.hexdigest(),
                      records=records, scope='Runtime wiring on existing training distributions, not independent task success or hardware proof.')
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    finally:
        WujiBridge3Hemisphere.compute_reward = original_reward
        hook.remove()
        if env.viewer is not None:
            env.gym.destroy_viewer(env.viewer)
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
