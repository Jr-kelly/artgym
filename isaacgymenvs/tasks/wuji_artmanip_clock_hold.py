"""Explicit fixed-clock/absolute-body holding objective; reference dynamics unchanged."""
import torch
from .wuji_artmanip_reference import WujiArtManipReference
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate

class WujiArtManipClockHold(WujiArtManipReference):
    def __init__(self,cfg,*args,**kwargs):
        self.clock_ready=False
        super().__init__(cfg,*args,**kwargs)
        self.clock_period=torch.full((self.num_envs,),60,device=self.device,dtype=torch.long)
        self.clock_switches=torch.zeros_like(self.clock_period)
        self.clock_ready=True

    def reset_idx(self,env_ids,goal_env_ids=None):
        super().reset_idx(env_ids,goal_env_ids)
        if self.clock_ready and not self.eval_mode:
            self.clock_period[env_ids]=torch.where(torch.randint(2,(len(env_ids),),device=self.device)==0,60,150)
            self.clock_switches[env_ids]=0
            self.goal_refresh_interval[env_ids]=float('inf')

    def compute_reward(self,actions):
        if self.eval_mode or not self.clock_ready:
            return super().compute_reward(actions)
        # progress_buf is incremented before reward; this transition saw the
        # previous clock phase. Switch only after scoring, before observations.
        phase=((self.progress_buf-1).clamp_min(0)//self.clock_period)%2
        expected=self.init_obj_dof_pos[:,0]+torch.where(phase==0,.04,0.)
        if not torch.allclose(self.goal_obj_dof_pos[:,0],expected,atol=1e-6):
            raise RuntimeError('Training goal does not match fixed pre-action clock')
        super().compute_reward(actions)
        if self.goal_achieved_step.any():raise RuntimeError('Arrival unexpectedly switched fixed-clock goal')
        drift=torch.linalg.vector_norm(self.object_pos-self.init_object_pos,dim=-1)
        angle=2*torch.asin(torch.linalg.vector_norm(quat_mul(self.object_rot,quat_conjugate(self.init_object_rot))[:,:3],dim=-1).clamp(0,1))
        valid=~self.truncated_envs & torch.isfinite(drift) & torch.isfinite(angle)
        stable=valid&(drift<.01)&(angle<.25)
        error=torch.nan_to_num((self.obj_dof_pos[:,0]-self.goal_obj_dof_pos[:,0]).abs(),nan=1.,posinf=1.)
        hold=5*torch.exp(-(error/.002).square())*stable.float()
        body=5*torch.nan_to_num(torch.maximum(drift/.01,angle/.25),nan=5.,posinf=5.).clamp(0,5)
        self.rew_buf.add_(hold-body)
        self.extras['holding/reward']=hold.mean()
        self.extras['holding/body_penalty']=-body.mean()
        self.extras['holding/stable_fraction']=stable.float().mean()
        self.extras['holding/period2_fraction']=(self.clock_period==60).float().mean()
        self.extras['holding/max_abs_additional_reward']=(hold-body).abs().max()
        for source in range(4):
            mask=self.source_ids==source
            if mask.any():self.extras[f'source{source}/strict_body_fraction']=stable[mask].float().mean()
        switch=(self.progress_buf%self.clock_period==0)&(self.reset_buf==0)
        ids=switch.nonzero(as_tuple=False).squeeze(-1)
        if len(ids):
            self.update_goal(ids)
            self.clock_switches[ids]+=1
        self.extras['holding/switches_this_step']=switch.float().sum()
