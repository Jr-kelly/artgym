"""Wuji teacher/student arrival-triggered knife cycles, using inherited switching.

Paper-inspired evaluation only: 10 mm arrival, immediate command reversal,
no stage timeout. The trained Wuji physics/controller and rewards are retained;
this does not claim exact paper replication. Simulator arrival truth is used
only by the high-level test command scheduler, never as a student policy input.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
import numpy as np
import torch
from omegaconf import OmegaConf
from isaacgymenvs.student_eval_utils import run_grasp_evaluation_loop
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
from scripts.wuji_arrival_metrics import score_arrival_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--student-artifact', type=Path)
    parser.add_argument('--task', help='Explicit trained action/task variant; default follows teacher/student mode.')
    parser.add_argument('--hand', choices=['wuji_paper', 'wuji_paper_official_actuator'], default='wuji_paper')
    parser.add_argument('--object', default='knife_wuji_acquisition_precision', help='Explicit object and physics profile for this audit.')
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--initial-state-rows', type=int, nargs='+')
    parser.add_argument('--video', action='store_true', help='Text-free grid for at most six explicitly chosen states.')
    parser.add_argument('--physical-gpu-index', type=int, default=0,
                        help='Unmasked CUDA and Vulkan index for video only.')
    parser.add_argument('--camera-position', type=float, nargs=3, default=[-.10, -.16, .75])
    parser.add_argument('--camera-target', type=float, nargs=3, default=[0., -.085, .525])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--total-seconds', type=int, choices=[20, 60], required=True)
    parser.add_argument('--tolerance-mm', type=float, choices=[2., 10.], default=10.)
    parser.add_argument('--seed', type=int, default=1616)
    args = parser.parse_args()
    total_steps = args.total_seconds * 30
    tolerance = args.tolerance_mm / 1000.0
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'report.json').exists():
        raise RuntimeError('Preserve completed evidence; choose a new output directory')
    states = np.load(args.initial_states)
    if states.ndim != 2 or not np.isfinite(states).all():
        raise ValueError('Initial states must be a finite matrix')
    selected_rows = args.initial_state_rows or list(range(len(states)))
    if not selected_rows or min(selected_rows) < 0 or max(selected_rows) >= len(states):
        raise ValueError('Initial-state row selection is out of bounds')
    states = states[selected_rows]
    if args.video and not 1 <= len(states) <= 6:
        raise ValueError('A video requires one to six explicitly chosen initial states')
    task = args.task or ('wuji_acquisition_precision_student' if args.student_artifact else 'wuji_acquisition_precision_aug')
    overrides = ['object='+args.object, 'hand='+args.hand, 'test=True', 'task.env.episodeLength='+str(total_steps),
                 'object.task.success_threshold='+str(tolerance)]
    if args.video:
        index = args.physical_gpu_index
        overrides += ['graphics_device_id='+str(index), 'sim_device=cuda:'+str(index),
            'rl_device=cuda:'+str(index), 'task.env.enableCameraSensors=True',
            'task.env.camera.width=512', 'task.env.camera.height=384',
            'task.env.camera.cam_pos='+json.dumps(args.camera_position),
            'task.env.camera.cam_target='+json.dumps(args.camera_target)]
    cfg = configuration(task, len(states), overrides, train='wujiAcquisitionSAPG', seed=args.seed)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    audit_source = Path(__file__).read_bytes()
    scorer_source = Path(__file__).with_name('wuji_arrival_metrics.py').read_bytes()
    (args.output/'source.py').write_bytes(audit_source)
    (args.output/'source_metrics.py').write_bytes(scorer_source)
    env, player = make_player(cfg, args.checkpoint)
    if args.student_artifact:
        from isaacgymenvs.infer_student_impl import build_student_encoder_from_artifact
        from isaacgymenvs.eval_common import preprocess_train_config
        artifact = torch.load(args.student_artifact, map_location='cpu')
        metadata = artifact['distill_meta']
        if metadata['task'] != task or metadata['hand'] != args.hand:
            raise ValueError('Student identity mismatch')
        expected_teacher = metadata.get('teacher_checkpoint_sha256')
        if expected_teacher and hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() != expected_teacher:
            raise ValueError('Student was distilled against a different teacher checkpoint')
        encoder, _, _, _ = build_student_encoder_from_artifact(player, cfg,
            preprocess_train_config(cfg, OmegaConf.to_container(cfg.train, resolve=True)), artifact, metadata)
        player.model.a2c_network.priv_encoder = encoder
        player.model.eval()
        env.set_student_encoder_obs_enabled(True)
    env.configure_fixed_grasp_consecutive_evaluation(instance_id='000', grasp_state=states[0],
        goal_sequence=tuple(cfg.object.task.goals), episodes_per_grasp=len(states))
    if states.shape != tuple(env.eval_grasp_states.shape):
        raise ValueError('Saved initial state layout mismatch')
    env.eval_grasp_states[:] = torch.as_tensor(states, device=env.device)
    # Reuse the environment's arrival-triggered switching. Only the declared
    # tolerance, dwell time and stage timeout change relative to the old audit.
    env.success_hold_duration = 0.0
    env.eval_goal_timeout = 0.0
    dt = env.dt * env.control_freq_inv
    assert abs(dt - 1/30) < 1e-7
    assert env.cfg['env']['rewardProtocol'] != 'upstream'
    assert env.object_cfg['task']['success_threshold'] == tolerance
    frames = []
    compute_reward = env.compute_reward

    def observe_arrival(actions):
        active = env.eval_active_mask.clone()
        goal = env.goal_obj_dof_pos[:, 0].clone()
        stage = env.eval_goal_stage.clone()
        compute_reward(actions)
        valid = active & ~env.debug_reset_cause_fall & ~env.debug_reset_cause_invalid
        valid &= torch.isfinite(env.obj_dof_pos[:, 0])
        expected = valid & ~env.debug_reset_cause_timeout & ((env.obj_dof_pos[:, 0]-goal).abs() < tolerance)
        assert torch.equal(env.goal_achieved_step.bool(), expected)
        angle = 2*torch.asin(torch.norm(quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))[:, :3], dim=-1).clamp(0, 1))
        row = dict(active=active, goal=goal, stage=stage, achieved=env.goal_achieved_step,
                   slider=env.obj_dof_pos[:, 0], drift=torch.norm(env.object_pos-env.init_object_pos, dim=-1),
                   rotation=angle, fall=env.debug_reset_cause_fall, invalid=env.debug_reset_cause_invalid,
                   timeout=env.debug_reset_cause_timeout,
                   q=env.hand_dof_pos, target=env.cur_targets[:, :20], action=env.actions)
        frames.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})

    env.compute_reward = observe_arrival
    writer = None
    if args.video:
        import imageio.v2 as imageio
        from isaacgym import gymapi
        camera_frame = env.get_camera_frame

        def grid_frame(env_id=0):
            first = camera_frame(0)
            pictures = [first]
            for i in range(1, env.num_envs):
                camera = env.cam_handle_list[i]
                if torch.is_tensor(camera):
                    camera = int(camera.item())
                raw = env.gym.get_camera_image(env.sim, env.envs[i], camera, gymapi.IMAGE_COLOR)
                pictures.append(np.asarray(raw).reshape(384, 512, -1)[:, :, :3])
            columns = min(3, len(pictures))
            rows = (len(pictures)+columns-1)//columns
            pictures.extend([np.zeros_like(first)]*(rows*columns-len(pictures)))
            return np.concatenate([np.concatenate(pictures[j*columns:(j+1)*columns], axis=1)
                                   for j in range(rows)], axis=0)

        env.get_camera_frame = grid_frame
        writer = imageio.get_writer(args.output/'policy.mp4', fps=30)
    try:
        run_grasp_evaluation_loop(player, env, deterministic=True, progress_interval_sec=30,
                                  use_student_encoder=args.student_artifact is not None, video_writer=writer)
        trace = {key:np.stack([row[key] for row in frames]) for key in frames[0]}
        np.savez_compressed(args.output/'trace.npz', **trace)
        report = score_arrival_trace(trace, total_steps, tolerance)
        report.update(checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
            task=task, hand=args.hand, object=args.object,
            action_control=dict(support_span_rad=env.cfg['env']['supportActionSpan'],
                                thumb_step_rad=env.cfg['env']['thumbActionStep']),
            student_sha256=hashlib.sha256(args.student_artifact.read_bytes()).hexdigest() if args.student_artifact else None,
            initial_states_sha256=hashlib.sha256(args.initial_states.read_bytes()).hexdigest(),
            initial_state_rows=selected_rows,
            source_sha256=hashlib.sha256(audit_source).hexdigest(),
            scorer_sha256=hashlib.sha256(scorer_source).hexdigest(),
            protocol=dict(total_seconds=args.total_seconds, control_dt=dt,
                          goal_tolerance_m=tolerance, hold_steps=1,
                          schedule='arrival-triggered extension then retraction',
                          runtime_overrides=dict(success_hold_duration=0, eval_goal_timeout=0),
                          arrival_used_for_switching=True,
                          command_scheduler_has_simulator_arrival=True,
                          policy_has_current_object_state=not bool(args.student_artifact)), scope=__doc__)
        (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in report.items() if k not in ['records','scope']}), flush=True)
    finally:
        if writer:
            writer.close()
        # Camera diagnostics may own sensors in addition to the task cameras.
        # Release those while the simulation is still valid, exactly once.
        before_destroy = getattr(env, 'before_audit_destroy_sim', None)
        try:
            if before_destroy is not None:
                before_destroy()
        finally:
            env.gym.destroy_sim(env.sim)
        after_destroy = getattr(env, 'after_audit_destroy_sim', None)
        if after_destroy is not None:
            after_destroy()


if __name__ == '__main__':
    main()
