"""Refine thumb contact against the knife pose measured after a holding rollout."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from scripts.build_wuji_knife_demo import GraspBuilder
from scripts.wuji_kinematics import ROOT


def thumb_contact(builder, q, center, rotation, slider, depth=0, offset=(0,0)):
    q = np.asarray(q, dtype=np.float64)
    h = builder.hand
    normal = rotation[:,2]
    meta = builder.meta
    target = center + rotation @ (np.array(meta['slider_origin']) + [offset[0],offset[1]-slider,meta['slider_size'][2]/2-depth])
    q, _ = h.solve_finger('thumb',target,q,-normal)
    vertices = builder.vertices['hand_r_thumb_pad_link']
    def residual(values):
        p = q.copy(); p[-4:] = values
        frame = h.forward(p)['hand_r_thumb_pad_link']
        v = vertices@frame[:3,:3].T+frame[:3,3]
        point = v.mean(0)
        point += normal*(np.min(v@normal)-point@normal)
        return np.r_[(point-target)*100, (frame[:3,0]+normal)*.08]
    fit = least_squares(residual, np.clip(q[-4:],h.lower[-4:]+1e-7,h.upper[-4:]-1e-7),
                        bounds=(h.lower[-4:],h.upper[-4:]),max_nfev=100)
    q[-4:] = fit.x
    return q, np.linalg.norm(fit.fun[:3])/100


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rollout',type=Path,default=ROOT/'tmp/knife-demo/hold0/rollout.npz')
    parser.add_argument('--source',type=Path,default=ROOT/'tmp/knife-demo/candidates.npz')
    parser.add_argument('--output',type=Path,default=ROOT/'tmp/knife-demo/refined.npz')
    parser.add_argument('--candidate-index',type=int,default=0)
    args=parser.parse_args()
    result=np.load(args.rollout); original=np.load(args.source)
    idx=np.where(result['candidate_ids']==args.candidate_index)[0][0]
    state=result['states'][-1,idx]; candidate=result['candidate_ids'][idx]
    hand_r=Rotation.from_quat([.5,-.5,.5,.5])
    center=hand_r.inv().apply(state[1:4]-[0,0,.5])
    rotation=hand_r.inv()*Rotation.from_quat(state[4:8])
    meta=json.loads((ROOT/'assets/objects/knife_wuji_demo/000/parameters.json').read_text())
    builder=GraspBuilder(meta)
    qs, targets, settings=[],[],[]
    for depth in (-.002,0,.002,.004,.006):
        for x in (-.006,0,.006):
            for y in (-.008,0,.008):
                q,err=thumb_contact(builder,state[14:-1].copy(),center,rotation.as_matrix(),state[-1],depth,(x,y))
                command=original['targets'][candidate].copy() if 'targets' in original else original['qpos'][candidate].copy()
                command[-4:]=q[-4:]
                qs.append(q); targets.append(command); settings.append([depth,x,y,err])
    np.savez(args.output,qpos=qs,targets=targets,centers=np.tile(center,(len(qs),1)),
             rotations=np.tile(rotation.as_quat(),(len(qs),1)),slider=np.full(len(qs),state[-1]),parameters=settings)
    print('Saved',len(qs),'thumb refinements; knife center',center,'slider',state[-1],flush=True)


if __name__=='__main__':
    main()
