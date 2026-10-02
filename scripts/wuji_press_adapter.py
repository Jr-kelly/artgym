"""Bounded calibrated thumb target bias and independent passive prismatic effort."""
import json,math
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
from isaacgym import gymtorch
from isaacgymenvs.utils.torch_jit_utils import quat_apply

def calibrated_bias(states,mm):
 hand=WujiKinematics();delta=[];errors=[]
 for s in states:
  q=s[:20].astype(float);point=hand.contacts(q)[0][0];normal=Rotation.from_quat(s[43:47]).apply([0,1,0])
  if mm==0:new=q;err=0.
  else:new,err=hand.solve_finger('thumb',point-normal*(mm/1000),q)
  d=np.clip(new-q,-.15,.15);d[:16]=0;delta.append(d);errors.append(err)
 return np.asarray(delta),errors

def install(env,states,press_mm,resistance_n,profile,profile_seed,disable=False):
 assert press_mm>=0 and resistance_n>=0
 delta,errors=calibrated_bias(states,press_mm);bias=torch.as_tensor(delta,device=env.device,dtype=torch.float32)
 offset=torch.zeros_like(bias);env.press_diagnostics=[];env.press_force=torch.zeros(env.num_envs,device=env.device);env.press_velocity=env.press_force.clone();env.press_limit=env.press_force.clone();env.press_positive_power_max=0.;env.press_memory_error=0.
 env.press_metadata=dict(press_mm=press_mm,bias_joint_rad=delta.tolist(),ik_error_m=errors,resistance_n=resistance_n,profile=profile,profile_seed=profile_seed,normal='Fixed initial calibration +Y surface normal, never live object/slider feedback',force_proxy='Net thumb pad body contact force projected on current slider normal for diagnostics only; not an isolated thumb-slider pair force',slip_proxy='Relative thumb pad/slider body center axial velocity; not a resolved contact-point slip measurement',saturation='PD demand versus configured effort bound proxy, not measured joint torque',smoothing_velocity_mps=.02,profile_rule='constant amplitude or Fmax*(0.25+0.75*sin(2*pi*t/3.7+seed_phase)^2); seed phase=(seed%997)/997*2pi')
 pre=env.pre_physics_step
 def step(action):
  # Remove only last actually applied bias before the original recursive update.
  # The policy observation before this call still saw the final issued command.
  env.prev_targets[:,:20]-=offset
  if hasattr(env,'known_controller'):env.known_controller.issued-=offset
  pre(action)
  nominal=env.cur_targets[:,:20].clone();ramp=min(1.,max(0.,float(env.control_steps+1)/15));ramp=ramp*ramp*(3-2*ramp)
  desired=nominal+bias*ramp
  final=torch.maximum(torch.minimum(desired,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
  offset[:]=final-nominal;env.cur_targets[:,:20]=final;env.prev_targets[:,:20]=final
  if hasattr(env,'known_controller'):
   env.known_controller.issued[:]=final
   env.press_memory_error=max(env.press_memory_error,float((env.known_controller.issued-env.cur_targets[:,:20]).abs().max()))
  env.gym.set_dof_position_target_tensor(env.sim,gymtorch.unwrap_tensor(env.cur_targets))
 if not disable:env.pre_physics_step=step
 def substep(_):
  env.gym.refresh_dof_state_tensor(env.sim);v=env.obj_dof_state_vel[:,0]
  t=float(env.control_steps)*float(env.dt*env.control_freq_inv)+_*float(env.dt)
  factor=1. if profile=='constant' else .25+.75*math.sin(2*math.pi*t/3.7+(profile_seed%997)/997*2*math.pi)**2
  limit=resistance_n*factor;force=-limit*torch.tanh(v/.02)
  env.press_force[:]=force;env.press_velocity[:]=v;env.press_limit[:]=limit
  env.press_positive_power_max=max(env.press_positive_power_max,float((force*v).max()))
  env.dof_actuation_forces.zero_();env.dof_actuation_forces[:,env.num_hand_dofs]=force
  env.gym.set_dof_actuation_force_tensor(env.sim,gymtorch.unwrap_tensor(env.dof_actuation_forces))
 if not disable:env.press_physics_substep=substep
 reward=env.compute_reward
 kp=torch.as_tensor(env.hand_cfg['dof_props']['stiffness'],device=env.device);kd=torch.as_tensor(env.hand_cfg['dof_props']['damping'],device=env.device)
 props=env.gym.get_actor_dof_properties(env.envs[0],env.gym.find_actor_handle(env.envs[0],'hand'));effort=torch.as_tensor(props['effort'].copy(),device=env.device)
 def observe(action):
  reward(action)
  normal=quat_apply(env.world_object_rot,torch.tensor([0.,1.,0.],device=env.device).expand(env.num_envs,-1));axis=quat_apply(env.world_object_rot,torch.tensor([0.,0.,1.],device=env.device).expand(env.num_envs,-1))
  contact=env.contact_forces[:,env.force_handles[0]];pad=env.rigid_body_states[:,env.force_handles[0]];slider=env.rigid_body_states[:,env.object_link1_rb_handle]
  demand=kp*(env.cur_targets[:,:20]-env.hand_dof_pos)-kd*env.hand_dof_vel
  row=dict(normal_net_force_proxy_N=(contact*normal).sum(-1).clamp_min(0),relative_axis_velocity_mps=((pad[:,7:10]-slider[:,7:10])*axis).sum(-1),thumb_contact=env.contact_info[:,0],resistance_force_N=env.press_force,resistance_input_velocity_mps=env.press_velocity,resistance_limit_N=env.press_limit,pd_saturation_proxy=(demand.abs()>=effort).float().mean(-1),target_clip=(env.cur_targets[:,:20]<=env.hand_dof_lower_limits+1e-6).logical_or(env.cur_targets[:,:20]>=env.hand_dof_upper_limits-1e-6).float().mean(-1),applied_bias_rad=offset[:,16:])
  env.press_diagnostics.append({k:v.detach().cpu().numpy().copy() for k,v in row.items()})
 env.compute_reward=observe
 return env
