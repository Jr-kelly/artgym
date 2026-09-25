"""Freeze one physically exercised new training grasp for a separate RL stage.

Select functional27 training row24 after the documented scripted diagnostic.
This selection uses training data only. It remains fragile and is not a learned
policy success. Preserve both held-out rows and all multi-grasp experiments.
"""
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    source = 'knife_wuji_lowgain_functional27_20260922'
    name = 'knife_wuji_functional_single24_20260922'
    report_path = base / 'diagnostics/functional27-continuous-contact-motion/report.json'
    report = json.loads(report_path.read_text())
    status = json.loads(report_path.with_name('status.json').read_text())
    assert status['status'] == 'completed' and status['returncode'] == 0
    index = report['source_training_rows'].index(24)
    assert report['records'][index]['stable_full_all_endpoints']
    parent = root / 'caches/initial_grasp/wuji' / source / '000'
    original = np.load(parent / 'train/valid_grasps.npy')
    assert hashlib.sha256((parent / 'train/valid_grasps.npy').read_bytes()).hexdigest() == report['initial_states_sha256']
    train = original[24:25].copy()
    test = np.load(parent / 'test/valid_grasps.npy')
    assert train.shape == (1, 75) and test.shape == (2, 75)
    assert not ({row.tobytes() for row in train} & {row.tobytes() for row in test})
    asset = root / 'assets/objects' / name
    cache = root / 'caches/initial_grasp/wuji' / name / '000'
    assert not asset.exists() and not cache.exists()
    shutil.copytree(root / 'assets/objects' / source, asset)
    for split, array in [('train', train), ('test', test), ('valid', np.concatenate([train, test]))]:
        folder = cache / split
        folder.mkdir(parents=True)
        np.save(folder / 'valid_grasps.npy', array)
    np.save(cache / 'valid_grasps.npy', np.concatenate([train, test]))
    (cache / 'grasp_state_metadata.json').write_text('{"pose_frame":"hand_base"}\n')
    configuration = root / 'isaacgymenvs/cfg/object' / (name + '.yaml')
    configuration.write_text('defaults:\n  - knife_wuji_fingertip_precision000\n  - _self_\nasset:\n  asset_root: assets/objects/' + name + "\n  instance_id_list: ['000']\n")
    result = dict(status='frozen', dataset=name, train_count=1, test_count=2, scope=__doc__,
                  parent_dataset=source, parent_training_row=24, selection_report_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
                  parent_training_sha256=report['initial_states_sha256'],
                  scripted_result=report['records'][index],
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  geometry_sha256=hashlib.sha256((asset / '000/mobility.urdf').read_bytes()).hexdigest(),
                  artifact_sha256={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                                   for path in cache.rglob('*') if path.is_file()},
                  next_gate='Actual training runtime/control checks before scratch PPO. No imitation or trajectories in RL.')
    (base / 'functional-single24-dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (cache / 'dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(dataset=name, train=1, test=2)))


if __name__ == '__main__':
    main()
