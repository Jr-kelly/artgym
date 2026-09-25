"""Audit continuous thumb reach from the actual frozen functional grasps.

The legacy reach gate can move to a different initial thumb posture. Reuse the
previously defined fixed-material-point, bounded-step IK diagnostic to test
continuity without changing the dataset or its existing pass/fail decisions.
Kinematic failure is not proof of mechanical impossibility; success is not
contact-dynamics or RL success. No test state is selected for training here.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.audit_wuji_reach_continuity import anchored_path
from scripts.filter_wuji_fingertip_grasps import ThumbReach


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    assert not args.output.exists()
    root = Path(__file__).resolve().parents[1]
    name = 'knife_wuji_lowgain_functional27_20260922'
    cache = root / 'caches/initial_grasp/wuji' / name / '000'
    metadata_path = root / 'assets/objects' / name / '000/parameters.json'
    metadata = json.loads(metadata_path.read_text())
    reach = ThumbReach()
    records = []
    for split in ['train', 'test']:
        states = np.load(cache / split / 'valid_grasps.npy')
        for index, state in enumerate(states):
            legacy = reach.check(state, metadata)
            path = np.asarray(legacy['thumb_path_rad'])
            continuous = anchored_path(reach, state, metadata)
            sequence = np.asarray(continuous['thumb_path_rad'])
            # actionsMovingAverage=1, thumbActionStep=.025 and control_dt=1/30.
            # This is an ideal command-rate bound for this particular path,
            # excluding tracking error, force, contact, acceleration and holds.
            duration = float(np.max(np.abs(np.diff(sequence[:41], axis=0)), axis=1).sum() / .75)
            item = dict(split=split, dataset_row=index, legacy_pass=legacy['passed'],
                        legacy_initial_joint_jump_rad=float(np.abs(path[0] - state[16:20]).max()),
                        legacy_waypoint_joint_jump_rad=float(np.abs(np.diff(path, axis=0)).max()) if len(path) > 1 else None,
                        continuous=continuous,
                        ideal_opening_command_duration_bound_sec=duration if continuous['passed'] else None)
            records.append(item)
            summary = {key: value for key, value in item.items() if key != 'continuous'}
            summary.update(continuous_pass=continuous['passed'], points=continuous['points'])
            print(json.dumps(summary), flush=True)
    sources = [Path(__file__), Path(__file__).with_name('audit_wuji_reach_continuity.py'),
               Path(__file__).with_name('filter_wuji_fingertip_grasps.py'), metadata_path,
               cache / 'train/valid_grasps.npy', cache / 'test/valid_grasps.npy']
    result = dict(status='completed', scope=__doc__, dataset=name, records=records,
                  counts={split: dict(total=sum(row['split'] == split for row in records),
                                      continuous_pass=sum(row['split'] == split and row['continuous']['passed'] for row in records))
                          for split in ['train', 'test']},
                  rate_bound=dict(thumb_action_step_rad=.025, control_dt_sec=1/30, moving_average=1.),
                  sources={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources})
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['counts']), flush=True)


if __name__ == '__main__':
    main()
