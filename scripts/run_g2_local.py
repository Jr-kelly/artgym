"""Reproducible local diagnostic/evaluation; every episode retains raw states."""
import argparse
import json
from pathlib import Path
import time

from scripts.g2_local_env import LocalG2, ROOT
import numpy as np
import torch

TEACHER = Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/release-core-teacher-student-20260924-v1/wuji-core-teacher-student-20260924-teacher.pth')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', choices=['H', 'S'], default='H')
    p.add_argument('--baseline', choices=['fixed', 'full-teacher', 'thumb-only', 'learned', 'learned-static'], default='fixed')
    p.add_argument('--num-envs', type=int, default=1)
    p.add_argument('--episodes', type=int, default=1)
    p.add_argument('--route', choices=['support', 'joint'], help='Defaults to the checkpoint route, or support for a baseline')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--state',type=Path,help='Explicit measured state from a documented actual acquisition; local reset only, never whole-task success')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--input-ablation',choices=['fixed-body-live-slider','fixed-body-proprio-slider'],help='Frozen policy diagnostic using one ideal initialization; not a trained student')
    p.add_argument('--hand-gravity',action='store_true',help='Independent physics sensitivity: turn hand gravity ON, all other properties unchanged')
    p.add_argument('--hand-gravity-compensation',action='store_true',help='Explicit control variant: URDF modeled gravity/K motor feedforward capped .08rad; original total motor slew and limits')
    p.add_argument('--teacher', type=Path, default=TEACHER)
    p.add_argument('--teacher-device', default='cpu')
    p.add_argument('--steps', type=int)
    p.add_argument('--video', action='store_true')
    p.add_argument('--video-env',type=int,default=0,help='Declared replica to film; all replicas retain scores and raw traces')
    p.add_argument('--thumb-plan',type=Path,help='Named geometric motor-path diagnostic replaces frozen thumb actor; no slider actuation')
    p.add_argument('--motor-replay',type=Path,help='Open-loop successful motor-command replay diagnostic; no network or object-state replay')
    p.add_argument('--replay-contact-follow',choices=['none','normal','point'],default='none',help='Explicit privileged motor replay correction using actual simulated knife and slider pose')
    p.add_argument('--thumb-first-stroke-q4-correction', type=float, default=0., help='Declared single-factor diagnostic, normalized additive q4 thumb correction only first5s; total increment remains capped .025rad/step')
    p.add_argument('--prepare-closed-seconds',type=float,default=0.,help='Explicit local diagnostic: physical closed-goal teacher preparation, separately scored, then a fresh20s external clock. No physics reset at boundary.')
    args = p.parse_args()
    assert not args.hand_gravity_compensation or args.hand_gravity
    if args.input_ablation:
        assert args.task=='S' and args.baseline=='learned' and args.checkpoint and not args.prepare_closed_seconds
    if args.motor_replay:
        assert args.task=='S' and args.baseline=='fixed' and args.checkpoint is None
        assert args.thumb_plan is None and not args.prepare_closed_seconds
    else:
        assert args.replay_contact_follow=='none'
    if args.prepare_closed_seconds:
        assert args.task=='S' and args.baseline in ['learned','thumb-only'] and 0<args.prepare_closed_seconds<=6
    artifact=torch.load(args.checkpoint,map_location='cpu') if args.checkpoint else None
    args.route=args.route or (artifact['route'] if artifact else 'support')
    if artifact:assert args.route==artifact['route'], 'Checkpoint/control route mismatch'
    plan=json.loads(args.thumb_plan.read_text()) if args.thumb_plan else (artifact.get('thumb_plan') if artifact else None)
    if plan is not None:
        assert args.task=='S' and args.baseline in ['learned','learned-static'] and not args.thumb_first_stroke_q4_correction and not args.prepare_closed_seconds
    args.output.mkdir(parents=True, exist_ok=False)
    env = LocalG2(args.task, args.num_envs, args.route, graphics=args.video,state_path=args.state,hand_gravity=args.hand_gravity,hand_gravity_compensation=args.hand_gravity_compensation)
    (args.output/'physics-diagnostic.json').write_text(json.dumps(dict(hand_gravity_on=args.hand_gravity,
        effective_robot_gravity_flags=env.effective_gravity_flags,
        baseline_robot_gravity_flags=env.metadata['robot_gravity_flags'],
        hand_gravity_compensation=args.hand_gravity_compensation,
        gravity_model_vs_actual_properties=env.gravity_model_property_audit,
        policy_reference='nominal motor reference before G2 integral and optional hand gravity feedforward; actual actuator targets logged separately',
        scope='Only explicit hand gravity override; baseline physical parameters otherwise unchanged. Feedforward, when requested, changes motor commands only.'),indent=2)+'\n')
    assert abs(args.thumb_first_stroke_q4_correction) <= 1.
    env.thumb_first_stroke_q4_correction = args.thumb_first_stroke_q4_correction
    env.thumb_plan=plan
    network = None
    if args.checkpoint:
        from scripts.train_g2_local import ActorCritic
        network = ActorCritic(env.observation().shape[-1], env.action_dim)
        network.load_state_dict(artifact['model'])
        network.eval()
    if args.task == 'S' and args.baseline in ['full-teacher', 'thumb-only', 'learned', 'learned-static'] and env.thumb_plan is None:
        from scripts.g2_local_teacher import BatchedTeacher
        env.teacher = BatchedTeacher(env, args.teacher, args.teacher_device)
    writer = camera = None
    if args.video:
        assert 0<=args.video_env<env.n
        import imageio.v2 as imageio
        from isaacgym import gymapi
        cp = gymapi.CameraProperties()
        cp.width, cp.height = 960, 720
        camera = env.gym.create_camera_sensor(env.envs[args.video_env], cp)
        o = env.object[args.video_env, :3]
        env.gym.set_camera_location(camera, env.envs[args.video_env], gymapi.Vec3(*(o+torch.tensor([.25,-.27,.18])).tolist()), gymapi.Vec3(*o.tolist()))
    summaries = []
    start = time.monotonic()
    try:
        for episode in range(args.episodes):
            if episode:
                env.reset()
            reduced=None
            if args.input_ablation:
                from scripts.g2_input_ablation import InputAblation
                reduced=InputAblation(args.input_ablation,env.object,env.dof[:,27,0],env.dof[:,:27,0])
                (args.output/'input-contract.json').write_text(json.dumps(reduced.description(),indent=2)+'\n')
            replays = None
            if args.motor_replay:
                from scripts.g2_motor_replay import MotorReplay
                replays = [MotorReplay(args.motor_replay,env.targets[j,7:27].numpy(),env.lower[7:27].numpy(),env.upper[7:27].numpy(),args.replay_contact_follow) for j in range(env.n)]
            if args.video:
                writer = imageio.get_writer(args.output/('local-episode-%03d.mp4'%episode), fps=30, codec='libx264', quality=7, pixelformat='yuv420p', ffmpeg_params=['-movflags', '+faststart'])
            preparation = None
            if args.prepare_closed_seconds:
                env.goal_override = 0.
                prep = [env.frame()]
                prep_steps = round(args.prepare_closed_seconds*30)
                for i in range(prep_steps):
                    with torch.no_grad():
                        action = torch.zeros(env.n,env.action_dim) if network is None else network.mean_action(env.observation())
                    env.step(action,baseline=args.baseline)
                    prep.append(env.frame())
                    if writer:
                        env.gym.step_graphics(env.sim)
                        env.gym.render_all_camera_sensors(env.sim)
                        image=env.gym.get_camera_image(env.sim,env.envs[args.video_env],camera,gymapi.IMAGE_COLOR)
                        writer.append_data(image.reshape(720,960,4)[:,:,:3])
                np.savez_compressed(args.output/('preparation-%03d.npz'%episode),**{k:np.asarray([v[k] for v in prep]) for k in prep[0]})
                preparation = dict(seconds=args.prepare_closed_seconds,
                    world_drift_m=env.max_drift.tolist(),world_rotation_rad=env.max_rotation.tolist(),
                    stable=((env.max_drift<.01)&(env.max_rotation<.25)&~env.ever_drop).tolist(),
                    closed_goal_max_error_m=env.max_slider_goal_error.tolist(),
                    preparation_pass=((env.max_drift<.01)&(env.max_rotation<.25)&~env.ever_drop&(env.max_slider_goal_error<.01)).tolist(),
                    slider_at_end=env.dof[:,27,0].tolist(),scope='physical preparation, fixed initial reference, no object/hand writes')
                before = env.frame()
                recurrent_before = [v.clone() for v in env.teacher.states] if env.teacher else []
                history_before = env.teacher.history.clone() if env.teacher else None
                env.start_operation_window()
                after = env.frame()
                unchanged = ['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state',
                    'targets','reference_targets','arm_integral_state','residual','action']
                boundary_error = max(float(np.max(np.abs(before[k]-after[k]))) for k in unchanged)
                rnn_error = max([float((a-b).abs().max()) for a,b in zip(recurrent_before,env.teacher.states)]+[0.]) if env.teacher else 0.
                history_error = float((history_before-env.teacher.history).abs().max()) if env.teacher else 0.
                assert boundary_error == rnn_error == history_error == 0.
                preparation.update(boundary_physics_and_command_max_error=boundary_error,
                    boundary_rnn_max_error=rnn_error,boundary_history_max_error=history_error,
                    teacher_initial_observation_reference='unchanged from before physical preparation; RNN/history carry through',
                    operation_reference='fixed once at physical preparation end; prep also scored against its original fixed reference')
                (args.output/('preparation-%03d.json'%episode)).write_text(json.dumps(preparation,indent=2)+'\n')
            first = env.frame()
            first.update(env.contacts_for_evaluation())
            rows = [first]
            if reduced:
                rows[0].update(input_observation=np.zeros((env.n,artifact['obs_dim']),dtype=np.float32),
                    input_slider_estimate=env.dof[:,27,0].numpy().copy())
            for i in range(args.steps or env.steps):
                if replays is not None:
                    # Only motor references change; env.step retains original
                    # servo/integrator, physics and independent task metrics.
                    for j,replay in enumerate(replays):
                        env.targets[j,7:27] = torch.from_numpy(replay.step(env.wrist[j].numpy(),env.object[j].numpy(),float(env.dof[j,27,0])))
                        if replay.diagnostic is not None:
                            with (args.output/'replay-contact-feedback.jsonl').open('a') as feedback:
                                feedback.write(json.dumps(dict(step=i,episode=episode,replica=j,**replay.diagnostic))+'\n')
                with torch.no_grad():
                    if i == 0 or args.baseline != 'learned-static':
                        if reduced:
                            live=args.input_ablation=='fixed-body-live-slider'
                            observation=reduced.observation(env.dof[:,:27,0],env.dof[:,:27,1],env.targets,
                                env.age,env.residual,env.last_action,env.goal(),env.lower,env.upper,env.slider_lower,
                                live_slider=env.dof[:,27,0] if live else None,
                                live_slider_velocity=env.dof[:,27,1] if live else None)
                        else:
                            observation=env.observation()
                        action = torch.zeros(env.n, env.action_dim) if network is None else network.mean_action(observation)
                env.step(action, baseline='learned' if args.baseline=='learned-static' else args.baseline)
                frame = env.frame()
                frame.update(env.contacts_for_evaluation())
                if reduced:
                    frame.update(input_observation=observation.numpy().copy(),input_slider_estimate=reduced.estimated_slider.numpy().copy())
                if env.teacher:
                    frame.update(teacher_action=env.teacher.last_action.numpy().copy(),
                        teacher_raw_action=env.teacher.raw_action.numpy().copy(), teacher_observation=env.teacher.last_obs.numpy().copy())
                    if i == 0:
                        for k in ['teacher_action', 'teacher_raw_action', 'teacher_observation']:
                            rows[0][k] = np.zeros_like(frame[k])
                rows.append(frame)
                if (i+1)%150 == 0:
                    print(json.dumps(dict(episode=episode,step=i+1,
                        max_drift_m=env.max_drift.tolist(),max_rotation_rad=env.max_rotation.tolist())),flush=True)
                if writer:
                    env.gym.step_graphics(env.sim)
                    env.gym.render_all_camera_sensors(env.sim)
                    image = env.gym.get_camera_image(env.sim, env.envs[args.video_env], camera, gymapi.IMAGE_COLOR)
                    writer.append_data(image.reshape(720, 960, 4)[:, :, :3])
            np.savez_compressed(args.output/('episode-%03d.npz'%episode), **{k:np.asarray([r[k] for r in rows]) for k in rows[0]})
            summary = {k:v.tolist() for k,v in env.metrics().items()}
            if preparation is not None:
                summary['preparation'] = preparation
                summary['preparation_and_operation_success'] = [a and b for a,b in zip(preparation['preparation_pass'],summary['success'])]
            summaries.append(summary)
            print(json.dumps(dict(episode=episode, metrics=summary)), flush=True)
            if writer:
                writer.close()
                writer = None
        (args.output/'report.json').write_text(json.dumps(dict(scope='local reset diagnostic; not continuous tabletop acquisition',
            args={k:str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
            thumb_controller=('privileged contact-referenced motor replay: '+args.replay_contact_follow if args.replay_contact_follow!='none' else 'open-loop learned motor-command replay diagnostic') if args.motor_replay else ('geometric motor path from explicit file or embedded checkpoint' if env.thumb_plan is not None else ('frozen teacher' if env.teacher is not None else 'fixed')),
            elapsed_seconds=time.monotonic()-start, episodes=summaries), indent=2)+'\n')
    finally:
        if writer:
            writer.close()
        env.close()


if __name__ == '__main__':
    main()
