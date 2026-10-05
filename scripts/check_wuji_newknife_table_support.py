"""Passive initial table support diagnosis; no hand, no demo or policy claim."""
from isaacgym import gymapi
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

def main():
 p=argparse.ArgumentParser();p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 g=gymapi.acquire_gym();s=gymapi.SimParams();s.dt=1/240;s.gravity=gymapi.Vec3(0,0,-9.81);s.up_axis=gymapi.UP_AXIS_Z;s.physx.use_gpu=True;s.physx.solver_type=1;s.physx.num_position_iterations=8;s.physx.num_velocity_iterations=2;s.physx.contact_offset=.001;s.physx.rest_offset=0
 sim=g.create_sim(0,-1,gymapi.SIM_PHYSX,s);opt=gymapi.AssetOptions();opt.fix_base_link=True;table=g.create_box(sim,.60,.80,.05,opt);opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;asset=g.load_asset(sim,str(a.asset.resolve().parent),a.asset.name,opt);cases=[]
 for x,y in [(x,y) for x in [.306,.310,.314] for y in [-.6295,-.6255]]:
  env=g.create_env(sim,gymapi.Vec3(-2,-2,-2),gymapi.Vec3(2,2,2),3);t=gymapi.Transform();t.p=gymapi.Vec3(.60,-.23,.725);g.create_actor(env,table,t,'table',len(cases),0);t.p=gymapi.Vec3(x,y,.7541);q=(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat();t.r=gymapi.Quat(*q);knife=g.create_actor(env,asset,t,'knife',len(cases),0)
  props=g.get_actor_dof_properties(env,knife);props['driveMode'][:]=gymapi.DOF_MODE_VEL;props['damping'][:]=25000;props['effort'][:]=.73549875;props['friction'][:]=.001;props['armature'][:]=.001;g.set_actor_dof_properties(env,knife,props);g.set_actor_dof_velocity_targets(env,knife,np.zeros(1,np.float32));ds=np.zeros(1,dtype=gymapi.DofState.dtype);g.set_actor_dof_states(env,knife,ds,gymapi.STATE_ALL)
  props=g.get_actor_rigid_shape_properties(env,knife)
  for p in props:p.friction=1.8;p.filter=1
  g.set_actor_rigid_shape_properties(env,knife,props)
  masses=[dict(mass=p.mass,com=[p.com.x,p.com.y,p.com.z]) for p in g.get_actor_rigid_body_properties(env,knife)]
  cases.append(dict(x=x,y=y,env=env,knife=knife,states=[],mass_properties=masses,contacts=[]))
 g.prepare_sim(sim)
 for k in range(240):
  g.simulate(sim);g.fetch_results(sim,True)
  if k in [0,23,47,119,239]:
   for c in cases:
    b=g.get_actor_rigid_body_states(c['env'],c['knife'],gymapi.STATE_ALL)[0];p=b['pose']['p'];q=b['pose']['r'];c['states'].append(dict(t=(k+1)/240,p=[float(p[v]) for v in ['x','y','z']],q=[float(q[v]) for v in ['x','y','z','w']]))
    if k==0:
     for z in g.get_env_rigid_contacts(c['env']):c['contacts'].append(dict(body0=int(z['body0']),body1=int(z['body1']),normal_force=float(z['lambda']),local0=[float(z['localPos0'][v]) for v in ['x','y','z']],local1=[float(z['localPos1'][v]) for v in ['x','y','z']]))
 for c in cases:del c['env'];del c['knife'];c['stayed_on_table']=c['states'][-1]['p'][2]>.75
 (a.output/'results.json').write_text(json.dumps(cases,indent=2));print(json.dumps([{k:v for k,v in c.items() if k not in ['contacts','states']} for c in cases],indent=2));g.destroy_sim(sim)
if __name__=='__main__':main()
