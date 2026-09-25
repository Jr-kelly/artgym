"""Measure nominal-grasp separation; never relabel or discard held-out rows."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset',default='knife_wuji_lowgain_functional20_20260922')
    parser.add_argument('--output',type=Path,default=Path('runs/wuji-goal/diagnostics/functional20-grasp-separation.json'))
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    name=args.dataset
    cache=root/'caches/initial_grasp/wuji'/name/'000'
    train=np.load(cache/'train/valid_grasps.npy');test=np.load(cache/'test/valid_grasps.npy')
    rows=[]
    for i,state in enumerate(test):
        position=np.linalg.norm(train[:,40:43]-state[40:43],axis=1)
        angle=(Rotation.from_quat(train[:,43:47])*Rotation.from_quat(state[43:47]).inv()).magnitude()
        joint=np.sqrt(((train[:,:20]-state[:20])**2).mean(1))
        near=(position<=.005)&(angle<=.05)
        k=int(np.argmin(position/.005+angle/.05))
        rows.append(dict(test_row=i,nearest_pose_train_row=k,nearest_position_m=float(position[k]),
            nearest_rotation_rad=float(angle[k]),nearest_joint_rms_rad=float(joint[k]),
            near_duplicate_pose_train_rows=np.flatnonzero(near).tolist(),
            near_pose_joint_rms_rad={str(j):float(joint[j]) for j in np.flatnonzero(near)},
            exact_duplicate_train_rows=[j for j,row in enumerate(train) if np.array_equal(row,state)]))
    payload=dict(scope=__doc__,dataset=name,train=len(train),test=len(test),records=rows,
        diagnostic_pose_thresholds=dict(position_m=.005,rotation_rad=.05),
        note='These are existing optional object-pose uniqueness thresholds, used descriptively. Near object poses can have different hand joints; joint RMS is reported separately. No split changes or success claims.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inputs={split:hashlib.sha256((cache/split/'valid_grasps.npy').read_bytes()).hexdigest() for split in ['train','test']})
    output=root/args.output
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(payload))


if __name__=='__main__':main()
