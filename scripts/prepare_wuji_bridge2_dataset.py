"""Freeze an adaptive two-grasp curriculum, keeping source and novel grasp distinct.

Training row0 is the exact successful source mapped into generated-asset axes;
row1 is functional20 training row16, chosen from training-only transfer results.
The original one held-out grasp stays held out. This is a curriculum branch,
not broad generalization or a replacement for the ongoing20-grasp experiment.
"""
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for seconds in [2, 5]:
        folder = base / 'verification' / ('near5-cp50-equivalent-original-frame-seed30-timed%dseconds' % seconds)
        status = json.loads((folder / 'status.json').read_text())
        report = json.loads((folder / 'report.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        assert report['num_envs'] == 100 and report['stable_full_all_endpoints'] == 100
    source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
    original = root / 'assets/objects/knife_wuji_lowgain_functional20_20260922'
    original_cache = root / 'caches/initial_grasp/wuji/knife_wuji_lowgain_functional20_20260922/000'
    nominal = np.load(source).copy()
    assert sha(source) == '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
    rotation = Rotation.from_euler('x', 90, degrees=True)
    for start in [43, 50]:
        nominal[:, start:start + 4] = (Rotation.from_quat(nominal[:, start:start + 4]) * rotation).as_quat()
    nominal[:, 54] += float(ET.parse(original / '000/mobility.urdf').find(".//joint[@name='slider']/limit").get('lower'))
    novel = np.load(original_cache / 'train/valid_grasps.npy')[16:17]
    train = np.concatenate([nominal, novel])
    test = np.load(original_cache / 'test/valid_grasps.npy')
    assert train.shape == (2, 75) and test.shape == (1, 75)
    assert len(np.unique(train, axis=0)) == 2
    name = 'knife_wuji_bridge2_20260922'
    asset = root / 'assets/objects' / name
    cache = root / 'caches/initial_grasp/wuji' / name / '000'
    assert not asset.exists() and not cache.exists()
    shutil.copytree(original / '000', asset / '000')
    shutil.copy2(original / 'lbx.json', asset / 'lbx.json')
    for split, data in [('train', train), ('test', test), ('valid', np.concatenate([train, test]))]:
        folder = cache / split
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / 'valid_grasps.npy', data)
    np.save(cache / 'valid_grasps.npy', np.concatenate([train, test]))
    (cache / 'grasp_state_metadata.json').write_text(json.dumps(dict(pose_frame='hand_base')) + '\n')
    result = dict(status='frozen', scope=__doc__, dataset=name, train_count=2, test_count=1,
                  records=[dict(split='train', row=0, source='mapped_original_successful_grasp'),
                           dict(split='train', row=1, source='functional20_training_row16'),
                           dict(split='test', row=0, source='unchanged_functional20_heldout_row0')],
                  input_sha256={str(p.relative_to(root)): sha(p) for p in [source, original_cache / 'train/valid_grasps.npy', original_cache / 'test/valid_grasps.npy']},
                  geometry_sha256=sha(asset / '000/mobility.urdf'),
                  artifact_sha256={str(p.relative_to(root)): sha(p) for parent in [asset, cache] for p in parent.rglob('*') if p.is_file()})
    (base / 'bridge2-dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (cache / 'dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    out = base / 'bridge2-evaluation-states'
    out.mkdir(exist_ok=False)
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    evaluation = {}
    for index, label in enumerate(['source', 'novel_train']):
        states = states_for_seed(train[index:index + 1], 20261036 + index, hand)
        path = out / (label + '.npy')
        np.save(path, states)
        evaluation[label] = dict(seed=20261036 + index, nominal_grasps=1, trials=100, sha256=sha(path))
    # Reuse the existing held-out perturbations, unfiltered; do not call these
    # fresh or 32 independent unseen grasps.
    heldout = base / 'functional20-evaluation-states/test.npy'
    shutil.copy2(heldout, out / 'heldout.npy')
    evaluation['heldout'] = dict(reused=True, nominal_grasps=1, trials=32, sha256=sha(heldout))
    (out / 'manifest.json').write_text(json.dumps(evaluation, indent=2) + '\n')
    print(json.dumps(dict(dataset=name, train=2, test=1, evaluation=evaluation)))


if __name__ == '__main__':
    main()
