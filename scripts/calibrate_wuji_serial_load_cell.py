"""Bidirectional calibrated known force through isolated series spring; full-rate residuals."""
from isaacgym import gymapi,gymtorch
import argparse,json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation

def run(asset_path,angle,moving=False,implicit=False):
 par=json.loads((asset_path.parent/'parameters.json').read_text())['serial_load_cell'];gym=gymapi.acquire_gym();sp=gymapi.SimParams();hz=240 if implicit else 960;sp.dt=1/hz;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2
 sim=gym.create_sim(0,-1,gymapi.SIM_PHYSX,sp);assert sim;env=gym.create_env(sim,gymapi.Vec3(-1,-1,-1),gymapi.Vec3(1,1,1),1);opt=gymapi.AssetOptions();opt.fix_base_link=not moving;opt.disable_gravity=False;opt.collapse_fixed_joints=False;opt.override_com=False;opt.override_inertia=False;asset=gym.load_asset(sim,str(asset_path.resolve().parent),asset_path.name,opt);pose=gymapi.Transform();pose.r=gymapi.Quat(*Rotation.from_euler('y',angle,degrees=True).as_quat());actor=gym.create_actor(env,asset,pose,'load_cell_fixture',0,0)
 shapes=gym.get_actor_rigid_shape_properties(env,actor)
 for shape in shapes:shape.filter=1;shape.friction=0.
 gym.set_actor_rigid_shape_properties(env,actor,shapes)
 names=gym.get_actor_dof_names(env,actor);bodies=gym.get_actor_rigid_body_names(env,actor);guide=names.index('slider');cell=names.index('serial_load_cell');cap=bodies.index('link_1');props=gym.get_actor_dof_properties(env,actor);props['driveMode'][:]=gymapi.DOF_MODE_EFFORT;props['damping'][:]=0;props['stiffness'][:]=0;props['friction'][:]=0;props['armature'][:]=0;props['driveMode'][guide]=gymapi.DOF_MODE_VEL;props['damping'][guide]=250;props['effort'][guide]=10;
 if implicit:props['driveMode'][cell]=gymapi.DOF_MODE_POS;props['stiffness'][cell]=par['spring_N_per_m'];props['damping'][cell]=par['damper_N_s_per_m'];props['effort'][cell]=10.
 gym.set_actor_dof_properties(env,actor,props);gym.set_actor_dof_position_targets(env,actor,np.zeros(2,np.float32));gym.set_actor_dof_velocity_targets(env,actor,np.zeros(2,np.float32));state=np.zeros(2,dtype=gymapi.DofState.dtype);state['pos'][guide]=(props['lower'][guide]+props['upper'][guide])/2;gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL)
 gym.prepare_sim(sim);d=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));ef=torch.zeros((len(bodies),3));et=torch.zeros_like(ef);motor=torch.zeros(2);axis=Rotation.from_euler('y',angle,degrees=True).apply([0,0,1]);rows=[];oldvel=np.zeros(3)
 for step in range(9*hz):
  gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);oldvel=rb[cap,7:10].numpy().copy();seg=step//hz;known=[0,.15,-.15,.3,-.3,.6,-.6,0,0][seg];known=known+.05*np.sin(step/hz*5) if seg==8 else known
  if moving:axis=Rotation.from_quat(rb[0,3:7].numpy()).apply([0,0,1])
  spring=-par['spring_N_per_m']*float(d[cell,0])-par['damper_N_s_per_m']*float(d[cell,1]);assert abs(spring)<10;motor[cell]=0. if implicit else spring;ef[:]=0;ef[cap]=torch.tensor(axis*known,dtype=torch.float32);
  if moving:
   ef[0]=torch.tensor([.02*np.sin(step/hz*3),0.,.035*9.81+.01*np.cos(step/hz*2)],dtype=torch.float32);et[0,1]=.000001*np.sin(step/hz*4)
  gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(ef),gymtorch.unwrap_tensor(et),gymapi.ENV_SPACE);gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(motor));gym.simulate(sim);gym.fetch_results(sim,True);gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);acc=(rb[cap,7:10].numpy()-oldvel)*hz
  if implicit:spring=np.clip(-par['spring_N_per_m']*float(d[cell,0])-par['damper_N_s_per_m']*float(d[cell,1]),-10.,10.)
  inferred=par['cap_mass_kg']*float(acc@axis)-par['cap_mass_kg']*float(np.array([0,0,-9.81])@axis)-spring
  rows.append([step/hz,seg,known,float(d[cell,0]),float(d[cell,1]),spring,inferred,inferred-known,float(acc@axis)])
 gym.destroy_sim(sim);z=np.array(rows);return z,dict(angle_degrees=angle,moving_base=moving,implicit_native_spring=implicit,physics_hz=hz,mean_abs_residual_N=float(abs(z[:,7]).mean()),max_abs_residual_N=float(abs(z[:,7]).max()),steady_max_abs_residual_N=float(abs(z[(z[:,0]%1)>.5,7]).max()),deflection_peak_mm=float(abs(z[:,3]).max()*1000),passed=bool(abs(z[:,7]).max()<.02))
def main():
 p=argparse.ArgumentParser();p.add_argument('--implicit-cell',action='store_true',help='Native passive zero-rest spring with qpost/vpost force reconstruction, validatebeforeusing240Hztask');p.add_argument('--moving-base-only',action='store_true');p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[]
 for angle in ([45] if a.moving_base_only else [0,90,45]):
  z,r=run(a.asset,angle,moving=a.moving_base_only,implicit=a.implicit_cell);np.savez_compressed(a.output/('angle%d.npz'%angle),samples=z,columns=['time_s','segment','known_force_N','cell_q_m','cell_v_m_s','spring_applied_N','inferred_external_axial_N','residual_N','cap_world_acc_axis_m_s2']);rows.append(r)
 report=dict(scope='Isolated serial elastic diagnostic calibration, not original knife contact/hardware. Signed world acceleration and gravity included; known external load independently commanded, not brakecapacity. Explicit actualcommand or implicit reconstructedqpost/vpost native spring force; integrationHz explicitinrows, no calibration inferredbefore pass. No contactor endstop allowed.',rows=rows,passed=all(r['passed'] for r in rows));(a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['passed']
if __name__=='__main__':main()
