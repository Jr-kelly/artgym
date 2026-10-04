"""Short known-load diagnostics of native rigid sensor attribution, not a knife demo."""
from isaacgym import gymapi,gymtorch
import argparse,json
from pathlib import Path
import numpy as np
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.substeps=1;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.up_axis=gymapi.UP_AXIS_Z;sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2;sp.physx.contact_collection=gymapi.ContactCollection.CC_ALL_SUBSTEPS
 sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim
 pl=gymapi.PlaneParams();pl.normal=gymapi.Vec3(0,0,1);pl.static_friction=1.;pl.dynamic_friction=1.;gym.add_ground(sim,pl)
 env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,1),1);opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.collapse_fixed_joints=False
 urdf='<robot name="known_rail"><link name="base"><inertial><mass value="1"/><inertia ixx=".01" iyy=".01" izz=".01" ixy="0" ixz="0" iyz="0"/></inertial></link><link name="box"><inertial><mass value=".064"/><inertia ixx=".0000170667" iyy=".0000170667" izz=".0000170667" ixy="0" ixz="0" iyz="0"/></inertial><collision><geometry><box size=".04 .04 .04"/></geometry></collision></link><joint name="rail" type="prismatic"><parent link="base"/><child link="box"/><origin xyz="0 0 .025"/><axis xyz="1 0 0"/><limit lower="-.1" upper=".1" effort="2" velocity="1"/></joint></robot>'
 (a.output/'fixture.urdf').write_text(urdf);asset=gym.load_asset(sim,str(a.output.resolve()),'fixture.urdf',opt)
 modes=[('solver_only',False,True),('forward_only',True,False),('combined',True,True)]
 for label,dyn,solver in modes:
  prop=gymapi.ForceSensorProperties();prop.enable_forward_dynamics_forces=dyn;prop.enable_constraint_solver_forces=solver;prop.use_world_frame=True
  assert gym.create_asset_force_sensor(asset,1,gymapi.Transform(),prop)>=0
 pose=gymapi.Transform();pose.p=gymapi.Vec3(0,0,.1);actor=gym.create_actor(env,asset,pose,'known_free_box',0,0);mass=gym.get_actor_rigid_body_properties(env,actor)[1].mass
 props=gym.get_actor_dof_properties(env,actor);props['driveMode'][:]=gymapi.DOF_MODE_VEL;props['damping'][:]=250.;props['stiffness'][:]=0.;props['effort'][:]=.5;props['friction'][:]=0.;gym.set_actor_dof_properties(env,actor,props);gym.set_actor_dof_velocity_targets(env,actor,np.zeros(1,np.float32))
 print({'sensor_count':gym.get_actor_force_sensor_count(env,actor)},flush=True)
 if gym.get_actor_force_sensor_count(env,actor)==0:
  report=dict(status='unavailable',reason='Installedbackend returnszero actorforce sensors despite registeredassetrequests; do notinterpret aszero contactforce',sensor_modes=modes);(a.output/'report.json').write_text(json.dumps(report,indent=2));gym.destroy_sim(sim);return
 gym.prepare_sim(sim);rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));sensor=gymtorch.wrap_tensor(gym.acquire_force_sensor_tensor(sim));net=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));force=torch.zeros((2,3));rows=[];examples=[]
 for k in range(1440):
  segment=k//480;fx=[.15,-.15,0.][segment];force[1]=torch.tensor([fx,0.,-.4]);gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(force),None,gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_force_sensor_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim)
  cs=gym.get_env_rigid_contacts(env)
  if len(cs)>0 and len(examples)<1:
   c=cs[0];examples.append({'fields':list(c.dtype.names),'lambdaFriction':str(c['lambdaFriction']) if 'lambdaFriction' in c.dtype.names else None})
  rows.append(dict(time_s=(k+1)/240,segment=segment,external_N=[fx,0.,-.4],sensors=sensor.numpy().copy().tolist(),net=net.numpy().copy().tolist(),state=rb.numpy().copy().tolist()))
 np.savez_compressed(a.output/'raw.npz',time_s=[r['time_s'] for r in rows],external_N=[r['external_N'] for r in rows],sensor=[r['sensors'] for r in rows],net=[r['net'] for r in rows],state=[r['state'] for r in rows])
 summary=[]
 for j in range(3):
  z=rows[j*480+240:(j+1)*480];s=np.mean([r['sensors'] for r in z],axis=0);expected=np.array([-z[0]['external_N'][0],0,mass*9.81+.4]);summary.append(dict(segment=j,expected_solver_force_on_box_N=expected.tolist(),sensor_means=s.tolist(),solver_force_max_abs_error_N=float(np.max(abs(s[0,:3]-expected))),net_mean_N=np.mean([r['net'] for r in z],axis=0).tolist(),mean_velocity_m_s=np.mean([r['state'][1][7:10] for r in z],axis=0).tolist()))
 report=dict(scope='Known fixed prismatic rail body diagnostic only; includes actual native guide drive reaction; sensors include all selected body forces, not a contact pair in articulated knife. No normal/friction units redefinition.',mass_kg=mass,sensor_modes=modes,contact_record_examples=examples,segments=summary,solver_sensor_known_bidirectional_load_pass=all(r['solver_force_max_abs_error_N']<.02 for r in summary))
 (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));gym.destroy_sim(sim)
if __name__=='__main__':main()
