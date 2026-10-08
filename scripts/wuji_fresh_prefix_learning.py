"""Fresh-table physics replay initializes transition learning, never a held-state restore.

A uses the actual issued 743 motor history. Every training episode starts with
natural table placement, then simulates the complete prefix. No state setters
occur after episode initialization. This is training, not native acceptance.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from isaacgym import gymtorch
import torch
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_conjugate
from scripts.wuji_regrasp_learning import RegraspLearning
from scripts.wuji_regrasp_contract import phase_increment,entry_progress_reward
from scripts.wuji_pose_motion import PoseMotion

class FreshPrefixRegrasp(RegraspLearning):
 def __init__(self,n,source,reference,prefix_trace,prefix_spec,steps=900,functional_workspace=False,linear_potential=False,failure_penalty=12.,self_bad_penalty=.5,task_geometry=False,free_motor=False,workspace_query_distance_m=.004,workspace_cadence_frames=15,pose_motion_observation=False,fail_on_self_contact=False,functional_contact_reward=False,task_stroke_m=.03):
  self.task_stroke_m=float(task_stroke_m)
  assert .020<self.task_stroke_m<=.035
  self.functional_contact_reward=functional_contact_reward
  assert not functional_contact_reward or fail_on_self_contact
  self.fail_on_self_contact=fail_on_self_contact
  assert not fail_on_self_contact or (pose_motion_observation and task_geometry)
  self.free_motor=free_motor
  self.task_geometry=task_geometry
  self.pose_motion_observation=pose_motion_observation;self.pose_motion=PoseMotion()
  self.workspace_query_distance_m=workspace_query_distance_m;self.workspace_cadence_frames=workspace_cadence_frames
  assert workspace_query_distance_m>0 and workspace_cadence_frames>0 and workspace_cadence_frames%15==0
  assert not task_geometry or functional_workspace
  self.self_bad_penalty=self_bad_penalty;self.linear_potential=linear_potential;self.failure_penalty=failure_penalty
  self.functional_workspace=functional_workspace;self.affordance=None;self.affordance_cache=None
  self.fresh_ready=False;self.prefix_path=str(prefix_trace);self.prefix_spec_path=str(prefix_spec);spec=json.loads(Path(prefix_spec).read_text());data=np.load(prefix_trace);self.prefix_numpy=data['applied_target'].astype(np.float32);self.fresh_object=np.asarray(spec['physical_initial_object_world']);self.fresh_q=np.r_[spec['direct_pickup']['initial_arm_q'],spec['direct_pickup']['open_q']];self.fresh_initial_pose=np.r_[self.fresh_object[:3,3],Rotation.from_matrix(self.fresh_object[:3,:3]).as_quat(),np.zeros(6)];self.fresh_episode_index=0
  super().__init__(n,source,reference,physx_buffer_multiplier=16,safe_reset_order=True)
  if functional_workspace:
   from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
   self.affordance=FunctionalEntryAffordance(self.task_stroke_m)
  self.prefix_motor=self.tensor(self.prefix_numpy);self.span[7:]=1.2;self.span[:7]=.6 if free_motor else .2;self.steps=steps;self.fresh_ready=True;self.motor_anchor=torch.zeros((n,27),device=self.device);self.reset(torch.arange(n,device=self.device),perturb=False)
 def reset(self,ids,perturb=False,physical_offsets=None):
  if not self.fresh_ready:return super().reset(ids,perturb=False)
  assert len(ids)==self.n and physical_offsets is None
  self.pose_motion=PoseMotion()
  self.refresh();self.root[:,0,:]=0;self.root[:,0,6]=1;self.root[:,0,:3]=self.origins;self.root[:,2,:]=self.tensor(self.fresh_initial_pose);self.root[:,2,:3]+=self.origins;self.dof[:,:27,0]=self.tensor(self.fresh_q);self.dof[:,:27,1]=0;self.dof[:,27,0]=self.initial_slider;self.dof[:,27,1]=0;self.target=self.prefix_motor[0].expand(self.n,-1).clone();self.command_target=self.target.clone();self.forces[:]=0
  actor_ids=torch.stack([ids*3,ids*3+2],-1).flatten().to(torch.int32);self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root.view(-1,13)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids));self.gym.set_dof_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.dof.view(-1,2)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids))
  # Consume initialization buffers before refresh, with gravity at the actual
  # initialized q rather than the preceding episode's native Jacobian.
  gravity=self.tensor(self.reset_gravity(self.fresh_q));torque=self.kp*(self.target-self.dof[:,:27,0])+gravity;self.forces[:,:27]=torch.maximum(torch.minimum(torque,self.effort),-self.effort);self.gym.set_dof_actuation_force_tensor(self.sim,gymtorch.unwrap_tensor(self.forces.flatten()));self.gym.simulate(self.sim);self.gym.fetch_results(self.sim,True);self.refresh();self.servo(self.target,substeps=7)
  prefix_min=torch.full((self.n,),float('inf'),device=self.device);qhistory=[];ohistory=[]
  for tick,motor in enumerate(self.prefix_motor[1:],1):
   self.servo(motor.expand(self.n,-1))
   if tick/30>=7.:
    prefix_min=torch.minimum(prefix_min,self.whole_clearance())
   if tick%30==0:qhistory.append(self.dof[:,:27,0].clone());ohistory.append(self.rb[:,self.object_index].clone())
  self.prefix_min_clearance=prefix_min;self.prefix_final_object=self.rb[:,self.object_index].clone();self.prefix_final_q=self.dof[:,:27,0].clone();self.prefix_actual_q_1hz=torch.stack(qhistory);self.prefix_actual_object_1hz=torch.stack(ohistory);self.fresh_episode_index+=1
  self.servo(self.target) # Same real held-target warm frame as native policy.
  self.stage_initial_object=self.rb[:,self.object_index].clone()
  self.motor_anchor=self.command_target-self.motor_reference[0];self.affordance_cache=None;self.age[:]=0;self.phase[:]=0;self.offset[:]=0;self.last[:]=0;self.failed=(self.whole_clearance()<.025)|(prefix_min<.002);self.entry_frames=torch.zeros(self.n,device=self.device);self.best_entry_error=torch.full((self.n,),float('inf'),device=self.device);self.best_entry_dwell=torch.zeros(self.n,device=self.device);self.entry_awarded=torch.zeros(self.n,device=self.device,dtype=torch.bool);self.held_frames=torch.zeros(self.n,device=self.device);self.max_held_frames=torch.zeros(self.n,device=self.device);self.pause_steps=torch.zeros(self.n,device=self.device);self.stage_slider_start=self.dof[:,27,0].clone();self.previous_potential=self.entry_metrics()['potential'];return self.observation()
 def whole_clearance(self):
  o=self.rb[:,self.object_index];Z=quat_apply(o[:,3:7],self.tensor([0,0,1]).expand(self.n,-1));Y=quat_apply(o[:,3:7],self.tensor([0,1,0]).expand(self.n,-1));X=quat_apply(o[:,3:7],self.tensor([1,0,0]).expand(self.n,-1));return o[:,2]-.75-Z[:,2].abs()*.072-Y[:,2].abs()*.006-X[:,2].abs()*.0095
 def servo(self,motor,substeps=8):
  super().servo(motor,substeps=substeps)
  if self.fresh_ready and self.pose_motion_observation:self.pose_motion.update(self.rb[:,self.object_index,:7],substeps/240)
 def object_motion(self):
  if self.pose_motion_observation and self.fresh_ready:return self.pose_motion.velocity
  return self.rb[:,self.object_index,7:13]
 def cap_distance(self):
  n=self.n;count=len(self.thumb_vertices);pad=self.rb[:,self.pad_indices[0]];slider=self.rb[:,self.slider_index];vertices=quat_apply(pad[:,None,3:7].expand(-1,count,-1).reshape(-1,4),self.thumb_vertices[None].expand(n,-1,-1).reshape(-1,3)).reshape(n,count,3)+pad[:,None,:3];inv=quat_conjugate(slider[:,3:7]);local=quat_apply(inv[:,None].expand(-1,count,-1).reshape(-1,4),(vertices-slider[:,None,:3]).reshape(-1,3)).reshape(n,count,3);return (local.abs()-self.slider_half[:,None]).clamp_min(0).norm(dim=-1).amin(-1)
 def entry_metrics(self):
  m=super().entry_metrics();distance=self.cap_distance();m['cap_distance_m']=distance;m['clearance_m']=self.whole_clearance();m['held']=m['held']&(m['clearance_m']>.025);m['error']=distance/.01+.05*m['rotation_rad']/.6+.05*m['q_rms_rad']/.5+.05*m['position_m']/.025;m['potential']=torch.where(m['held'],torch.exp(-m['error']),torch.zeros_like(distance))
  if self.pose_motion_observation and self.fresh_ready:m['held']=m['finite']&~self.failed&(m['clearance_m']>.025)&(self.object_motion()[:,:3].norm(dim=-1)<.3)
  if self.functional_workspace and self.fresh_ready:
   if self.affordance_cache is None:
    self.affordance_cache={'path_error':torch.full((self.n,),self.task_stroke_m,device=self.device),'tail_distance':torch.full((self.n,),.04,device=self.device),'self_bad':torch.zeros(self.n,device=self.device,dtype=torch.bool),'eligible':torch.zeros(self.n,device=self.device,dtype=torch.bool),'checked_age':-1,'full_path_queries':0,'best_safe_path_error':torch.full((self.n,),float('inf'),device=self.device)}
   c=self.affordance_cache;age=int(self.age[0]);pad=self.rb[:,self.pad_indices[0]];o=self.rb[:,self.object_index];count=len(self.thumb_vertices);world=quat_apply(pad[:,None,3:7].expand(-1,count,-1).reshape(-1,4),self.thumb_vertices[None].expand(self.n,-1,-1).reshape(-1,3)).reshape(self.n,count,3)+pad[:,None,:3];local=quat_apply(quat_conjugate(o[:,3:7])[:,None].expand(-1,count,-1).reshape(-1,4),(world-o[:,None,:3]).reshape(-1,3)).reshape(self.n,count,3);weights=torch.softmax(-local[:,:,1]/.0002,-1);foot=(weights[:,:,None]*local).sum(1);center_z=-.026+self.dof[:,27,0];clamped=foot.clone();clamped[:,0]=clamped[:,0].clamp(-.0035,.0035);clamped[:,1]=.006;clamped[:,2]=torch.minimum(torch.maximum(clamped[:,2],center_z-.016),center_z-.008);tail_distance=(foot-clamped).norm(dim=-1);c['tail_distance']=tail_distance;c['foot_delta']=foot-clamped
   if age%15==0 and c['checked_age']!=age:
    from scripts.g2_kinematics import transform
    selected=torch.nonzero(((m['clearance_m']>.025) if self.task_geometry else (distance<.004))&~self.failed).flatten().cpu().tolist()
    for i in selected:
     values=self.dof[i,:27,0].cpu().numpy().astype(float)
     if distance[i]<self.workspace_query_distance_m and age%self.workspace_cadence_frames==0:
      c['full_path_queries']+=1
      pose=o[i,:7].cpu().numpy();a=self.affordance.assess(values,transform(pose[:3],pose[3:7]),float(self.dof[i,27,0]));c['path_error'][i]=min(.04,a['reference_FK_error_m']);c['self_bad'][i]=bool(a['self_intersections']);c['eligible'][i]=a['reference_eligible']
      if not a['self_intersections']:c['best_safe_path_error'][i]=min(float(c['best_safe_path_error'][i]),a['reference_FK_error_m'])
     else:
      c['self_bad'][i]=bool(self.affordance.H.inspect(values[7:]))
      if distance[i]>=self.workspace_query_distance_m:c['eligible'][i]=False
    c['checked_age']=age
   m.update(reference_FK_error_m=c['path_error'],tail_roof_distance_m=tail_distance,reference_eligible=c['eligible']&~c['self_bad'])
   m['error']=tail_distance/(.006 if self.functional_contact_reward else .018)+.6*(c['path_error']/.01).clamp(max=3)+.03*m['rotation_rad']/.6+.03*m['position_m']/.025+self.self_bad_penalty*c['self_bad'].float()
   if self.task_geometry:
    o=self.rb[:,self.object_index];delta=(self.dof[:,27,0]-self.stage_slider_start).abs();thumb=self.dof[:,23:27,0];reserve=torch.minimum(thumb-self.limitlow[23:27],self.limithi[23:27]-thumb).amin(-1)
    motion=self.object_motion();m['slider_drift_m']=delta;m['linear_speed_m_s']=motion[:,:3].norm(dim=-1);m['angular_speed_rad_s']=motion[:,3:].norm(dim=-1)
    m['error']+=.75*((delta-.001).clamp(min=0)/.002).clamp(max=4)+.3*((m['linear_speed_m_s']-.04).clamp(min=0)/.08).clamp(max=2)+.2*((m['angular_speed_rad_s']-.4).clamp(min=0)/.8).clamp(max=2)+(2. if self.functional_contact_reward else .5)*((.075-reserve).clamp(min=0)/.075).clamp(max=2)
    if self.functional_contact_reward:m['error']+=.75*(distance/.004).clamp(max=4)
   m['potential']=torch.where(m['held'],(1-m['error']/(12 if self.task_geometry else 8)).clamp(0,1) if self.linear_potential else torch.exp(-m['error']),torch.zeros_like(distance))
  return m
 def observation(self):
  base=super().observation();motion=self.object_motion();obs=torch.cat([base,motion[:,:3],motion[:,3:]*.05,self.dof[:,27,0:1]*10,self.dof[:,27,1:2]*.2,self.cap_distance()[:,None]*100],-1)
  if self.task_geometry and self.fresh_ready:
   c=self.affordance_cache;extra=torch.cat([c['foot_delta']*100,c['tail_distance'][:,None]*100,c['path_error'][:,None]*100,c['self_bad'][:,None].float(),(self.dof[:,27,0]-self.stage_slider_start)[:,None]*100,motion[:,:3].norm(dim=-1,keepdim=True)*5,motion[:,3:].norm(dim=-1,keepdim=True),c['eligible'][:,None].float()],-1);assert extra.shape==(self.n,10);obs=torch.cat([obs,extra],-1)
  return obs
 def step(self,action):
  action=action.detach().clamp(-1,1);assert action.shape==(self.n,27 if self.free_motor else 28);was_alive=~self.failed;self.offset=(self.offset+action[:,:27]*self.slew).clamp(-self.span,self.span)
  if self.free_motor:
   advance=torch.zeros(self.n,device=self.device);self.pause_steps+=(action.abs().amax(-1)<.05).float()*was_alive.float();guide=self.motor_reference[0]+self.motor_anchor
  else:
   advance=phase_increment(action[:,27]);self.pause_steps+=(advance==0).float()*was_alive.float();self.phase=(self.phase+advance*was_alive.float()).clamp(max=len(self.motor_reference)-1.0001);guide=self.guide_targets()+self.motor_anchor
  desired=guide+self.offset;motor=self.command_target+(desired-self.command_target).clamp(-self.slew,self.slew);motor=torch.minimum(torch.maximum(motor,self.limitlow),self.limithi);motor=torch.where(was_alive[:,None],motor,self.command_target);self.servo(motor);self.offset=self.command_target-guide;self.age+=1;m=self.entry_metrics();geometry_failure=self.affordance_cache['self_bad'] if getattr(self,'fail_on_self_contact',False) else torch.zeros_like(was_alive);new_failed=was_alive&((m['clearance_m']<.01)|~m['finite']|geometry_failure);self.failed|=new_failed;held=m['held']&~self.failed
  thumb=self.dof[:,23:27,0];reserve=torch.minimum(thumb-self.limitlow[23:27],self.limithi[23:27]-thumb).amin(-1);o=self.rb[:,self.object_index];motion=self.object_motion() if getattr(self,'pose_motion_observation',False) else o[:,7:13];entry=held&(m['cap_distance_m']<.0015)&(reserve>.075)&(motion[:,:3].norm(dim=-1)<.08)&(motion[:,3:].norm(dim=-1)<.8)&((self.dof[:,27,0]-self.stage_slider_start).abs()<.002)
  if self.functional_workspace:entry=entry&m['reference_eligible']
  self.entry_frames=torch.where(entry,self.entry_frames+1,torch.zeros_like(self.entry_frames));dwell=self.entry_frames.clamp(max=30);new_dwell=(dwell-self.best_entry_dwell).clamp(min=0);self.best_entry_dwell=torch.maximum(self.best_entry_dwell,dwell);first=(self.entry_frames>=30)&~self.entry_awarded;self.entry_awarded|=first;self.held_frames=torch.where(held,self.held_frames+1,torch.zeros_like(self.held_frames));self.max_held_frames=torch.maximum(self.max_held_frames,self.held_frames);self.best_entry_error=torch.minimum(self.best_entry_error,torch.where(held,m['error'],torch.full_like(m['error'],float('inf'))));potential=torch.where(held,m['potential'],torch.zeros_like(m['potential']));reward=entry_progress_reward(self.previous_potential,potential,new_dwell,first.float(),held.float());reward-=.002*action[:,:27].square().mean(-1)
  if self.task_geometry:reward-=.02*self.affordance_cache['self_bad'].float()*was_alive.float()
  reward=torch.where(new_failed,torch.full_like(reward,-self.failure_penalty),torch.where(was_alive,reward,torch.zeros_like(reward)));self.previous_potential=potential;self.last=action[:,:27].clone();return self.observation(),reward,self.failed|(self.age>=self.steps),dict(m,entry_frames=self.entry_frames,failed=self.failed,phase_increment=advance,max_held_frames=self.max_held_frames,best_entry_dwell=self.best_entry_dwell,scope='Fresh-table prefix physics and functional cap/holding proxies; no B/fulltask acceptance')
