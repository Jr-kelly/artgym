"""Wuji commands with a sampled, exogenous duration for each training stage."""
import math
import torch
from .wuji_acquisition import WujiAcquisition
from .wuji_timed_acquisition import WujiTimedAcquisition


class WujiVariableTimedAcquisition(WujiTimedAcquisition):
    def __init__(self,cfg,*args,**kwargs):
        self._duration_clock_ready=False
        super().__init__(cfg,*args,**kwargs)
        if float(cfg['env'].get('endpointHoldReward',0))!=0:
            raise ValueError('This duration comparison preserves the original reward without a hold bonus')
        dt=float(self.dt*self.control_freq_inv)
        seconds=list(cfg['env']['trainingCommandDurationsSec'])
        steps=[round(float(value)/dt) for value in seconds]
        if len(steps)!=2 or any(s<=0 or not math.isclose(s*dt,float(v),abs_tol=1e-6) for s,v in zip(steps,seconds)):
            raise ValueError('Two positive whole-step command durations are required')
        self.training_duration_steps=torch.tensor(steps,device=self.device,dtype=torch.long)
        self.command_deadline=torch.zeros(self.num_envs,device=self.device,dtype=torch.long)
        self._duration_clock_ready=True
        self._schedule_duration(torch.arange(self.num_envs,device=self.device))

    def _schedule_duration(self,ids):
        if len(ids):
            # Both the [2,2] and [2,5] arms consume the same number of RNG draws.
            duration=self.training_duration_steps[torch.randint(2,(len(ids),),device=self.device)]
            self.command_deadline[ids]=self.progress_buf[ids]+duration

    def reset_idx(self,env_ids,goal_env_ids=None):
        super().reset_idx(env_ids,goal_env_ids)
        if self._duration_clock_ready and not self.eval_mode:
            self._schedule_duration(env_ids)

    def compute_reward(self,actions):
        # Preserve inherited arrival rewards and stability costs. The inherited
        # timed update_goal override suppresses training arrival-based switching.
        WujiAcquisition.compute_reward(self,actions)
        if not self.eval_mode:
            due=(self.progress_buf>=self.command_deadline)&(self.reset_buf==0)
            ids=due.nonzero(as_tuple=False).squeeze(-1)
            if len(ids):
                WujiAcquisition.update_goal(self,ids)
                self._schedule_duration(ids)
            self.extras['TimedCommandSwitches']=due.float().sum()
