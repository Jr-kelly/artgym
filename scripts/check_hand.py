"""Load a configured hand, exercise its joints, and render a headless video."""
import argparse
from pathlib import Path

from isaacgym import gymapi, gymtorch
import imageio.v2 as imageio
import numpy as np
import torch
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hand', default='wuji')
    parser.add_argument('--cpu-pipeline', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('tmp/wuji-check'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg = yaml.safe_load((root / 'isaacgymenvs/cfg/hand' / f'{args.hand}.yaml').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    gym = gymapi.acquire_gym()
    params = gymapi.SimParams()
    params.dt = 1 / 120
    params.substeps = 4
    params.up_axis = gymapi.UP_AXIS_Z
    params.gravity = gymapi.Vec3(0, 0, -9.81)
    params.use_gpu_pipeline = not args.cpu_pipeline
    params.physx.use_gpu = True
    params.physx.num_position_iterations = 16
    params.physx.num_velocity_iterations = 4
    params.physx.contact_collection = gymapi.ContactCollection.CC_ALL_SUBSTEPS
    sim = gym.create_sim(0, 0, gymapi.SIM_PHYSX, params)
    if sim is None:
        raise RuntimeError('Failed to create PhysX simulation')
    try:
        options = gymapi.AssetOptions()
        options.fix_base_link = True
        options.disable_gravity = True
        options.collapse_fixed_joints = False
        options.use_physx_armature = True
        options.default_dof_drive_mode = gymapi.DOF_MODE_POS
        asset = gym.load_asset(sim, str(root), cfg['asset'], options)
        n = gym.get_asset_dof_count(asset)
        names = gym.get_asset_dof_names(asset)
        assert n == cfg['task']['numActions'], (n, cfg['task']['numActions'])
        assert names == cfg.get('dof_names', names), names
        shape_ranges = gym.get_asset_rigid_body_shape_indices(asset)
        for name in cfg['force_links']:
            index = gym.find_asset_rigid_body_index(asset, name)
            assert index >= 0 and shape_ranges[index].count > 0, name
        props = gym.get_asset_dof_properties(asset)
        for key, values in cfg['dof_props'].items():
            props[key][:] = values
        env = gym.create_env(sim, gymapi.Vec3(-0.5, -0.5, 0), gymapi.Vec3(0.5, 0.5, 1), 1)
        pose = gymapi.Transform()
        pose.p = gymapi.Vec3(0, 0, 0.5)
        pose.r = gymapi.Quat.from_axis_angle(gymapi.Vec3(0, 1, 0), -np.pi / 2) * gymapi.Quat.from_axis_angle(gymapi.Vec3(1, 0, 0), np.pi / 2)
        actor = gym.create_actor(env, asset, pose, 'hand', 0, 0 if cfg.get('self_collisions', True) else 1 << 3)
        gym.set_actor_dof_properties(env, actor, props)
        initial = np.clip(np.zeros(n, dtype=np.float32), props['lower'], props['upper'])
        state = np.zeros(n, dtype=gymapi.DofState.dtype)
        state['pos'] = initial
        gym.set_actor_dof_states(env, actor, state, gymapi.STATE_ALL)
        camera_props = gymapi.CameraProperties()
        camera_props.width, camera_props.height = 640, 480
        camera = gym.create_camera_sensor(env, camera_props)
        gym.set_camera_location(camera, env, gymapi.Vec3(0.22, -0.24, 0.72), gymapi.Vec3(0, -0.07, 0.5))
        gym.prepare_sim(sim)
        dofs = gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim))
        targets = torch.as_tensor(initial, dtype=torch.float32, device=dofs.device).clone()
        frames = []
        maximum_motion = 0.0
        for step in range(360):
            fraction = 0.25 * (1 - np.cos(2 * np.pi * step / 360))
            target = initial + fraction * (props['upper'] - initial)
            targets.copy_(torch.as_tensor(target, dtype=torch.float32, device=dofs.device))
            gym.set_dof_position_target_tensor(sim, gymtorch.unwrap_tensor(targets))
            gym.simulate(sim)
            gym.fetch_results(sim, True)
            gym.refresh_dof_state_tensor(sim)
            assert torch.isfinite(dofs).all().item()
            current = dofs[:, 0].cpu().numpy()
            assert np.all(current >= props['lower'] - 0.15) and np.all(current <= props['upper'] + 0.15), (step, current)
            maximum_motion = max(maximum_motion, float(np.mean(np.abs(current - initial))))
            if step % 6 == 0:
                gym.step_graphics(sim)
                gym.render_all_camera_sensors(sim)
                frame = np.asarray(gym.get_camera_image(sim, env, camera, gymapi.IMAGE_COLOR)).reshape(480, 640, 4)
                frames.append(frame[:, :, :3].copy())
        assert maximum_motion > 0.1, maximum_motion
        imageio.imwrite(args.output / 'hand.png', frames[len(frames) // 2])
        imageio.mimwrite(args.output / 'hand.mp4', frames, fps=20)
        report = {'hand':args.hand, 'asset':cfg['asset'], 'dofs':n, 'dof_names':names,
                  'rigid_bodies':gym.get_asset_rigid_body_count(asset),
                  'collision_shapes':gym.get_asset_rigid_shape_count(asset),
                  'pipeline':str(dofs.device), 'steps':360, 'max_mean_joint_motion_rad':maximum_motion}
        (args.output / 'report.yaml').write_text(yaml.safe_dump(report, sort_keys=False))
        print(yaml.safe_dump(report, sort_keys=False))
        print('HAND CHECK PASSED')
    finally:
        gym.destroy_sim(sim)


if __name__ == '__main__':
    main()
