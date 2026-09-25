"""Check binary GJK against separated boxes and inspect Sharpa rest-pose meshes."""
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
import trimesh
from lygra import gem
from lygra.robot.sharpa import Sharpa
from lygra.kinematics import build_kinematics_tree, batch_fk
from lygra.mesh import get_urdf_mesh_decomposed
from lygra.pipeline.module.collision import batch_hand_self_collision_check

box=trimesh.creation.box(extents=(.02,.02,.02))
v=torch.tensor(np.concatenate([box.vertices]*2),device='cuda',dtype=torch.float32)
vi=torch.tensor([0,8,16],device='cuda',dtype=torch.int32)
pairs=torch.tensor([[0,1]],device='cuda',dtype=torch.int32)
pose=torch.eye(4,device='cuda')[None,None].repeat(3,2,1,1)
pose[:,1,0,3]=torch.tensor([0.,.015,.1],device='cuda')
print('BOX_HITS',gem.batch_link_mesh_gjk(pose,v,vi,pairs).cpu().tolist(),flush=True)
robot=Sharpa();tree=build_kinematics_tree(robot.urdf_path,active_joint_names=robot.get_active_joints())
mesh=get_urdf_mesh_decomposed(robot.urdf_path,tree)
np_pairs=tree.get_self_collision_check_link_pairs(mesh['link_body_id'])
q=torch.tensor(tree.get_resting_q(),device='cuda')[None]
mask,hits,vertices=batch_hand_self_collision_check(tree,q,torch.tensor(np_pairs,device='cuda'),mesh=mesh)
fk=batch_fk(tree,q)['link'][0].cpu().numpy()
rows=[]
for body,linkid in enumerate(mesh['body_id_to_link_id']):
    a,b=mesh['vi'][body:body+2];local=mesh['v'][a:b]
    world=local@fk[linkid,:3,:3].T+fk[linkid,:3,3]
    rows.append(dict(body=body,link=tree.links[linkid],n_vertices=len(local),
                     world_bounds=[world.min(0).tolist(),world.max(0).tolist()] if len(local) else None))
print('REST',json.dumps(dict(q=q.cpu().tolist(),passed=mask.cpu().tolist(),bodies=rows,
    collision_links=[rows[i]['link'] for i in torch.where(hits[0])[0].cpu().tolist()])),flush=True)
valid_pairs=np_pairs[np.all(np.diff(mesh['vi'])[np_pairs]>0,axis=1)]
mask,hits,_=batch_hand_self_collision_check(tree,q,torch.tensor(valid_pairs,device='cuda'),mesh=mesh)
print('NONEMPTY_REST',json.dumps(dict(passed=mask.cpu().tolist(),
    collision_links=[rows[i]['link'] for i in torch.where(hits[0])[0].cpu().tolist()])),flush=True)

for a,b in valid_pairs:
    out=gem.batch_link_mesh_gjk(batch_fk(tree,q)["link"][:,mesh["body_id_to_link_id"]],torch.tensor(mesh["v"],device="cuda",dtype=torch.float32),torch.tensor(mesh["vi"],device="cuda",dtype=torch.int32),torch.tensor([[a,b]],device="cuda",dtype=torch.int32))
    if out.any():print("HIT_PAIR",rows[a]["link"],rows[b]["link"],flush=True)
