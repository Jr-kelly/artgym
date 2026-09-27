"""Batched frozen teacher, same FK/frame/clock bridge as continuous baseline.

For learned support, teacher receives its own executed thumb-channel action,
while support commands and residuals are separate logged controller channels.
Measured joint state remains actual. This is a new composite controller.
"""
import numpy as np
import torch
from scipy.spatial.transform import Rotation

from scripts.g2_frozen_policy import FrozenPolicy
from scripts.g2_local_env import local_pose, qmul, qrot
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere


class BatchedTeacher:
    def __init__(self, env, checkpoint, device='cpu'):
        env.cfg.rl_device = device
        self.env = env
        self.base = FrozenPolicy(env.cfg, checkpoint, action_mode='thumb-only')
        self.player = self.base.player
        self.device = self.player.device
        self.lower = torch.as_tensor(self.base.fk.lower, dtype=torch.float32)
        self.upper = torch.as_tensor(self.base.fk.upper, dtype=torch.float32)
        self.chain = []
        for parent, child, origin, idx, axis in self.base.fk.joints:
            self.chain.append((parent, child, torch.as_tensor(origin[:3, 3], dtype=torch.float32),
                torch.as_tensor(Rotation.from_matrix(origin[:3, :3]).as_quat(), dtype=torch.float32),
                idx, None if axis is None else torch.as_tensor(axis, dtype=torch.float32)))
        self.states = [torch.zeros(s.shape[0], env.n, s.shape[2], device=self.device)
                       for s in self.player.model.get_default_rnn_state()]
        self.last_action = torch.zeros(env.n, 20)
        self.raw_action = self.last_action.clone()
        self.init = torch.zeros(env.n, 55)
        self.previous_slider = torch.zeros(env.n)
        self.history = torch.zeros(env.n, 50, 40)
        self.last_obs = torch.zeros(env.n, 138)
        self.reset(torch.arange(env.n))

    def normalized(self, q):
        return 2 * (q - self.lower) / (self.upper - self.lower) - 1

    def tips(self, q):
        zero = torch.zeros(len(q), 3)
        ident = torch.zeros(len(q), 4)
        ident[:, 3] = 1
        frames = {'hand_r_base_link': (zero, ident)}
        for parent, child, p, rot, idx, axis in self.chain:
            pp, pq = frames[parent]
            cp = pp + qrot(pq, p.expand(len(q), -1))
            cq = qmul(pq, rot.expand(len(q), -1))
            if idx is not None:
                half = q[:, idx:idx+1] / 2
                r = torch.cat((torch.sin(half) * axis, torch.cos(half)), -1)
                cq = qmul(cq, r)
            frames[child] = (cp, cq)
        return torch.cat([frames[n][0] for n in self.base.fk.config['track_links']], -1)

    def reset(self, ids):
        e = self.env
        for state in self.states:
            state[:, ids.to(self.device)] = 0
        self.last_action[ids] = 0
        self.raw_action[ids] = 0
        self.previous_slider[ids] = e.dof[ids, 27, 0]
        q = e.dof[ids, 7:27, 0]
        dims = torch.tensor([.019, .008, .147, .01, .003, .03]).expand(len(ids), -1)
        self.init[ids] = torch.cat((self.normalized(q), local_pose(e.wrist[ids], e.object[ids]),
            local_pose(e.wrist[ids], e.slider_pose[ids]), self.tips(q), dims), -1)
        self.history[ids] = torch.cat((self.normalized(e.source['history_q'].float()),
                                      e.source['history_action'].float()), -1)

    def step(self, full=False):
        e = self.env
        q = e.dof[:, 7:27, 0]
        slider = e.dof[:, 27, 0]
        pol = torch.cat((self.init, self.normalized(q), self.last_action,
                         (e.goal() - e.slider_lower).unsqueeze(-1), self.tips(q)), -1)
        pri = torch.cat((local_pose(e.wrist, e.object), local_pose(e.wrist, e.slider_pose),
            torch.tensor([.029, .006, 3., .3, 0.]).expand(e.n, -1),
            (slider-e.slider_lower).unsqueeze(-1), ((slider-self.previous_slider)*30).unsqueeze(-1)), -1)
        pol, pri = original_to_acquisition_observations(pol, pri)
        pol, pri = align_quaternion_hemisphere(pol, pri, self.base.reference)
        obs = torch.cat((pol, pri, torch.zeros(e.n, 5),
                        self.player.intr_reward_coef_embd[:1].cpu().expand(e.n, -1)), -1)
        self.last_obs[:] = obs
        with torch.no_grad():
            result = self.player.model(dict(is_train=False, prev_actions=None,
                                           obs=obs.to(self.device), rnn_states=self.states))
        self.states = result['rnn_states']
        action = result['mus'].clamp(-1, 1).cpu()
        self.raw_action[:] = action
        if not full:
            action[:, :16] = 0
        self.last_action[:] = action
        self.previous_slider[:] = slider
        if full:
            e.targets[:, 7:23] = e.source['reference_targets'][7:23] + .04 * action[:, :16]
        e.targets[:, 23:27] += .025 * action[:, 16:]

    def record(self):
        self.history = torch.roll(self.history, -1, dims=1)
        self.history[:, -1] = torch.cat((self.normalized(self.env.dof[:, 7:27, 0]), self.last_action), -1)
