"""Optional observations of student training; does not alter actions or resets."""
import hashlib
import json
from pathlib import Path

import numpy as np
from omegaconf import OmegaConf


def tensor_digest(state, exclude_student=False):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        if exclude_student and name.startswith('a2c_network.priv_encoder.'):
            continue
        array = value.detach().cpu().contiguous().numpy()
        digest.update(name.encode())
        digest.update(str((array.dtype, array.shape)).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


class DistillationRuntimeAudit:
    def __init__(self, directory, cfg, args, env, model, teacher_encoder):
        self.path = Path(directory)
        self.path.mkdir(parents=True, exist_ok=True)
        OmegaConf.save(cfg, self.path/'config.yaml', resolve=True)
        arrays = {name: getattr(env, name).detach().cpu().numpy().copy()
                  for name in ['init_targets', 'init_object_pos', 'init_object_rot']}
        np.savez_compressed(self.path/'initial_states.npz', **arrays)
        noise_cfg = cfg.task.env.get('initialPoseNoise')
        noise = OmegaConf.to_container(noise_cfg, resolve=True) if noise_cfg else {}
        scale = float(env.extras.get('reset_noise/scale', 0.0))
        self.record = dict(
            status='running', arguments=vars(args), num_envs=env.num_envs,
            eval_mode=bool(env.eval_mode), policy_update_step=int(env.policy_update_step),
            initial_pose_noise=noise, observed_reset_noise_scale=scale,
            unique_initial_targets=int(len(np.unique(arrays['init_targets'], axis=0))),
            target_span_per_joint=np.ptp(arrays['init_targets'][:, :20], axis=0).tolist(),
            object_position_span_m=np.ptp(arrays['init_object_pos'], axis=0).tolist(),
            max_consecutive_successes=int(env.max_consecutive_successes),
            actor_and_normalizers_before=tensor_digest(model.state_dict(), True),
            teacher_encoder_before=tensor_digest(teacher_encoder.state_dict()),
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )
        if getattr(args, 'student_checkpoint', ''):
            import torch
            initialization = Path(args.student_checkpoint)
            payload = torch.load(initialization, map_location='cpu')
            expected = tensor_digest(payload['student_encoder_state_dict'])
            observed = tensor_digest(model.a2c_network.priv_encoder.state_dict())
            if expected != observed:
                raise RuntimeError('Actual initial student encoder differs from its declared artifact')
            self.record['student_initialization'] = dict(
                path=str(initialization), sha256=hashlib.sha256(initialization.read_bytes()).hexdigest(),
                expected_tensor_digest=expected, observed_tensor_digest=observed, passed=True)
        self.record['command_period_steps'] = int(getattr(env, 'command_period_steps', 0))
        self.record['clock_observed_transitions'] = 0
        self.record['clock_switches'] = 0
        if self.record['command_period_steps'] > 0:
            import torch
            original_reward = env.compute_reward
            period = self.record['command_period_steps']

            def observe_training_clock(actions):
                old_goal = env.goal_obj_dof_pos.clone()
                original_reward(actions)
                due = (env.progress_buf > 0) & (env.progress_buf % period == 0) & (env.reset_buf == 0)
                if env.eval_mode or not torch.equal((env.goal_obj_dof_pos != old_goal).any(dim=-1), due):
                    raise RuntimeError('Student training did not follow the declared command clock')
                self.record['clock_observed_transitions'] += env.num_envs
                self.record['clock_switches'] += int(due.sum())

            env.compute_reward = observe_training_clock
            props = env.gym.get_actor_dof_properties(env.envs[0], env.gym.find_actor_handle(env.envs[0], 'hand'))
            self.record['actual_actuator_properties'] = {k: props[k].tolist() for k in ['stiffness', 'damping', 'armature']}
            for key in self.record['actual_actuator_properties']:
                if not np.allclose(props[key], cfg.hand.dof_props[key], rtol=1e-6, atol=1e-7):
                    raise RuntimeError('Student actuator properties differ from the requested hand')
        self.write()
        if noise and int(noise.get('ramp_epochs', 0)) == 0:
            if env.eval_mode or scale != 1.0 or self.record['unique_initial_targets'] < env.num_envs // 2:
                raise RuntimeError('Declared full reset perturbations were not observed')

    def write(self):
        temporary = self.path/'runtime-audit.json.tmp'
        temporary.write_text(json.dumps(self.record, indent=2)+'\n')
        temporary.replace(self.path/'runtime-audit.json')

    def observe_player_actions(self, player, teacher_encoder, student_encoder):
        """Observe the actual encoder used at the actor call, not a schedule label."""
        original = player.get_action
        self.record['rollout_action_transitions'] = dict(teacher=0, student=0)
        mixing = bool(self.record['arguments'].get('teacher_latent_mix_initial', 0.0))
        if mixing:
            self.record['rollout_action_transitions']['mixed'] = 0
            self.record['teacher_fraction_transition_sum'] = 0.0
        self.record['student_rollout_module_modes'] = dict(training=0, evaluation=0)

        def observed(*args, **kwargs):
            network = player.model.a2c_network
            fraction = getattr(network, '_distillation_teacher_fraction', 0.0)
            if mixing:
                from isaacgymenvs.utils.distill_rollout_utils import teacher_mix_fraction
                arguments = self.record['arguments']
                update = sum(self.record['rollout_action_transitions'].values()) // (self.record['num_envs'] * arguments['rollout_steps'])
                expected = teacher_mix_fraction(update, arguments['teacher_latent_mix_initial'], arguments['teacher_latent_mix_updates'])
                if fraction != expected:
                    raise RuntimeError('Actual latent mixture differs from the declared update schedule')
            elif fraction:
                raise RuntimeError('Undeclared privileged mixture in student rollout')
            if network.priv_encoder is teacher_encoder:
                if network.actor_encoder_obs_override is not None:
                    raise RuntimeError('Teacher rollout must use the normal privileged normalization path')
                kind = 'teacher'
            elif network.priv_encoder is student_encoder:
                if network.actor_encoder_obs_override is None:
                    raise RuntimeError('Student rollout is missing restricted encoder observations')
                kind = 'mixed' if fraction else 'student'
                requested_eval = self.record['arguments'].get('student_rollout_eval_mode', False)
                if requested_eval and any(module.training for module in student_encoder.modules()):
                    raise RuntimeError('Student rollout was declared evaluation-mode but a module is training')
                mode = 'training' if student_encoder.training else 'evaluation'
                self.record['student_rollout_module_modes'][mode] += int(args[0].shape[0])
            else:
                raise RuntimeError('Unexpected rollout encoder identity')
            action = original(*args, **kwargs)
            import torch
            if not torch.isfinite(action).all():
                raise RuntimeError('Nonfinite distillation rollout action')
            self.record['rollout_action_transitions'][kind] += int(action.shape[0])
            if mixing:
                self.record['teacher_fraction_transition_sum'] += fraction * int(action.shape[0])
            return action

        player.get_action = observed

    def finish(self, model, teacher_encoder, student, updates):
        actor_after = tensor_digest(model.state_dict(), True)
        teacher_after = tensor_digest(teacher_encoder.state_dict())
        finite = all(np.isfinite(v.detach().cpu().numpy()).all() for v in student.state_dict().values())
        unchanged = (actor_after == self.record['actor_and_normalizers_before'] and
                     teacher_after == self.record['teacher_encoder_before'])
        self.record.update(status='verified' if unchanged and finite else 'failed',
                           completed_updates=updates, actor_and_normalizers_after=actor_after,
                           teacher_encoder_after=teacher_after, frozen_modules_unchanged=unchanged,
                           student_finite=bool(finite))
        self.write()
        if not unchanged or not finite:
            raise RuntimeError('Student runtime audit failed')
