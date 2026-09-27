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
    p.add_argument('--baseline', choices=['fixed', 'full-teacher', 'thumb-only', 'learned'], default='fixed')
    p.add_argument('--num-envs', type=int, default=1)
    p.add_argument('--episodes', type=int, default=1)
    p.add_argument('--route', choices=['support', 'joint'], default='support')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--teacher', type=Path, default=TEACHER)
    p.add_argument('--teacher-device', default='cpu')
    p.add_argument('--steps', type=int)
    p.add_argument('--video', action='store_true')
    args = p.parse_args()
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
        writer = imageio.get_writer(args.output/'local-diagnostic.mp4', fps=30, codec='libx264', quality=7, pixelformat='yuv420p', ffmpeg_params=['-movflags', '+faststart'])
    summaries = []
    start = time.monotonic()
    try:
        for episode in range(args.episodes):
            if episode:
                env.reset()
            first = env.frame()
            first.update(env.contacts_for_evaluation())
            rows = [first]
            for i in range(args.steps or env.steps):
                with torch.no_grad():
                    action = torch.zeros(env.n, env.action_dim) if network is None else network.mean_action(env.observation())
                env.step(action, baseline=args.baseline)
                frame = env.frame()
                frame.update(env.contacts_for_evaluation())
                if env.teacher:
                    frame.update(teacher_action=env.teacher.last_action.numpy().copy(),
                        teacher_raw_action=env.teacher.raw_action.numpy().copy(), teacher_observation=env.teacher.last_obs.numpy().copy())
                    if i == 0:
                        for k in ['teacher_action', 'teacher_raw_action', 'teacher_observation']:
                            rows[0][k] = np.zeros_like(frame[k])
                rows.append(frame)
                if writer:
                    env.gym.step_graphics(env.sim)
                    env.gym.render_all_camera_sensors(env.sim)
                    image = env.gym.get_camera_image(env.sim, env.envs[0], camera, gymapi.IMAGE_COLOR)
                    writer.append_data(image.reshape(720, 960, 4)[:, :, :3])
            np.savez_compressed(args.output/('episode-%03d.npz'%episode), **{k:np.asarray([r[k] for r in rows]) for k in rows[0]})
            summary = {k:v.tolist() for k,v in env.metrics().items()}
            summaries.append(summary)
            print(json.dumps(dict(episode=episode, metrics=summary)), flush=True)
        (args.output/'report.json').write_text(json.dumps(dict(scope='local reset diagnostic; not continuous tabletop acquisition',
            args={k:str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
            elapsed_seconds=time.monotonic()-start, episodes=summaries), indent=2)+'\n')
    finally:
        if writer:
            writer.close()
        env.close()


if __name__ == '__main__':
    main()
