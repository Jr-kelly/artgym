"""Bidirectional calibrated known force through isolated series spring; full-rate residuals."""
from isaacgym import gymapi,gymtorch
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation

def run(asset_path,angle):
 par=json.loads((asset_path.parent/'parameters.json').read_text())['serial_load_cell'];gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/960;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2
 sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim;env=gym.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1);opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=False;opt.collapse_fixed_joints=False;asset=gym.load_asset(sim,str(asset_path.resolve().parent),asset_path.name,opt);pose=gymapi.Transform();pose.r=gymapi.Quat(*Rotation.from_euler('y',angle,degrees=True).as_quat());actor=gym.create_actor(env,asset,pose,'load_cell_fixture',0,0)
 names=gym.get_actor_dof_names(env,actor);bodies=gym.get_actor_rigid_body_names(env,actor);guide=names.index('slider');cell=names.index('serial_load_cell');cap=bodies.index('link_1');props=gym.get_actor_dof_properties(env,actor);props['driveMode'][:]=gymapi.DOF_MODE_EFFORT;props['damping'][:]=0;props['stiffness'][:]=0;props['friction'][:]=0;props['armature'][:]=0;props['driveMode'][guide]=gymapi.DOF_MODE_VEL;props['damping'][guide]=250;props['effort'][guide]=10;gym.set_actor_dof_properties(env,actor,props);gym.set_actor_dof_velocity_targets(env,actor,np.zeros(2,np.float32));state=np.zeros(2,dtype=gymapi.DofState.dtype);state['pos'][guide]=(props['lower'][guide]+props['upper'][guide])/2;gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL)
 gym.prepare_sim(sim);d=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));ef=torch.zeros((len(bodies),3));motor=torch.zeros(2);axis=Rotation.from_euler('y',angle,degrees=True).apply([0,0,1]);rows=[];oldvel=np.zeros(3)
 for step in range(8640):
  gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);oldvel=rb[cap,7:10].numpy().copy();seg=step//960;known=[0,.15,-.15,.3,-.3,.6,-.6,0,0][seg];known=known+.05*np.sin(step/960*5) if seg==8 else known
  spring=-par['spring_N_per_m']*float(d[cell,0])-par['damper_N_s_per_m']*float(d[cell,1]);assert abs(spring)<10;motor[cell]=spring;ef[:]=0;ef[cap]=torch.tensor(axis*known,dtype=torch.float32);gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(ef),None,gymapi.ENV_SPACE);gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(motor));gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);acc=(rb[cap,7:10].numpy()-oldvel)*960;inferred=par['cap_mass_kg']*float(acc@axis)-par['cap_mass_kg']*float(np.array([0,0,-9.81])@axis)-spring
  rows.append([step/960,seg,known,float(d[cell,0]),float(d[cell,1]),spring,inferred,inferred-known,float(acc@axis)])
 gym.destroy_sim(sim);z=np.array(rows);return z,dict(angle_degrees=angle,mean_abs_residual_N=float(abs(z[:,7]).mean()),max_abs_residual_N=float(abs(z[:,7]).max()),steady_max_abs_residual_N=float(abs(z[(z[:,0]%1)>.5,7]).max()),deflection_peak_mm=float(abs(z[:,3]).max()*1000),passed=bool(abs(z[:,7]).max()<.02))
def main():
 p=argparse.ArgumentParser();p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[]
 for angle in [0,90,45]:
  z,r=run(a.asset,angle);np.savez_compressed(a.output/('angle%d.npz'%angle),samples=z,columns=['time_s','segment','known_force_N','cell_q_m','cell_v_m_s','spring_applied_N','inferred_external_axial_N','residual_N','cap_world_acc_axis_m_s2']);rows.append(r)
 report=dict(scope='Isolated serial elastic diagnostic calibration, not original knife contact/hardware. Signed world acceleration and gravity included; known external load independently commanded, not brakecapacity. Spring/damper exactcommand recorded960Hz. No contactor endstop allowed.',rows=rows,passed=all(r['passed'] for r in rows));(a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['passed']
if __name__=='__main__':main()
