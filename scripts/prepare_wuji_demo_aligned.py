"""Export the successful preview's exact asset and one initial state for RL.

This is a diagnostic training set, not a new grasp-generation/validation result.
There is one unique grasp; evaluation measures acquisition, not generalization.
"""
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

from scripts.wuji_kinematics import ROOT, WujiKinematics


def prepare():
    source = ROOT / 'assets/demo/wuji_knife/fingertip_preset.yaml'
    preset = yaml.safe_load(source.read_text())
    asset = ROOT / preset['asset']
    hand = WujiKinematics()
    for path, expected in [(asset, preset['asset_sha256']),
                           (ROOT / hand.config['asset'], preset['hand_urdf_sha256'])]:
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Reference asset changed: {path}')
    if hand.names != preset['dof_names']:
        raise ValueError('Reference DOF order changed')
    root = ROOT / 'assets/objects/knife_wuji_demo_aligned'
    folder = root / '000'
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(asset, folder / 'mobility.urdf')
    shutil.copyfile(asset.with_name('parameters.json'), folder / 'parameters.json')
    params = json.loads((folder / 'parameters.json').read_text())
    (root / 'lbx.json').write_text(json.dumps({'000': params['handle_size'] + params['slider_size']}, indent=2))
    initial = preset['initial']
    q = np.asarray(initial['qpos'])
    rot = Rotation.from_quat(initial['rotations'])
    center = np.asarray(initial['centers'])
    slider = float(initial['slider'])
    link1 = center + rot.apply(np.asarray(params['slider_origin']) + [0, -slider, 0])
    frames = hand.forward(q)
    tips = np.concatenate([frames[name][:3, 3] for name in hand.config['track_links']])
    # Contact observations start at zero before the first physical step.
    state = np.concatenate([q, initial['targets'], center, rot.as_quat(), link1,
                            rot.as_quat(), [slider], tips, np.zeros(5)]).astype(np.float32)[None, :]
    assert state.shape == (1, 75) and np.isfinite(state).all()
    cache = ROOT / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000'
    cache.mkdir(parents=True, exist_ok=True)
    np.save(cache / 'valid_grasps.npy', state)
    (cache / 'train').mkdir(exist_ok=True)
    np.save(cache / 'train/valid_grasps.npy', state)
    metadata = dict(pose_frame='hand_base', unique_grasps=1,
                    source=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    provenance='Exact scripted-preview initial state; no trajectory imitation in RL',
                    evaluation_scope='Same training grasp only; not held-out generalization')
    (cache / 'grasp_state_metadata.json').write_text(json.dumps(metadata, indent=2))
    (root / 'manifest.json').write_text(json.dumps(dict(train_ids=['000'], test_ids=[], **metadata), indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    prepare()
