"""Freeze an expansion of functional20 without modifying any ongoing run.

Only previously declared physical/posture/reach/contact gates select rows.
The 20/1 dataset and its evaluation states stay byte-identical. New seeds add
seven training grasps and one held-out grasp of the same geometry. Two held-out
poses do not establish broad generalization; the old five failed sources remain
a separate unchanged benchmark. No training or policy evaluation is launched.
"""
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial.transform import Rotation


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    base = root / 'runs/wuji-goal'
    previous_path = base / 'functional20-dataset-manifest.json'
    previous = json.loads(previous_path.read_text())
    assert previous['status'] == 'frozen'
    for name, digest in previous['artifact_sha256'].items():
        assert sha(root / name) == digest, name
    old_cache = root / 'caches/initial_grasp/wuji' / previous['dataset'] / '000'
    selected = {split: list(np.load(old_cache / split / 'valid_grasps.npy'))
                for split in ['train', 'test']}
    records = [dict(row) for row in previous['records']]
    sources = {str(previous_path.relative_to(root)): sha(previous_path)}
    counts = {}
    for seed in [19, 20]:
        folder = base / 'diagnostics' / ('fresh-lowgain-functional-generation-seed' + str(seed)) / 'independent-quality'
        paths = {name: folder / name for name in ['status.json', 'report.json',
                 'candidates/manifest.json', 'candidates/initial_states.npy']}
        status = json.loads(paths['status.json'].read_text())
        report = json.loads(paths['report.json'].read_text())
        manifest = json.loads(paths['candidates/manifest.json'].read_text())
        assert status['status'] == report['status'] == 'completed'
        assert all(stage['returncode'] == 0 for stage in status['stages'])
        assert manifest['expected_object_urdf_sha256'] == previous['geometry_sha256']
        assert manifest['rules']['version'] == 'approved_fingertip_v1'
        assert sha(paths['candidates/initial_states.npy']) == report['initial_states_sha256'] == manifest['states_sha256']
        states = np.load(paths['candidates/initial_states.npy'])
        counts[str(seed)] = report['counts']
        for row in report['records']:
            if not row['all_gates_pass']:
                continue
            split, index = row['split'], row['candidate_row']
            assert split in selected
            records.append(dict(group='fresh_seed202610' + str(seed), split=split,
                                candidate_row=index, source=str(paths['candidates/initial_states.npy'].relative_to(root)),
                                dataset_split_row=len(selected[split])))
            selected[split].append(states[index])
        sources.update({str(path.relative_to(root)): sha(path) for path in paths.values()})
    arrays = {split: np.stack(values) for split, values in selected.items()}
    assert arrays['train'].shape == (27, 75) and arrays['test'].shape == (2, 75)
    for split, array in arrays.items():
        assert np.isfinite(array).all()
        assert len({row.tobytes() for row in array}) == len(array)
        old = np.load(old_cache / split / 'valid_grasps.npy')
        assert np.array_equal(array[:len(old)], old)
    assert not ({row.tobytes() for row in arrays['train']} & {row.tobytes() for row in arrays['test']})
    separation = []
    for index, state in enumerate(arrays['test']):
        train = arrays['train']
        position = np.linalg.norm(train[:, 40:43] - state[40:43], axis=1)
        angle = (Rotation.from_quat(train[:, 43:47]) * Rotation.from_quat(state[43:47]).inv()).magnitude()
        nearest = int(np.argmin(position / .005 + angle / .05))
        separation.append(dict(test_row=index, nearest_train_row=nearest,
                               nearest_position_m=float(position[nearest]), nearest_rotation_rad=float(angle[nearest]),
                               near_pose_train_rows=np.flatnonzero((position <= .005) & (angle <= .05)).tolist()))
    name = 'knife_wuji_lowgain_functional27_20260922'
    asset = root / 'assets/objects' / name
    cache = root / 'caches/initial_grasp/wuji' / name / '000'
    configuration = root / 'isaacgymenvs/cfg/object' / (name + '.yaml')
    assert not asset.exists() and not cache.exists() and not configuration.exists()
    old_asset = root / 'assets/objects' / previous['dataset']
    assert sha(old_asset / '000/mobility.urdf') == previous['geometry_sha256']
    shutil.copytree(old_asset, asset)
    all_states = np.concatenate([arrays['train'], arrays['test']])
    for split, data in list(arrays.items()) + [('valid', all_states)]:
        folder = cache / split
        folder.mkdir(parents=True)
        np.save(folder / 'valid_grasps.npy', data)
    np.save(cache / 'valid_grasps.npy', all_states)
    (cache / 'grasp_state_metadata.json').write_text(json.dumps(dict(pose_frame='hand_base')) + '\n')
    configuration.write_text('defaults:\n  - knife_wuji_fingertip_precision000\n  - _self_\nasset:\n  asset_root: assets/objects/' + name + "\n  instance_id_list: ['000']\n")
    result = dict(status='frozen', scope=__doc__, dataset=name, train_count=27, test_count=2,
                  records=records, fresh_counts=counts, input_sha256=sources,
                  geometry_sha256=previous['geometry_sha256'], source_sha256=sha(Path(__file__)),
                  separation=separation, separation_thresholds=dict(position_m=.005, rotation_rad=.05),
                  artifact_sha256={str(path.relative_to(root)): sha(path) for path in cache.rglob('*') if path.is_file()},
                  next_gate='Unchanged runtime and physical checks before any new training; no modification of functional20 comparisons')
    (cache / 'dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (base / 'functional27-dataset-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    for name, digest in previous['artifact_sha256'].items():
        assert sha(root / name) == digest
    print(json.dumps(dict(dataset=result['dataset'], train=27, test=2, separation=separation)))


if __name__ == '__main__':
    main()
