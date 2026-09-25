"""Privileged reset-stress diagnosis, with the RGB experiment's physical setup.

The teacher receives current simulator state. causal_truth instead reconstructs
the same state from exact pose/slider with the RGB controller's causal velocity.
Neither arm is deployable. Camera and estimator construction match the frozen
RGB run, including RNG consumption; only four diagnostic frames are rendered.
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
from omegaconf import OmegaConf
from scripts.wuji_rgb_state_model import RGBStateModel
from scripts.wuji_physical_state_encoder import encode_target, decode_prediction, SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.check_wuji_student_actor_runtime import TEACHER
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--initial-states', type=Path, required=True)
    p.add_argument('--initial-state-rows', type=int, nargs='+', required=True)
    p.add_argument('--seconds', type=int, choices=[2, 5], required=True)
    p.add_argument('--feedback', choices=['teacher', 'causal_truth'], required=True)
    p.add_argument('--evaluation-seed', type=int, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    assert hashlib.sha256((ROOT/TEACHER).read_bytes()).hexdigest() == '4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
    assert hashlib.sha256(args.artifact.read_bytes()).hexdigest() == '9221141fe68ec6c116d0b30fab1415794a0eefa48b4c0e8591ba7afe00669d28'
    artifact = torch.load(args.artifact, map_location='cpu')
    torch.set_num_threads(4)
    original = wuji_goal_common.make_player
    refs = {}
    rows = []
    checks = dict(physics_transitions=0, action_target_max_error=0., diagnostic_camera_frames=0)
    (args.output/'source-oracle.py').write_bytes(Path(__file__).read_bytes())

    def make_player(cfg, checkpoint):
        cfg.graphics_device_id = 0
        cfg.task.env.enableCameraSensors = True
        env, player = original(cfg, checkpoint)
        (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
        model = player.model.eval()
        # Preserve the exact post-player RNG consumption of the RGB evaluator.
        estimator = RGBStateModel(artifact['feature_mean'], artifact['feature_scale']).to(player.device).eval()
        estimator.load_state_dict(artifact['state_dict'])
        for network in [model, estimator]:
            for parameter in network.parameters():
                parameter.requires_grad_(False)
        refs.update(model=model, estimator=estimator, before=tensor_digest(model.state_dict()))
        props = env.object_cfg['default_props']
        properties = torch.tensor(list(props['mass'])+[props['friction'], props['dof_damping'], props.get('dof_stiffness', 0.)], device=player.device).reshape(1, 5)
        cameras = []
        center = np.array([0., -.085, .525])
        offset = np.array([0., .25, .12])
        for handle in env.envs:
            settings = gymapi.CameraProperties()
            settings.width = settings.height = 320
            settings.horizontal_fov = 45.
            camera = env.gym.create_camera_sensor(handle, settings)
            assert camera >= 0
            env.gym.set_camera_location(camera, handle, gymapi.Vec3(*(center+offset)), gymapi.Vec3(*center))
            cameras.append(camera)
        actual = player.get_action
        pre = env.pre_physics_step
        expected = {}
        dt = env.dt*env.control_freq_inv
        assert abs(dt-1/30) < 1e-7

        def pre_step(action):
            pre(action)
            assert torch.equal(env.actions, expected['action'])
            error = float((env.cur_targets[:, :20]-expected['targets']).abs().max())
            assert error < 1e-6, error
            checks['action_target_max_error'] = max(checks['action_target_max_error'], error)
            checks['physics_transitions'] += env.num_envs
        env.pre_physics_step = pre_step

        def action(obs, is_deterministic=False, **kwargs):
            assert is_deterministic
            step = len(rows)
            with torch.no_grad():
                truth = encode_target(obs[:, :55], obs[:, 111:132])*obs.new_tensor(SCALES)
                values = truth.clone()
                values[:, 7] = 0 if step == 0 else .75*expected['values'][:, 7]+.25*(truth[:, 6]-expected['values'][:, 6])/dt
                modified = obs.clone()
                if args.feedback == 'causal_truth':
                    modified[:, 111:132] = decode_prediction(obs[:, :55], values/values.new_tensor(SCALES), properties)
                else:
                    assert torch.equal(modified, obs)
                result = actual(modified, is_deterministic=True, **kwargs)
                assert result.shape == (env.num_envs, 20) and torch.isfinite(result).all()
                expected.update(action=result.clone(), targets=env.actions_to_targets(result).clone(), values=values.clone())
                rows.append(dict(truth=truth.cpu().numpy().copy(), actor_privileged=modified[:, 111:132].cpu().numpy().copy(),
                                 true_privileged=obs[:, 111:132].cpu().numpy().copy(), features=obs[:, :96].cpu().numpy().copy(),
                                 active=env.eval_active_mask.cpu().numpy().copy(), causal_values=values.cpu().numpy().copy()))
                if step in [1, 151, 301, 451]:
                    env.gym.fetch_results(env.sim, True)
                    env.gym.step_graphics(env.sim)
                    env.gym.render_all_camera_sensors(env.sim)
                    images = [np.asarray(env.gym.get_camera_image(env.sim, handle, cam, gymapi.IMAGE_COLOR), dtype=np.uint8).reshape(320, 320, 4)[..., :3].copy()
                              for handle, cam in zip(env.envs[:3], cameras[:3])]
                    imageio.imwrite(args.output/f'camera-step{step:04d}-no-text.png', np.concatenate(images, axis=1))
                    checks['diagnostic_camera_frames'] += len(images)
            if step % 60 == 0:
                atomic_json(args.output/'status.json', dict(status='evaluating', step=step, heartbeat=now(), checks=checks))
            return result
        player.get_action = action
        return env, player

    wuji_goal_common.make_player = make_player
    oldargv = sys.argv
    try:
        sys.argv = [oldargv[0], '--checkpoint', str(ROOT/TEACHER), '--output', str(args.output),
                    '--task', 'wuji_acquisition_bridge3_hemisphere', '--hand', 'wuji_paper_official_actuator',
                    '--object', 'knife_wuji_bridge3_20260922', '--initial-states', str(args.initial_states),
                    '--stage-seconds', str(args.seconds), '--seed', str(args.evaluation_seed),
                    '--initial-state-rows']+list(map(str, args.initial_state_rows))
        from scripts.audit_wuji_timed_commands import main as evaluate
        evaluate()
        report = json.loads((args.output/'report.json').read_text())
        assert len(rows) == report['recorded_steps'] == 600
        assert checks['physics_transitions'] == 600*len(args.initial_state_rows)
        assert tensor_digest(refs['model'].state_dict()) == refs['before']
        np.savez_compressed(args.output/'oracle-input-trace.npz', **{k: np.stack([r[k] for r in rows]) for k in rows[0]})
        audit = dict(status='passed', finished=now(), feedback=args.feedback, checks=checks, model_unchanged=True,
                     current_truth_actor_input=True, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), scope=__doc__)
        atomic_json(args.output/'oracle-audit.json', audit)
        atomic_json(args.output/'status.json', dict(status='completed', finished=now(), feedback=args.feedback, checks=checks))
    except BaseException as exc:
        atomic_json(args.output/'status.json', dict(status='failed', finished=now(), error=repr(exc), checks=checks))
        raise
    finally:
        sys.argv = oldargv
        wuji_goal_common.make_player = original


if __name__ == '__main__':
    main()
