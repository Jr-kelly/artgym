"""Support decisions may be slower than thumb decisions, with correct PPO logs.

Holding a sampled support action creates one decision, not five independent
Gaussian samples. The joint event mask excludes held support coordinates from
the later log probabilities, entropy and rollout KL. Thumb remains30Hz.
"""
import torch


class SupportCommandSampler:
    def __init__(self,n,device,period=1,takeover_frame=480):
        assert period in [1,5]
        self.period=period;self.takeover_frame=takeover_frame
        self.held=torch.zeros((n,16),device=device)

    def sample(self,distribution,clock_frames):
        action=distribution.sample()
        event=(clock_frames-self.takeover_frame)%self.period==0
        self.held[event]=action[event,:16]
        action[:,:16]=self.held
        mask=torch.ones_like(action,dtype=torch.bool);mask[:,:16]=event[:,None]
        return action,mask


def log_prob(distribution,action,joint_events):
    return (distribution.log_prob(action)*joint_events).sum(-1)


def entropy(distribution,joint_events):
    return (distribution.entropy()*joint_events).sum(-1)
