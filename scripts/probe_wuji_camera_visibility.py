"""Render fixed candidate viewpoints while the frozen teacher drives physics.

Segmentation IDs measure visibility only. Neither images nor masks feed the
policy. This is a camera-placement diagnostic, not a vision policy or new
independent success test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import wuji_goal_common
from isaacgym import gymapi
import imageio.v2 as imageio
import numpy as np
import torch

from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import now

ROOT = Path(__file__).resolve().parents[1]
VIEWS = [(-.25, -.22, .18), (.25, -.22, .18), (0., .25, .12),
         (0., -.30, .10), (0., 0., .32), (-.30, .05, .08)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    original = wuji_goal_common.make_player
    rows, refs = [], {}
    writer = imageio.get_writer(args.output/'wuji-knife-six-camera-views-no-text.mp4', fps=3)

    def make_player(cfg, checkpoint):
        cfg.graphics_device_id = 0
        cfg.task.env.enableCameraSensors = True
        env, player = original(cfg, checkpoint)
        assert env.graphics_device_id == 0
        model = player.model.eval()
        refs.update(model=model, initial_digest=tensor_digest(model.state_dict()))
        cameras = []
        center = np.array([0., -.085, .525])
        for index, (handle, obj) in enumerate(zip(env.envs, env.object_handles)):
            names = env.gym.get_actor_rigid_body_names(handle, obj)
            assert names == ['link_0', 'link_1'], names
            for body in range(2):
                env.gym.set_rigid_body_segmentation_id(handle, obj, body, body+101)
            current = []
            for offset in VIEWS:
                props = gymapi.CameraProperties()
                props.width = props.height = 320
                props.horizontal_fov = 45.
                camera = env.gym.create_camera_sensor(handle, props)
                assert camera >= 0, (index, offset, camera)
                env.gym.set_camera_location(camera, handle, gymapi.Vec3(*(center+offset)), gymapi.Vec3(*center))
                current.append(camera)
            cameras.append(current)
        action = player.get_action
        step = [0]

        def observe(obs, is_deterministic=False, **kwargs):
            assert is_deterministic
            if step[0] % 10 == 0:
                env.gym.fetch_results(env.sim, True)
                env.gym.step_graphics(env.sim)
                env.gym.render_all_camera_sensors(env.sim)
                pictures, masks = [], []
                for index, handle in enumerate(env.envs):
                    images = []
                    for view, camera in enumerate(cameras[index]):
                        rgb = np.asarray(env.gym.get_camera_image(env.sim, handle, camera, gymapi.IMAGE_COLOR), dtype=np.uint8).reshape(320, 320, 4)[..., :3].copy()
                        segmentation = np.asarray(env.gym.get_camera_image(env.sim, handle, camera, gymapi.IMAGE_SEGMENTATION)).reshape(320, 320).copy()
                        values = []
                        for body in [101, 102]:
                            y, x = np.nonzero(segmentation == body)
                            box = [int(x.min()), int(y.min()), int(x.max()), int(y.max())] if len(x) else None
                            values.append(dict(pixels=len(x), bbox=box))
                        rows.append(dict(step=step[0], grasp_row=[0, 100, 200][index], view=view,
                            body=values[0], slider=values[1], active=bool(env.eval_active_mask[index])))
                        images.append(rgb)
                        masks.append(segmentation.astype(np.int16))
                    pictures.append(np.concatenate(images, axis=1))
                grid = np.concatenate(pictures, axis=0)
                writer.append_data(grid)
                if step[0] in [0, 150, 300, 450, 590]:
                    imageio.imwrite(args.output/f'views-step{step[0]:04d}.png', grid)
                    np.savez_compressed(args.output/f'masks-step{step[0]:04d}.npz', masks=np.stack(masks))
                if step[0] % 150 == 0:
                    print(json.dumps(dict(camera_step=step[0], images=len(masks))), flush=True)
            step[0] += 1
            return action(obs, is_deterministic=is_deterministic, **kwargs)

        player.get_action = observe
        return env, player

    wuji_goal_common.make_player = make_player
    argv = sys.argv
    try:
        sys.argv = [argv[0], '--checkpoint', str(ROOT/TEACHER), '--output', str(args.output),
            '--task', 'wuji_acquisition_bridge3_hemisphere', '--hand', 'wuji_paper_official_actuator',
            '--object', 'knife_wuji_bridge3_20260922', '--initial-states',
            str(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'),
            '--initial-state-rows', '0', '100', '200', '--stage-seconds', '2', '--seed', '20261060']
        from scripts.audit_wuji_timed_commands import main as evaluate
        evaluate()
    finally:
        writer.close()
        wuji_goal_common.make_player = original
        sys.argv = argv
    assert tensor_digest(refs['model'].state_dict()) == refs['initial_digest']
    assert len(rows) == 60*3*6
    groups = []
    for grasp in [0, 100, 200]:
        for view in range(6):
            selected = [r for r in rows if r['grasp_row'] == grasp and r['view'] == view]
            groups.append(dict(grasp_row=grasp, view=view, samples=len(selected),
                slider_visible_frames=sum(r['slider']['pixels'] > 0 for r in selected),
                slider_pixels_min=min(r['slider']['pixels'] for r in selected),
                slider_pixels_median=float(np.median([r['slider']['pixels'] for r in selected])),
                body_visible_frames=sum(r['body']['pixels'] > 0 for r in selected)))
    result = dict(created=now(), status='completed', scope=__doc__, teacher_unchanged=True,
        teacher_sha256=hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        current_truth_used_only_for_visibility_counts=True, policy_observations_unchanged=True,
        camera_center=[0., -.085, .525], relative_positions=VIEWS, width=320, height=320,
        sample_frequency_hz=3, row_order=[0, 100, 200], column_order=list(range(6)), rows=rows, groups=groups)
    (args.output/'visibility.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(groups))


if __name__ == '__main__':
    main()
