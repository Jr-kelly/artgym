"""Execute the bounded local grip actor in an uninterrupted acquisition.

No simulator handles/state setters. Initialization uses the actual closed grasp;
all later object inputs are privileged simulator truth, explicitly not student.
"""
import json,hashlib
from pathlib import Path
from scripts.g2_local_runtime import LocalPolicyRuntime
from scripts.g2_local_env import LocalG2,local_pose
from scripts.g2_v2_grip_env import grip_observation
from scripts.train_g2_local import ActorCritic
import numpy as np
import torch

class GripPolicyRuntime:
 goal=LocalG2.goal
 observation=grip_observation
 update_state=LocalPolicyRuntime.update_state
 def __init__(self,checkpoint,physics,positions,velocities,targets,wrist,obj,slider):
  saved=torch.load(checkpoint,map_location='cpu')
  assert saved['task_variant'] in ['v2-grip','v2-prefix-grip']
  assert saved['task']=='H' and saved['route']=='joint' and saved['obs_dim']==124 and saved['action_dim']==20
  self.task='H';self.route='joint';self.n=1;self.dt=1/30;self.span=.20;self.speed=.60;self.steps=150;self.action_dim=20
  self.goal_override=None;self.ready=True
  self.lower=torch.tensor(physics['robot_dof_properties']['lower']);self.upper=torch.tensor(physics['robot_dof_properties']['upper'])
  self.slider_lower=float(physics['knife_dof_properties']['lower'][0])
  self.dof=torch.zeros(1,28,2);self.wrist=torch.zeros(1,13);self.object=torch.zeros(1,13);self.slider_pose=torch.zeros(1,13)
  self.targets=torch.tensor(np.array(targets),dtype=torch.float32).reshape(1,28)
  self.source=dict(reference_targets=self.targets[0].clone(),slider=torch.tensor(float(positions[27])))
  self.residual=torch.zeros(1,20);self.last_action=torch.zeros(1,20);self.age=torch.zeros(1,dtype=torch.long)
  self.update_state(positions,velocities,wrist,obj,slider)
  self.initial_object=self.object[:,:7].clone();self.initial_local=local_pose(self.wrist,self.object).clone()
  self.model=ActorCritic(124,20);self.model.load_state_dict(saved['model']);self.model.eval()
  self.last_observation=self.observation();self.model_calls=0;self.checkpoint=str(checkpoint)
  self.checkpoint_sha256=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest();self.variant=saved['task_variant']

 def step(self,positions,velocities,wrist,obj,slider,nominal_hand=None):
  self.update_state(positions,velocities,wrist,obj,slider);self.last_observation=self.observation()
  with torch.no_grad():action=self.model.mean_action(self.last_observation)
  self.model_calls+=1;self.last_action[:]=action
  self.residual+=(action*.20-self.residual).clamp(-.02,.02)
  self.targets[:,7:27]=self.source['reference_targets'][7:27]+self.residual
  self.targets[:,:27]=torch.max(self.lower,torch.min(self.upper,self.targets[:,:27]));self.age+=1
  return self.targets[0,7:27].numpy().copy()

 def description(self):
  return dict(checkpoint=self.checkpoint,sha256=self.checkpoint_sha256,training_variant=self.variant,method='Frozen new privileged grip-retention PPO, original manipulation teacher unchanged',scope='Actual continuous lift plus1s hold, motor-only; no local-state reload',inputs='actual q/qd, actual commanded reference, live simulated wrist/body pose+velocity and slider, actual initial hand/body reference, elapsed lift clock, previous outputs',deployable=False,student=False,action='20 absolute motor residuals +/-0.20rad, slew0.02rad/control, original limits',initialization='actual closed acquisition; zero residual/action; feedforward no RNN, no fabricated history',actual_model_calls=self.model_calls)
