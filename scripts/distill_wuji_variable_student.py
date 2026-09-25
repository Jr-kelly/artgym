"""Run existing student distillation with a read-only variable-clock audit.

This entry point preserves the teacher's three-grasp observation convention and
2/5 s command schedule. It changes no rollout, supervision, optimizer or physics
code. The inherited fixed-clock observer is replaced before any environment
step because variable deadlines need their own independent check.
"""
import hashlib
from pathlib import Path

from scripts import wuji_goal_common  # Isaac Gym must precede torch.
import torch
from scripts import audit_distillation_runtime as audit_module


class VariableClockDistillationAudit(audit_module.DistillationRuntimeAudit):
    def __init__(self, directory, cfg, args, env, model, teacher_encoder):
        reward = env.compute_reward
        super().__init__(directory, cfg, args, env, model, teacher_encoder)
        assert args.task in ['wuji_acquisition_bridge3_hemisphere', 'wuji_acquisition_bridge3_controller_state']
        assert env.runtime_grasp_split == 'train' and not env.eval_mode
        assert env.all_valid_states.shape == (3, 75)
        assert env.training_duration_steps.tolist() == [60, 150]
        self.record['command_clock_kind'] = 'sampled_deadline'
        self.record['command_duration_steps'] = [60, 150]
        self.record['training_grasp_step_counts'] = [0, 0, 0]
        self.record['rescheduled_duration_counts'] = {'60': 0, '150': 0}
        self.record['student_observation_dim'] = env.student_obs_dim
        augmented = args.task == 'wuji_acquisition_bridge3_controller_state'
        self.record['controller_state_inputs'] = augmented
        self.record['controller_input_checks'] = 0
        if augmented:
            assert env.student_obs_dim == 2076 and cfg.task.env.studentInitObsDim == 76
            self.record['controller_state_layout'] = ['20 normalized issued joint targets', 'commanded slider offset / 0.04m']
        self.record['variable_audit_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (self.path / 'variable-clock-source.py').write_bytes(Path(__file__).read_bytes())

        def observe(actions):
            if augmented:
                from isaacgymenvs.tasks.wuji_bridge3_controller_state import controller_state_features
                # The observations feeding this action came from the preceding
                # control step. Validate the shared pure deployment mapping on
                # the current controller state, then check the actual stored
                # student input at the actor call separately below.
                expected = controller_state_features(env.cur_targets[:, :20], env.hand_dof_lower_limits,
                    env.hand_dof_upper_limits, env.goal_obj_dof_pos-env.init_obj_dof_pos, .04)
                assert torch.equal(expected, env.current_controller_features())
            target = env.goal_obj_dof_pos.clone()
            progress = env.progress_buf.clone()
            deadline = env.command_deadline.clone()
            reward(actions)
            due = (progress >= deadline) & (env.reset_buf == 0)
            assert not env.eval_mode
            assert torch.equal((target != env.goal_obj_dof_pos).any(-1), due)
            assert torch.equal(env.command_deadline[~due], deadline[~due])
            durations = env.command_deadline[due] - progress[due]
            assert ((durations == 60) | (durations == 150)).all()
            for value in [60, 150]:
                self.record['rescheduled_duration_counts'][str(value)] += int((durations == value).sum())
            self.record['clock_switches'] += int(due.sum())
            self.record['clock_observed_transitions'] += env.num_envs
            # Nearest nominal hand configuration identifies reset ownership;
            # the three grasps differ much more than their 0.01 rad noise.
            nominal = env.all_valid_states[:, :20]
            distances = (env.init_hand_dof_pos[:, None, :] - nominal[None, :, :]).abs().amax(-1)
            best, row = distances.min(-1)
            assert (best < .011).all(), 'An undeclared grasp entered student training'
            counts = torch.bincount(row, minlength=3).tolist()
            self.record['training_grasp_step_counts'] = [a+b for a,b in zip(self.record['training_grasp_step_counts'], counts)]

        env.compute_reward = observe
        self.write()

    def observe_player_actions(self, player, teacher_encoder, student_encoder):
        super().observe_player_actions(player, teacher_encoder, student_encoder)
        if not self.record['controller_state_inputs']:
            return
        env = player.env.env
        original = player.get_action
        def observed(*args, **kwargs):
            inputs = player.model.a2c_network.actor_encoder_obs_override
            assert inputs is not None and inputs.shape[-1] == 2076
            assert torch.equal(inputs[:, -21:], env.current_controller_features())
            base = torch.cat([env.proprioception_buf.reshape(env.num_envs, -1), env._get_init_obs()], -1)
            assert torch.equal(inputs[:, :2055], base)
            self.record['controller_input_checks'] += env.num_envs
            return original(*args, **kwargs)
        player.get_action = observed

    def finish(self, model, teacher_encoder, student, updates):
        assert min(self.record['training_grasp_step_counts']) > 0
        assert sum(self.record['training_grasp_step_counts']) == self.record['clock_observed_transitions']
        assert min(self.record['rescheduled_duration_counts'].values()) > 0
        if self.record['controller_state_inputs']:
            assert self.record['controller_input_checks'] == self.record['clock_observed_transitions']
        super().finish(model, teacher_encoder, student, updates)


def main():
    previous = audit_module.DistillationRuntimeAudit
    audit_module.DistillationRuntimeAudit = VariableClockDistillationAudit
    try:
        from isaacgymenvs.distill import main as distill
        distill()
    finally:
        audit_module.DistillationRuntimeAudit = previous


if __name__ == '__main__':
    main()
