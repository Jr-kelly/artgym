"""Maintain issued Wuji targets using commands, without reading live simulator targets."""
import torch
from isaacgymenvs.utils.torch_jit_utils import scale,unscale,tensor_clamp

class KnownWujiController:
 def __init__(self,lower,upper,n):
  self.lower=lower.clone();self.upper=upper.clone()
  self.initial=torch.zeros((n,20),device=lower.device,dtype=lower.dtype)
  self.issued=self.initial.clone()
  self.support_span=.04;self.support_step=None
  self.last_executed_action=self.initial.clone()
 def configure_support(self,span=.04,step=None):
  assert .04<=span<=.20 and (step is None or 0<step<=.025)
  self.support_span=float(span);self.support_step=step
 def reset(self,ids,initial_command):
  # Supplied by the initialization command, never inferred from measured q.
  self.initial[ids]=initial_command;self.issued[ids]=initial_command
  self.last_executed_action[ids]=0
 def step(self,action):
  previous=self.issued.clone();target=self.initial+self.support_span*action
  target[:,16:]=self.issued[:,16:]+.025*action[:,16:]
  if self.support_step is not None:target[:,:16]=torch.minimum(torch.maximum(target[:,:16],previous[:,:16]-self.support_step),previous[:,:16]+self.support_step)
  target=tensor_clamp(target,self.lower,self.upper)
  # Preserve the actual original controller's normalized-command round trip.
  normalized=unscale(target,self.lower,self.upper)
  desired=scale(normalized,self.lower,self.upper)
  self.issued=tensor_clamp(desired,self.lower,self.upper)
  self.last_executed_action=(self.issued-self.initial)/self.support_span
  self.last_executed_action[:,16:]=(self.issued[:,16:]-previous[:,16:])/.025
  return self.issued
 def observed_targets(self):return unscale(self.issued,self.lower,self.upper)

def install_known_controller(env,mode):
 assert mode in ['real','masked']
 assert float(env.cfg['env']['supportActionSpan'])==.04 and float(env.cfg['env']['thumbActionStep'])==.025
 assert not env.use_relative_control and env.act_moving_average==1.
 controller=KnownWujiController(env.hand_dof_lower_limits,env.hand_dof_upper_limits,env.num_envs)
 env.known_controller=controller;env.known_controller_max_error=0.;env.known_controller_mode=mode
 sampling=env.sample_grasps
 def sample(ids):
  states=sampling(ids)
  controller.reset(ids,states[:,20:40])
  return states
 env.sample_grasps=sample
 pre=env.pre_physics_step
 def step(action):
  predicted=controller.step(action.to(env.device))
  pre(action)
  # Audit only: simulator targets do not flow back into controller or policy.
  error=float((predicted-env.cur_targets[:,:20]).abs().max())
  env.known_controller_max_error=max(env.known_controller_max_error,error)
  assert error<2e-6, 'Independent command memory differs from actual controller'
 env.pre_physics_step=step
 observation=env._compute_student_encoder_observations
 def observe(policy,privileged):
  old=observation(policy,privileged)
  context=torch.cat([controller.observed_targets(),policy[:,95:96]/.04],dim=1)
  if mode=='masked':context=torch.zeros_like(context)
  return torch.cat([old,context],dim=1)
 env._compute_student_encoder_observations=observe
 # Physical/public dimensions remain111+21+5. The declared student context is
 # initial55 plus21 dynamic known command fields, not a fictitious initial76.
 env.student_obs_dim=2076
 env.student_obs_buf=torch.zeros((env.num_envs,2076),device=env.device)
 env.cfg['env']['studentObsDim']=2076
 return controller
