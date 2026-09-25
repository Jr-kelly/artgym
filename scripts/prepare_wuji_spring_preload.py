"""Probe low-gain initial targets using the old grasp's proportional spring error.

This uses Kp * (command - measured q) as a diagnostic estimate, not measured
joint torque. Saved velocities, friction and actuator dynamics are not matched.
Only commanded targets change; measured q, object and geometry remain fixed.
Select on 33 training grasps, then report all five validation grasps separately.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml
from scripts.wuji_kinematics import ROOT, WujiKinematics


def target_values(states, old_kp, new_kp, ratio_fraction, support_only):
    if ratio_fraction == 0:
        return states[:, 20:40].copy()
    measured, original = states[:, :20], states[:, 20:40]
    estimate = (original-measured)*old_kp
    requested = measured+ratio_fraction*estimate/new_kp
    hand = WujiKinematics()
    result = np.clip(requested, np.maximum(hand.lower, original-.35),
                     np.minimum(hand.upper, original+.35))
    if support_only:
        result[:, 16:] = original[:, 16:]
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--selection', type=Path)
    args=parser.parse_args()
    assert not args.output.exists(), 'Preserve previous probes'
    args.output.mkdir(parents=True)
    split='test' if args.selection else 'train'
    path=ROOT/f'caches/initial_grasp/wuji/knife_wuji_fingertip/000/{split}/valid_grasps.npy'
    states=np.load(path)
    assert states.shape==(5 if args.selection else 33,75)
    old_path=ROOT/'isaacgymenvs/cfg/hand/wuji.yaml'
    new_path=ROOT/'isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml'
    old=np.array(yaml.safe_load(old_path.read_text())['dof_props']['stiffness'])
    new=np.array(yaml.safe_load(new_path.read_text())['dof_props']['stiffness'])
    settings=[dict(fraction=0.,support_only=False)]+[
        dict(fraction=f,support_only=only) for f in [.025,.05,.1,.2] for only in [False,True]]
    if args.selection:
        selection=json.loads(args.selection.read_text())
        assert selection['status']=='selected_on_training_only'
        settings=[selection['setting']]
    arrays,records=[],[]
    for index,setting in enumerate(settings):
        result=states.copy()
        result[:,20:40]=target_values(states,old,new,setting['fraction'],setting['support_only'])
        assert np.array_equal(result[:,:20],states[:,:20]) and np.array_equal(result[:,40:],states[:,40:])
        assert np.max(abs(result[:,20:40]-states[:,20:40]))<=.350001
        for row in range(len(states)):
            records.append(dict(env=len(records),setting_index=index,source_row=row,
                target_shift_l2=float(np.linalg.norm(result[row,20:40]-states[row,20:40])),
                target_shift_abs_max=float(np.max(abs(result[row,20:40]-states[row,20:40])))))
        arrays.append(result)
    result=np.concatenate(arrays)
    np.save(args.output/'initial_states.npy',result)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,old_path,new_path,Path(__file__)]}
    manifest=dict(scope=__doc__,settings=settings,split=split,source_grasps=len(states),records=records,
                  expected_object_asset_root='assets/objects/knife_wuji_fingertip',
                  expected_object_urdf_sha256=hashlib.sha256((ROOT/'assets/objects/knife_wuji_fingertip/000/mobility.urdf').read_bytes()).hexdigest(),
                  sources=hashes,states_sha256=hashlib.sha256((args.output/'initial_states.npy').read_bytes()).hexdigest(),
                  target_shift_cap_rad=.35,
                  selection_sha256=hashlib.sha256(args.selection.read_bytes()).hexdigest() if args.selection else None,
                  selection_rule='Maximize training stable20s count, then minimize mean target shift L2, then setting index. Preserve every failed row.')
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(split=split,settings=len(settings),states=len(result))))


if __name__=='__main__':
    main()
