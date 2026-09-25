"""Compare native and chunked projection on real Wuji/Sharpa mesh geometry."""
import json
import os
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT/'func_lygra');sys.path.insert(0,str(Path.cwd()))
for name,value in [('float',float),('int',int),('bool',bool),('complex',complex),('object',object)]:
    if name not in np.__dict__:setattr(np,name,value)
import torch
import yaml
from scripts_official_adapter import install_adapters
from projection_memory import project_in_chunks
from lygra import gem
from lygra.robot import build_robot
from lygra.kinematics import build_kinematics_tree,batch_fk
from lygra.mesh import get_urdf_mesh_for_projection

os.environ.pop('ARTGYM_PROJECTION_CHUNK',None)
install_adapters(ROOT)
torch.manual_seed(2718)
results=[]
for name,config_name in [('wuji_artbot','knife_wuji_artbot'),('sharpa','knife')]:
    robot=build_robot(name)
    tree=build_kinematics_tree(robot.urdf_path,active_joint_names=robot.get_active_joints())
    cfg=yaml.safe_load((ROOT/f'func_lygra/configs/object/{config_name}.yaml').read_text())
    config=robot.get_contact_field_config(cfg['digits'][name])
    mesh=get_urdf_mesh_for_projection(robot.urdf_path,tree,config,mesh_scale=robot.get_mesh_scale())
    v=torch.as_tensor(mesh['v'],device='cuda',dtype=torch.float32)
    vi=torch.as_tensor(mesh['vi'],device='cuda',dtype=torch.int32)
    f=torch.as_tensor(mesh['f'],device='cuda',dtype=torch.int32)
    n=torch.as_tensor(mesh['n'],device='cuda',dtype=torch.float32)
    fi=torch.as_tensor(mesh['fi'],device='cuda',dtype=torch.int32)
    links=np.flatnonzero(np.diff(mesh['fi'])>0)[:5]
    assert len(links)==5
    count=259  # Multiple chunks plus a tail.
    q=torch.as_tensor(tree.get_resting_q(),device='cuda')[None].repeat(count,1)
    q=q+torch.rand_like(q)*0.08
    pose=batch_fk(tree,q)['link']
    link_ids=torch.as_tensor(links,device='cuda',dtype=torch.int32)[None].repeat(count,1)
    local=torch.stack([v[int(mesh['vi'][i]):int(mesh['vi'][i+1])].mean(0) for i in links])
    selected=pose[:,links]
    query=(selected[:,:,:3,:3]@local[None,:,:,None]).squeeze(-1)+selected[:,:,:3,3]
    query=query+torch.rand_like(query)*0.01
    normal=torch.nn.functional.normalize(torch.rand_like(query)-0.5,dim=-1)
    for weight in (0.0,0.01):
        for to_link in (True,False):
            args=(pose,link_ids,v,vi,f,n,fi,query,normal,to_link,weight)
            expected=gem.batch_solve_contact_with_normal(*args)
            actual=project_in_chunks(gem.batch_solve_contact_with_normal,128,*args)
            error=float((expected-actual).abs().max())
            assert torch.isfinite(expected).all() and torch.isfinite(actual).all()
            torch.testing.assert_close(actual,expected,rtol=0,atol=0)
            results.append(dict(robot=name,candidates=count,contacts=5,chunk_size=128,
                                to_link_frames=to_link,orientation_weight=weight,max_abs_error=error))
destination=ROOT/'runs/experiment-suite/projection-chunking-audit.json'
destination.write_text(json.dumps(dict(passed=True,cases=results),indent=2)+'\n')
print(destination.read_text())
