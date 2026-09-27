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
    p.add_argument('--route', choices=['support', 'joint'], default='support')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--teacher', type=Path, default=TEACHER)
    p.add_argument('--teacher-device', default='cpu')
    p.add_argument('--steps', type=int)
    p.add_argument('--video', action='store_true')
    p.add_argument('--prepare-closed-seconds',type=float,default=0.,help='Explicit local diagnostic: physical closed-goal teacher preparation, separately scored, then a fresh20s external clock. No physics reset at boundary.')
    args = p.parse_args()
    if args.prepare_closed_seconds:
        assert args.task=='S' and args.baseline in ['learned','thumb-only'] and 0<args.prepare_closed_seconds<=6
    args.output.mkdir(parents=True, exist_ok=False)
    env = LocalG2(args.task, args.num_envs, args.route, graphics=args.video)
    network = None
    if args.checkpoint:
        from scripts.train_g2_local import ActorCritic
        artifact = torch.load(args.checkpoint, map_location='cpu')
        network = ActorCritic(env.observation().shape[-1], env.action_dim)
        network.load_state_dict(artifact['model'])
        network.eval()
    if args.task == 'S' and (args.baseline in ['full-teacher', 'thumb-only'] or args.route == 'support' and args.baseline == 'learned'):
        from scripts.g2_local_teacher import BatchedTeacher
        env.teacher = BatchedTeacher(env, args.teacher, args.teacher_device)
    writer = camera = None
    if args.video:
        import imageio.v2 as imageio
        from isaacgym import gymapi
        cp = gymapi.CameraProperties()
        cp.width, cp.height = 960, 720
        camera = env.gym.create_camera_sensor(env.envs[0], cp)
        o = env.object[0, :3]
        env.gym.set_camera_location(camera, env.envs[0], gymapi.Vec3(*(o+torch.tensor([.25,-.27,.18])).tolist()), gymapi.Vec3(*o.tolist()))
    summaries = []
    start = time.monotonic()
    try:
        for episode in range(args.episodes):
            if episode:
                env.reset()
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
                        image=env.gym.get_camera_image(env.sim,env.envs[0],camera,gymapi.IMAGE_COLOR)
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
            for i in range(args.steps or env.steps):
                with torch.no_grad():
                    if i == 0 or args.baseline != 'learned-static':
                        action = torch.zeros(env.n, env.action_dim) if network is None else network.mean_action(env.observation())
                env.step(action, baseline='learned' if args.baseline=='learned-static' else args.baseline)
                frame = env.frame()
                frame.update(env.contacts_for_evaluation())
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
                    image = env.gym.get_camera_image(env.sim, env.envs[0], camera, gymapi.IMAGE_COLOR)
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
            elapsed_seconds=time.monotonic()-start, episodes=summaries), indent=2)+'\n')
    finally:
        if writer:
            writer.close()
        env.close()


if __name__ == '__main__':
    main()
