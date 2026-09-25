"""Export stable contact measurements as candidates for ArtGrasp validation.

This does not create valid_grasps.npy; the original validator must approve them.
"""
import argparse
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.wuji_kinematics import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rollout',type=Path,default=ROOT/'tmp/knife-demo/refined-hold/rollout.npz')
    p.add_argument('--source',type=Path,default=ROOT/'tmp/knife-demo/refined.npz')
    p.add_argument('--output',type=Path,default=ROOT/'caches/initial_grasp/wuji/knife_wuji_demo/000')
    p.add_argument('--count',type=int,default=64)
    p.add_argument('--support-fingers',type=int,default=3)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    result=np.load(args.rollout);source=np.load(args.source)
    contact=result['contacts'][len(result['contacts'])//2:].mean(0)
    candidates=np.where((contact[:,0]>.9)&((contact[:,1:]>.9).sum(1)>=args.support_fingers))[0]
    if len(candidates)==0: raise RuntimeError('No candidates with sufficient sustained thumb/handle contact')
    hr=Rotation.from_quat([.5,-.5,.5,.5]);rng=np.random.default_rng(42)
    qs,poses=[],[]
    for i in range(args.count):
        idx=candidates[i%len(candidates)];state=result['states'][-1,idx]
        source_idx=result['candidate_ids'][idx]
        q=source['targets'][source_idx].copy()
        if i>=len(candidates): q+=rng.normal(0,.001,20)
        pose=np.eye(4)
        pose[:3,:3]=(hr.inv()*Rotation.from_quat(state[4:8])).as_matrix()
        pose[:3,3]=hr.inv().apply(state[1:4]-[0,0,.5])
        qs.append(q);poses.append(pose)
    np.save(args.output/'qpos.npy',np.array(qs,dtype=np.float32))
    np.save(args.output/'opos.npy',np.array(poses,dtype=np.float32))
    print('Exported',len(qs),'raw candidates from',len(candidates),'measured grasps')


if __name__=='__main__':
    main()
