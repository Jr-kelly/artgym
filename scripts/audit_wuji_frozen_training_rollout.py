"""Frozen-policy rollout through actual training resets, with independent accounting.

No weights or observation-normalization statistics are updated. All five SAPG
blocks run at the training batch size. Each block contains equal deterministic
and stochastic cohorts. First episodes and subsequent completed episodes are
reported separately so fast successful resets cannot hide slow failures.
"""
import argparse,json,hashlib,time
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
from isaacgymenvs.eval_common import _infer_expl_num_blocks
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=5120)
    p.add_argument('--steps',type=int,default=600);p.add_argument('--noise-epoch',type=int,default=50)
    p.add_argument('--task',default='wuji_acquisition_precision_aug');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);blocks=_infer_expl_num_blocks(a.checkpoint)
    if blocks!=5 or a.envs%(2*blocks):raise ValueError('Use equal deterministic/stochastic cohorts for five SAPG blocks')
    cfg=configuration(a.task,a.envs,['object=knife_wuji_acquisition_precision','test=False'],train='wujiAcquisitionSAPG',seed=2021)
    (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env,player=make_player(cfg,a.checkpoint)
    assert not env.eval_mode and env.runtime_grasp_split=='train'
    assert torch.all(player.actions_low==-1) and torch.all(player.actions_high==1)
    env.policy_update_step=a.noise_epoch;env._update_reward_scales_current()
    n=a.envs//blocks;batch_ids=torch.arange(a.envs,device=env.device)
    block=batch_ids//n;deterministic=(batch_ids%n)<n//2
    ids=torch.linspace(50.,0.,blocks,device=player.device)
    player.intr_reward_coef_embd[:]=ids.repeat_interleave(n).reshape(-1,1)
    before={k:v.detach().cpu().clone() for k,v in player.model.state_dict().items()}
    latest={}
    def model_capture(module,inputs,output):latest['mu']=output['mus'].detach()
    hook=player.model.register_forward_hook(model_capture)
    first_done=torch.zeros(a.envs,dtype=torch.bool,device=env.device)
    first_success=torch.zeros_like(first_done);first_strict=torch.zeros_like(first_done)
    first_reason=torch.full((a.envs,),-1,dtype=torch.int64,device=env.device)
    finished=torch.zeros(a.envs,dtype=torch.int64,device=env.device);successful=finished.clone();stable=finished.clone()
    maxdrift=torch.zeros(a.envs,device=env.device);maxrot=maxdrift.clone();maxrotfirst=maxrot.clone()
    reward_sum=maxdrift.clone();episode_returns=maxdrift.clone()
    current_reward=env.compute_reward;trace=[];sample=torch.cat([torch.arange(i*n,i*n+8,device=env.device) for i in range(blocks)])
    def record(actions):
        current_reward(actions)
        drift=torch.linalg.vector_norm(env.object_pos-env.init_object_pos,dim=1)
        angle=2*torch.asin(torch.linalg.vector_norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=1).clamp(0,1))
        maxdrift.copy_(torch.maximum(maxdrift,drift));maxrot.copy_(torch.maximum(maxrot,angle));reward_sum.add_(env.rew_buf)
        done=env.reset_buf.bool();passed=env.successes>=2
        strict=passed&(maxdrift<.01)&(maxrot<.25)
        first=done&~first_done
        first_success[first]=passed[first];first_strict[first]=strict[first];maxrotfirst[first]=maxrot[first]
        first_reason[first]=torch.where(env.truncated_envs[first],2,torch.where(passed[first],0,1))
        first_done.logical_or_(done);finished.add_(done);successful.add_(done&passed);stable.add_(done&strict)
        episode_returns.add_(torch.where(done,reward_sum,0.))
        trace.append(dict(slider=env.obj_dof_pos[sample,0].detach().cpu().numpy().copy(),
            goal=env.goal_obj_dof_pos[sample,0].detach().cpu().numpy().copy(),
            successes=env.successes[sample].detach().cpu().numpy().copy(),
            done=done[sample].cpu().numpy(),rotation=angle[sample].cpu().numpy()))
        maxdrift[done]=0;maxrot[done]=0;reward_sum[done]=0
    env.compute_reward=record
    started=time.monotonic()
    try:
        obs=player.env_reset(player.env)
        for step in range(a.steps):
            action=player.get_action(obs,is_deterministic=False)
            action[deterministic]=latest['mu'][deterministic].clamp(-1,1)
            obs,_,done,_=player.env_step(player.env,action)
            if player.is_rnn:
                indices=done.nonzero(as_tuple=False).squeeze(-1)
                for state in player.states:state[:,indices,:]=0.
            if (step+1)%100==0:print(json.dumps(dict(step=step+1,first_finished=int(first_done.sum()),first_success=int(first_success.sum()),seconds=time.monotonic()-started)),flush=True)
        groups=[]
        for b in range(blocks):
            for det in [True,False]:
                mask=(block==b)&(deterministic==det)
                groups.append(dict(block=b,deterministic=det,envs=int(mask.sum()),first_finished=int(first_done[mask].sum()),
                    first_success=int(first_success[mask].sum()),first_strict=int(first_strict[mask].sum()),
                    all_completed_episodes=int(finished[mask].sum()),all_successful_episodes=int(successful[mask].sum()),
                    all_strict_episodes=int(stable[mask].sum()),completed_episode_mean_return=float(episode_returns[mask].sum()/finished[mask].sum().clamp_min(1))))
        unchanged=all(torch.equal(v,player.model.state_dict()[k].detach().cpu()) for k,v in before.items())
        if not unchanged:raise RuntimeError('Frozen audit modified network or normalization state')
        report=dict(protocol=__doc__,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
            task=a.task,noise_epoch=a.noise_epoch,seed=2021,steps=a.steps,network_and_normalizers_unchanged=unchanged,groups=groups,
            elapsed_seconds=time.monotonic()-started)
        np.savez_compressed(a.output/'sampled-trace.npz',**{k:np.stack([x[k] for x in trace]) for k in trace[0]})
        np.savez_compressed(a.output/'per-env.npz',first_success=first_success.cpu().numpy(),first_strict=first_strict.cpu().numpy(),
            first_done=first_done.cpu().numpy(),first_reason=first_reason.cpu().numpy(),first_max_rotation=maxrotfirst.cpu().numpy(),
            finished=finished.cpu().numpy(),successful=successful.cpu().numpy(),strict=stable.cpu().numpy())
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(groups),flush=True)
    finally:hook.remove();env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
