"""Hold the initialized commanded joint targets; no learned or scripted motion.

Separate initialization/contact stability from manipulation-policy failures.
The knife stays free and passive. No motor-force measurement is claimed.
An earlier optional DOF sensor request produced only zeros with an unavailable
sensor warning; those readings are archived separately and not used here.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_env
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hand', choices=['wuji_paper', 'wuji_paper_official_actuator'], required=True)
    parser.add_argument('--task', default='wuji_acquisition_precision_aug')
    parser.add_argument('--object', default='knife_wuji_acquisition_precision')
    parser.add_argument('--initial-states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit_source = Path(__file__).read_bytes()
    args.output.mkdir(parents=True, exist_ok=True)
    states = np.load(args.initial_states)
    assert states.ndim == 2 and len(states) > 0
    assert np.isfinite(states).all()
    cfg = configuration(args.task, len(states),
        ['object='+args.object, 'hand='+args.hand, 'test=True', 'task.env.episodeLength=600'],
        train='wujiAcquisitionSAPG', seed=1616)
    manifest_path=args.initial_states.parent/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        if manifest.get('expected_object_asset_root'):
            assert cfg.object.asset.asset_root==manifest['expected_object_asset_root'], 'Initial states and object geometry use different asset frames'
            urdf=Path(cfg.object.asset.asset_root)/'000'/cfg.object.asset.asset_file
            assert hashlib.sha256(urdf.read_bytes()).hexdigest()==manifest['expected_object_urdf_sha256'], 'Object geometry changed after state preparation'
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=True))
    (args.output/'source.py').write_bytes(audit_source)
    env = make_env(cfg)
    try:
        env.configure_fixed_grasp_consecutive_evaluation('000', states[0],
            goal_sequence=tuple(cfg.object.task.goals), episodes_per_grasp=len(states))
        assert tuple(env.eval_grasp_states.shape) == states.shape
        env.eval_grasp_states[:] = torch.as_tensor(states, device=env.device)
        env.success_hold_duration = 1e9
        env.eval_goal_timeout = 0.
        props = env.gym.get_actor_dof_properties(env.envs[0], env.gym.find_actor_handle(env.envs[0], 'hand'))
        actual = {k:props[k].tolist() for k in props.dtype.names}
        for key in ['stiffness', 'damping', 'armature']:
            assert np.allclose(props[key], cfg.hand.dof_props[key], atol=1e-7, rtol=1e-6)
        frames = []
        original = env.compute_reward

        def capture(actions):
            active = env.eval_active_mask.clone()
            original(actions)
            angle = 2*torch.asin(torch.norm(quat_mul(env.object_rot, quat_conjugate(env.init_object_rot))[:, :3], dim=-1).clamp(0, 1))
            row = dict(active=active, drift=torch.norm(env.object_pos-env.init_object_pos, dim=-1), rotation=angle,
                slider=env.obj_dof_pos[:, 0], fall=env.debug_reset_cause_fall, invalid=env.debug_reset_cause_invalid,
                q=env.hand_dof_pos, target=env.cur_targets[:, :20], contact=env.contact_info)
            frames.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})

        env.compute_reward = capture
        env.reset()
        zero = torch.zeros((len(states), 20), device=env.device)
        for step in range(600):
            if env.is_grasp_evaluation_complete():
                break
            env.step(zero)
            if (step+1) % 150 == 0:
                print(json.dumps(dict(step=step+1, active=int(env.eval_active_mask.sum()))), flush=True)
        trace = {k:np.stack([f[k] for f in frames]) for k in frames[0]}
        np.savez_compressed(args.output/'trace.npz', **trace)
        rows = []
        for i in range(len(states)):
            active = trace['active'][:, i]
            valid = active & ~trace['fall'][:, i] & ~trace['invalid'][:, i]
            pose = (trace['drift'][:, i] < .01) & (trace['rotation'][:, i] < .25)
            rows.append(dict(env=i, stable2s=bool(valid[:60].all() and pose[:60].all() and len(valid)>=60),
                stable20s=bool(len(valid)==600 and valid.all() and pose.all()),
                max_drift_m=float(trace['drift'][:, i][active].max()),
                max_rotation_rad=float(trace['rotation'][:, i][active].max()),
                fall=bool(trace['fall'][:, i][active].any()),
                max_target_change_rad=float(np.max(np.abs(trace['target'][:, i][active]-states[i, 20:40])))))
        assert max(r['max_target_change_rad'] for r in rows) < 2e-6
        result = dict(hand=args.hand, task=args.task, object=args.object,
            controller='zero action, holds initial commanded targets',
            stable2s=sum(r['stable2s'] for r in rows), stable20s=sum(r['stable20s'] for r in rows),
            num_envs=len(states), recorded_steps=len(frames), actual_dof_properties=actual,
            initial_state_sha256=hashlib.sha256(args.initial_states.read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(audit_source).hexdigest(), scope=__doc__, records=rows)
        (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ['hand', 'stable2s', 'stable20s', 'num_envs']}), flush=True)
    finally:
        env.gym.destroy_sim(env.sim)


if __name__ == '__main__':
    main()
