"""Motor-only execution of the learned local policy in continuous acquisition.

No simulator handle or state setter. Current object truth is privileged input.
The reference is fixed once at takeover; initial targets are actual commands.
"""
import json
from pathlib import Path
from scripts.g2_local_env import LocalG2, DATA, local_pose  # Isaac before torch
import numpy as np
import torch
from scripts.train_g2_local import ActorCritic


class LocalPolicyRuntime:
    def __init__(self, checkpoint, positions, velocities, targets, wrist, obj, slider):
        artifact = torch.load(checkpoint, map_location='cpu')
        self.task, self.route = artifact['task'], artifact['route']
        self.goal_override = None
        self.n, self.dt, self.span, self.speed = 1, 1/30, .20, .60
        self.action_dim = artifact['action_dim']
        self.steps = 660 if self.task == 'H' else 600
        properties = json.loads((DATA/'physics.json').read_text())
        self.lower = torch.tensor(properties['robot_dof_properties']['lower'])
        self.upper = torch.tensor(properties['robot_dof_properties']['upper'])
        self.slider_lower = float(properties['knife_dof_properties']['lower'][0])
        self.dof = torch.zeros(1,28,2)
        self.targets = torch.as_tensor(np.asarray(targets).copy(),dtype=torch.float32).reshape(1,28)
        self.source = dict(reference_targets=self.targets[0].clone(),slider=torch.tensor(float(positions[27])))
        self.residual = torch.zeros(1,self.action_dim)
        self.last_action = torch.zeros_like(self.residual)
        self.age = torch.zeros(1,dtype=torch.long)
        self.wrist = torch.zeros(1,13)
        self.object = torch.zeros(1,13)
        self.slider_pose = torch.zeros(1,13)
        self.update_state(positions,velocities,wrist,obj,slider)
        self.initial_object = self.object[:,:7].clone()
        self.initial_local = local_pose(self.wrist,self.object).clone()
        self.model = ActorCritic(artifact['obs_dim'],self.action_dim)
        self.model.load_state_dict(artifact['model'])
        self.model.eval()
        self.last_observation = LocalG2.observation(self)
        self.checkpoint = str(checkpoint)

    goal = LocalG2.goal

    def update_state(self,positions,velocities,wrist,obj,slider):
        self.dof[0,:,0] = torch.as_tensor(np.asarray(positions).copy())
        self.dof[0,:,1] = torch.as_tensor(np.asarray(velocities).copy())
        for dest,value in [(self.wrist,wrist),(self.object,obj),(self.slider_pose,slider)]:
            value = torch.as_tensor(np.asarray(value).copy())
            dest[0,:len(value)] = value

    def step(self,positions,velocities,wrist,obj,slider,nominal_hand):
        self.update_state(positions,velocities,wrist,obj,slider)
        self.last_observation = LocalG2.observation(self)
        with torch.no_grad():
            action = self.model.mean_action(self.last_observation)
        self.last_action[:] = action
        desired = action*self.span
        self.residual += (desired-self.residual).clamp(-self.speed*self.dt,self.speed*self.dt)
        self.targets[0,7:27] = torch.as_tensor(np.asarray(nominal_hand).copy())
        self.targets[:,7:7+self.action_dim] = self.source['reference_targets'][7:7+self.action_dim]+self.residual
        self.targets[:,:27] = torch.max(self.lower,torch.min(self.upper,self.targets[:,:27]))
        self.age += 1
        return self.targets[0,7:27].numpy().copy()

    def description(self):
        return dict(checkpoint=self.checkpoint,task=self.task,route=self.route,
            method='new learned controller, not unchanged full teacher',
            inputs='measured q/qd, commanded targets, fixed takeover reference, live simulator knife pose/velocity, wrist pose, slider state, external clock, previous learner output',
            privileged=True, deployable=False, rnn='learner feedforward; frozen thumb teacher keeps original takeover RNN reset',
            reference='fixed once at actual continuous takeover',span_rad=self.span,speed_rad_s=self.speed,
            physics_writes='none; returns robot hand motor targets only')
