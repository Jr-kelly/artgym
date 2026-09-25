"""Derive a two-mode sampling audit using training joints only.

No grasp is generated, removed, relabeled, or copied from validation. The largest
gap in the training thumb's distal joint separates two kinematic postures. Equal
mass per posture keeps every original row available while testing imbalance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    path=ROOT/'caches/initial_grasp/wuji/knife_wuji_fingertip/000/train/valid_grasps.npy'
    states=np.load(path,allow_pickle=False)
    q=states[:,19];order=np.argsort(q);gaps=np.diff(q[order]);index=int(np.argmax(gaps))
    if gaps[index]<.5:
        raise ValueError('Training data do not contain the hypothesized separated thumb postures')
    threshold=float((q[order[index]]+q[order[index+1]])/2)
    groups=(q>threshold).astype(int)
    counts=np.bincount(groups,minlength=2)
    weights=.5/counts[groups]
    report=dict(protocol=__doc__,training_path=str(path.relative_to(ROOT)),
        training_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        joint_index=19,largest_gap_rad=float(gaps[index]),threshold_rad=threshold,
        group_sizes=counts.tolist(),groups=groups.tolist(),weights=weights.tolist(),
        original_uniform_group_probabilities=(counts/len(states)).tolist(),
        balanced_group_probabilities=[.5,.5],validation_data_read=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['groups','weights','protocol']}))


if __name__=='__main__':main()
