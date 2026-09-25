"""Inspect grasp contacts/drift at several times without changing the source pool."""
import argparse
import json
from pathlib import Path
import tempfile

import isaacgym
from isaacgym import gymapi
import numpy as np
import torch
from hydra import compose, initialize_config_dir
from PIL import Image
import isaacgymenvs

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', default='000')
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--steps', type=int, default=30)
    parser.add_argument('--output', type=Path, default=ROOT/'tmp/paper-grasps/diagnostic')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = ROOT/'caches/initial_grasp/wuji/knife_wuji_paper'/args.instance
    q, poses = np.load(source/'qpos.npy'), np.load(source/'opos.npy')
    count = min(args.count, len(q), len(poses))
    q, poses = q[:count].copy(), poses[:count].copy()
    np.save(args.output/'qpos.npy', q); np.save(args.output/'opos.npy', poses)
    with tempfile.TemporaryDirectory(prefix='_paper_probe_', dir=ROOT/'assets/objects') as temp:
        asset = Path(temp)
        (asset/args.instance).symlink_to(ROOT/'assets/objects/knife_wuji_paper'/args.instance, target_is_directory=True)
        (asset/'lbx.json').symlink_to(ROOT/'assets/objects/knife_wuji_paper/lbx.json')
        with tempfile.TemporaryDirectory(prefix=asset.name, dir=ROOT/'caches/initial_grasp/wuji') as ctemp:
            # Cache key follows the asset directory name, so use the unique cache name.
            key = Path(ctemp).name
            alias = ROOT/'assets/objects'/key
            alias.symlink_to(asset, target_is_directory=True)
            try:
                cache = Path(ctemp)/args.instance
                cache.mkdir()
                np.save(cache/'qpos.npy', q); np.save(cache/'opos.npy', poses)
                isaacgymenvs.register_omegaconf_resolvers()
                with initialize_config_dir(version_base='1.1', config_dir=str(ROOT/'isaacgymenvs/cfg')):
                    cfg = compose('config', overrides=['task=artgrasp', 'train=artmanipPrivLSTMPPO', 'hand=wuji_paper', 'object=knife_wuji_paper',
                        f'asset_dir={key}', f"object.asset.instance_id_list=['{args.instance}']",
                        f'task.env.numEnvs={count}', f'task.env.episodeLength={args.steps+1}',
                        'pipeline=cpu', 'headless=True', 'task.env.forceScale=0',
                        'task.env.enableCameraSensors=True', 'task.task.randomize=False',
                        'object.randomization.randomize=False', 'hand.randomization.randomize=False'])
                env = isaacgymenvs.make(20260920, 'artgrasp', count, 'cuda:0', 'cuda:0', 0, True, cfg=cfg)
                try:
                    env.reset()
                    reports = []
                    for step in range(1, args.steps+1):
                        env.step(env.zero_actions())
                        if step not in {1, 3, 10, args.steps}: continue
                        drift = (env.object_pos-env.init_object_pos).norm(dim=-1).cpu().numpy()
                        contact = np.zeros((count,5), dtype=bool)
                        forces = np.zeros((count,5))
                        for i, handle in enumerate(env.envs):
                            for c in env.gym.get_env_rigid_contacts(handle):
                                a, b = int(c['body0']), int(c['body1'])
                                for finger, pad in enumerate(env.force_handles.tolist()):
                                    obj = env.object_link1_handle if finger==0 else env.object_link0_handle
                                    if {a,b} == {int(pad),int(obj)}:
                                        forces[i,finger] += float(c['lambda'])
                                        contact[i,finger] |= float(c['lambda'])>1e-6
                        reports.append(dict(step=step, drift_m=drift.tolist(), contacts=contact.tolist(), forces=forces.tolist()))
                        print('step',step,'stable',int(env.check_valid().sum()), 'contacts',contact.sum(0),
                              'max_contacts',int(contact.sum(-1).max()),'drift_quantiles',np.quantile(drift,[0,.5,1]),flush=True)
                        env.gym.step_graphics(env.sim)
                        env.gym.render_all_camera_sensors(env.sim)
                        best = np.argsort(-contact.sum(-1))[:4]
                        for index in best:
                            frame = env.gym.get_camera_image(env.sim, env.envs[index],env.cam_handle_list[index],gymapi.IMAGE_COLOR)
                            image = frame.reshape(env.image_height,env.image_width,-1)[...,:3]
                            Image.fromarray(image).save(args.output/f'step{step:03d}-candidate{index:03d}.png')
                    (args.output/'contacts.json').write_text(json.dumps(reports,indent=2))
                finally:
                    env.gym.destroy_sim(env.sim)
            finally:
                alias.unlink()


if __name__ == '__main__':
    main()
