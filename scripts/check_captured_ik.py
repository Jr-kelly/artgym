"""Independently measure the contact residuals of rejected official candidates."""
import os
from pathlib import Path
import sys
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT/'func_lygra');sys.path.insert(0,str(Path.cwd()))
for name,value in [('float',float),('int',int),('bool',bool),('complex',complex),('object',object)]:
    if name not in np.__dict__:setattr(np,name,value)
import torch
from lygra.robot.sharpa import Sharpa
from lygra.kinematics import build_kinematics_tree,batch_fk
from urdfpy import URDF
robot=Sharpa();tree=build_kinematics_tree(robot.urdf_path,active_joint_names=robot.get_active_joints())
data=np.load(ROOT/'runs/experiment-suite/collision-diagnostic-full.candidates.npz')
print('KEYS',data.files,flush=True)
q=torch.tensor(data['q'],device='cuda');fk=batch_fk(tree,q)['link'].cpu().numpy()
print('Q',json.dumps(dict(zip(tree.active_joints,data['q'][0].tolist()))),flush=True)
ids=data['contact_link_id'];poses=fk[np.arange(len(q))[:,None],ids]
world=np.einsum('bkij,bkj->bki',poses[...,:3,:3],data['contact_pos'])+poses[...,:3,3]
error=np.linalg.norm(world-data['target_pos'],axis=-1)
print('CONTACT_ERROR_METRES',np.quantile(error,[0,.5,.9,1]).tolist(),flush=True)
urdf=URDF.load(robot.urdf_path);independent=urdf.link_fk(dict(zip(tree.active_joints,data['q'][0])))
print('FK_MAX_DIFF',max(np.abs(pose-fk[0,tree.get_link_id(link.name)]).max() for link,pose in independent.items()),flush=True)
print('CONTACT0',[(tree.links[i],world[0,k].tolist(),data['target_pos'][0,k].tolist()) for k,i in enumerate(ids[0])],flush=True)
lo,hi=tree.get_active_joint_limit();print('LIMIT_VIOLATIONS',np.maximum(lo-data['q'],data['q']-hi).max(),flush=True)
