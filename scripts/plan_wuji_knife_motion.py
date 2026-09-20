"""Plan a thumb-only contact trajectory from a measured, stable grasp."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.build_wuji_knife_demo import GraspBuilder
from scripts.refine_wuji_knife_grasp import thumb_contact
from scripts.wuji_kinematics import ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rollout',type=Path,default=ROOT/'tmp/knife-demo/refined-hold/rollout.npz')
    p.add_argument('--source',type=Path,default=ROOT/'tmp/knife-demo/refined.npz')
    p.add_argument('--candidate-index',type=int,default=32)
    p.add_argument('--all',action='store_true')
    p.add_argument('--output',type=Path,default=ROOT/'tmp/knife-demo/motion')
    p.add_argument('--depth',type=float,default=.004)
    p.add_argument('--x-offset',type=float,default=0)
    p.add_argument('--y-offset',type=float,default=.008)
    p.add_argument('--travel',type=float,default=.045)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    result=np.load(args.rollout);source=np.load(args.source)
    hr=Rotation.from_quat([.5,-.5,.5,.5])
    meta=json.loads((ROOT/'assets/objects/knife_wuji_demo/000/parameters.json').read_text())
    builder=GraspBuilder(meta)
    selected=result['candidate_ids'] if args.all else [args.candidate_index]
    initials,commands,centers,rotations,sliders=[],[],[],[],[]
    paths,desireds,error_sets=[],[],[]
    time=np.linspace(0,12,121)
    for candidate in selected:
        idx=np.where(result['candidate_ids']==candidate)[0][0]
        state=result['states'][-1,idx]
        center=hr.inv().apply(state[1:4]-[0,0,.5])
        rotation=hr.inv()*Rotation.from_quat(state[4:8])
        command=source['targets'][candidate].copy() if 'targets' in source else source['qpos'][candidate].copy()
        initials.append(state[14:-1]);commands.append(command);centers.append(center)
        rotations.append(rotation.as_quat());sliders.append(state[-1])
        qs,desired,errors=[],[],[];q=command.copy()
        for t in time:
            if t < 1: s=state[-1]
            elif t < 5: s=state[-1]+(args.travel-state[-1])*(1-np.cos(np.pi*(t-1)/4))/2
            elif t < 6: s=args.travel
            elif t < 10: s=args.travel+(-.004-args.travel)*(1-np.cos(np.pi*(t-6)/4))/2
            else: s=-.004
            q,err=thumb_contact(builder,q,center,rotation.as_matrix(),s,args.depth,(args.x_offset,args.y_offset))
            if t < 1:
                weight=(1-np.cos(np.pi*t))/2
                q=command*(1-weight)+q*weight
            qs.append(q.copy());desired.append(s);errors.append(err)
        paths.append(qs);desireds.append(desired);error_sets.append(errors)
        print('candidate',candidate,'maximum IK error mm',max(errors)*1000,flush=True)
    np.savez(args.output/'initial.npz',qpos=initials,targets=commands,centers=centers,rotations=rotations,slider=sliders)
    np.savez(args.output/'trajectory.npz',time=time,qpos=np.array(paths).transpose(1,0,2),
             desired_slider=np.array(desireds).T,ik_error=np.array(error_sets).T)


if __name__=='__main__':
    main()
