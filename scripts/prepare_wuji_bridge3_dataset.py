"""Add validated training grasp15 to the two-grasp curriculum without filtering.

The first two nominal states remain byte-identical; the third is row15 of the
previous functional20 training split. The one held-out grasp is never used in
training. Its poor results remain part of every subsequent development audit.
"""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed, WujiKinematics


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    validated = []
    for seconds in [2, 5]:
        folder = base / 'verification' / ('functional15-functional20-cp100-fresh200-seed44-timed%dseconds' % seconds)
        status = json.loads((folder / 'status.json').read_text())
        report = json.loads((folder / 'report.json').read_text())
        assert status['status'] == 'completed' and status['returncode'] == 0
        assert report['checkpoint_sha256'] == 'd44f5c6f49ed5661af33e0acc226bc1072ee74f316893c26ae6d512cca05a41d'
        assert report['initial_states_sha256'] == '15a089cd304f86afe8a44d936fb27f90248be870ec774b4f5e70edafbed0afd9'
        assert report['num_envs'] == 200 and report['stable_full_all_endpoints'] >= 150
        validated.append(dict(path=str((folder / 'report.json').relative_to(root)), sha256=sha(folder / 'report.json')))
    old = root / 'caches/initial_grasp/wuji/knife_wuji_bridge2_20260922/000'
    third = root / 'caches/initial_grasp/wuji/knife_wuji_lowgain_functional20_20260922/000/train/valid_grasps.npy'
    source = np.load(old / 'train/valid_grasps.npy')
    train = np.concatenate([source, np.load(third)[15:16]])
    test = np.load(old / 'test/valid_grasps.npy')
    assert train.shape == (3, 75) and test.shape == (1, 75)
    assert np.array_equal(train[:2], source) and len(np.unique(np.concatenate([train, test]), axis=0)) == 4
    dataset = 'knife_wuji_bridge3_20260922'
    asset = root / 'assets/objects' / dataset
    cache = root / 'caches/initial_grasp/wuji' / dataset / '000'
    assert not asset.exists() and not cache.exists()
    shutil.copytree(root / 'assets/objects/knife_wuji_bridge2_20260922', asset)
    for split, values in [('train', train), ('test', test), ('valid', np.concatenate([train, test]))]:
        folder = cache / split
        folder.mkdir(parents=True)
        np.save(folder / 'valid_grasps.npy', values)
    np.save(cache / 'valid_grasps.npy', np.concatenate([train, test]))
    (cache / 'grasp_state_metadata.json').write_text(json.dumps(dict(pose_frame='hand_base')) + '\n')
    result = dict(status='frozen', scope=__doc__, dataset=dataset, train_count=3, test_count=1,
                  records=[dict(split='train', row=0, source='mapped_original_successful_grasp'),
                           dict(split='train', row=1, source='functional20_training_row16'),
                           dict(split='train', row=2, source='functional20_training_row15'),
                           dict(split='test', row=0, source='unchanged_functional20_heldout_row0')],
                  validation=validated, input_sha256={str(p.relative_to(root)): sha(p) for p in [old / 'train/valid_grasps.npy', third, old / 'test/valid_grasps.npy']},
                  geometry_sha256=sha(asset / '000/mobility.urdf'),
                  artifact_sha256={str(p.relative_to(root)): sha(p) for parent in [asset, cache] for p in parent.rglob('*') if p.is_file()})
    (base / 'bridge3-dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (cache / 'dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    output = base / 'bridge3-evaluation-states'
    output.mkdir(exist_ok=False)
    hand = WujiKinematics()
    hand.lower = hand.lower.astype(np.float32)
    hand.upper = hand.upper.astype(np.float32)
    pieces, splits = [], {}
    for i, label in enumerate(['source', 'novel16', 'novel15']):
        values = states_for_seed(train[i:i + 1], 20261045 + i, hand, trials=100)
        np.save(output / (label + '.npy'), values)
        pieces.append(values)
        splits[label] = dict(seed=20261045 + i, start=i * 100, stop=(i + 1) * 100,
                             nominal_grasps=1, trials=100, sha256=sha(output / (label + '.npy')))
    heldout = base / 'bridge2-evaluation-states/heldout.npy'
    pieces.append(np.load(heldout))
    np.save(output / 'mixed332.npy', np.concatenate(pieces))
    splits['heldout'] = dict(start=300, stop=332, nominal_grasps=1, trials=32, reused=True, sha256=sha(heldout))
    metadata = dict(scope='Unfiltered development cohort prepared before bridge3 training; not a final independent candidate validation.',
                    splits=splits, mixed_sha256=sha(output / 'mixed332.npy'))
    (output / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(dict(dataset=dataset, train=3, test=1, evaluation=metadata)))


if __name__ == '__main__':
    main()
