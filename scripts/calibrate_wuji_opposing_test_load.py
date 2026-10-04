"""Known balanced test-force sign/units on the original free knife.

Isolated short impulses use an unbraked mid-rail fixture to remove unknown
guide reaction and endstops. This calibrates commanded test loads, not thumb
force or passive-brake actual reaction in the task.
"""
from isaacgym import gymapi,gymtorch
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation

R=Path(__file__).resolve().parents[1]

def run(angle,known):
 gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2
 sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);env=gym.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1);opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;opt.override_com=False;opt.override_inertia=False;asset=gym.load_asset(sim,str(R/'assets/objects/knife_wuji_real_size_20261002/000'),'mobility.urdf',opt);pose=gymapi.Transform();pose.r=gymapi.Quat(*Rotation.from_euler('y',angle,degrees=True).as_quat());actor=gym.create_actor(env,asset,pose,'isolated_original_knife',0,0)
 shapes=gym.get_actor_rigid_shape_properties(env,actor)
 for s in shapes:s.filter=1;s.friction=0
 gym.set_actor_rigid_shape_properties(env,actor,shapes);props=gym.get_actor_dof_properties(env,actor);props['driveMode'][:]=gymapi.DOF_MODE_EFFORT
 for field in ['damping','stiffness','friction','armature']:props[field][:]=0
 gym.set_actor_dof_properties(env,actor,props);state=np.zeros(1,dtype=gymapi.DofState.dtype);state['pos'][0]=(props['lower'][0]+props['upper'][0])/2;gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL);gym.prepare_sim(sim)
 rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));d=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));bodies=gym.get_actor_rigid_body_names(env,actor);base=bodies.index('link_0');cap=bodies.index('link_1');mass=gym.get_actor_rigid_body_properties(env,actor)[cap].mass;ef=torch.zeros((len(rb),3));et=torch.zeros_like(ef);rows=[]
 for step in range(10):
  gym.refresh_rigid_body_state_tensor(sim);axis=Rotation.from_quat(rb[base,3:7].numpy()).apply([0,0,1]);old=rb[cap,7:10].numpy().copy();f=axis*known;r=rb[cap,:3].numpy()-rb[base,:3].numpy();ef[:]=0;et[:]=0;ef[cap]=torch.tensor(f,dtype=torch.float32);ef[base]=torch.tensor(-f,dtype=torch.float32);et[base]=torch.tensor(np.cross(r,-f),dtype=torch.float32);netforce=(ef.sum(0)).numpy();netmoment=np.cross(r,f)+et[base].numpy();gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(ef),gymtorch.unwrap_tensor(et),gymapi.ENV_SPACE);gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_dof_state_tensor(sim);acc=(rb[cap,7:10].numpy()-old)*240;inferred=mass*(float(acc@axis)-float(np.array([0,0,-9.81])@axis));rows.append(dict(time_s=(step+1)/240,commanded_cap_axial_N=known,unbraked_cap_acceleration_inferred_N=inferred,residual_N=inferred-known,rail_position_m=float(d[0,0]),balanced_net_force_N=netforce.tolist(),balanced_net_moment_Nm=netmoment.tolist()))
 gym.destroy_sim(sim);res=max(abs(z['residual_N']) for z in rows);clear=all(props['lower'][0]+.002<z['rail_position_m']<props['upper'][0]-.002 for z in rows);return dict(angle_degrees=angle,known_N=known,cap_mass_kg=mass,rows=rows,maximum_residual_N=res,no_endstop=clear,passed=res<.002 and clear)

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 rows=[run(angle,force) for angle in [0,45,90] for force in [-.1,.05,.1]];result=dict(scope=__doc__,rows=rows,passed=all(r['passed'] for r in rows));(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=result['passed'],maximum_residual_N=max(r['maximum_residual_N'] for r in rows))));assert result['passed']

if __name__=='__main__':main()
