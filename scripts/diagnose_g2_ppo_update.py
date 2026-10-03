"""Counterfactual optimizer diagnostics on one actual G2 rollout batch.

No resulting model is a deployment candidate. Compare original joint clipping
and separate clipping for the already separate actor/critic networks, and report
analytic Gaussian KL beside the sampled importance-ratio approximation.
"""
import argparse,copy,hashlib,json,time
from pathlib import Path
from scripts.g2_continuous_scene import G2ContinuousScene
from scripts.wuji_robust_learning import ResidualActorCritic
import numpy as np
import torch
from torch.distributions import kl_divergence,Normal


def norm(parameters):
    return float(torch.sqrt(sum(p.grad.square().sum() for p in parameters if p.grad is not None)))


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--envs',type=int,default=512);p.add_argument('--seed',type=int,default=2026100377);p.add_argument('--prefix-steps',type=int,default=540);p.add_argument('--horizon',type=int,default=32);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);saved=torch.load(a.checkpoint,map_location='cuda');assert not saved.get('support_estimator_spec') and not saved.get('history_features');scene=G2ContinuousScene(a.envs,a.seed,1.,load_max=.2,detent_max=.2,reference_spec=saved['thumb_reference'],support_scale=.75,thumb_scale=.75,load_profile='mixed',functional_thumb_reward=True,contact_progress_reward=.5);model=ResidualActorCritic().cuda();model.load_state_dict(saved['model']);begin=time.monotonic()
    data={k:[] for k in ['public','critic','action','log','mean','scale','value','reward','done','active']}
    try:
        for step in range(a.prefix_steps+a.horizon):
            public,critic=scene.features()
            with torch.no_grad():dist,value=model(public,critic);action=dist.sample();log=dist.log_prob(action).sum(-1)
            active=scene.policy_active.clone();reward,done=scene.step(action)
            if step>=a.prefix_steps:
                values=dict(public=public,critic=critic,action=action,log=log,mean=dist.mean,scale=dist.scale,value=value,reward=reward,done=done,active=active)
                for key in data:data[key].append(values[key].detach().clone())
            if step%150==0:print(json.dumps(dict(step=step)),flush=True)
        with torch.no_grad():_,nv=model(*scene.features())
        v=torch.stack(data['value']);r=torch.stack(data['reward']);d=torch.stack(data['done']);adv=torch.zeros_like(r);gae=torch.zeros(a.envs,device='cuda')
        for t in reversed(range(a.horizon)):
            nextv=nv if t==a.horizon-1 else v[t+1];live=(~d[t]).float();delta=r[t]+.995*nextv*live-v[t];gae=delta+.995*.95*live*gae;adv[t]=gae
        returns=(adv+v).flatten();advantages=adv.flatten();advantages=(advantages-advantages.mean())/(advantages.std()+1e-8);px=torch.stack(data['public']).flatten(0,1);cx=torch.stack(data['critic']).flatten(0,1);ac=torch.stack(data['action']).flatten(0,1);lp=torch.stack(data['log']).flatten();eligible=torch.stack(data['active']).flatten();old=Normal(torch.stack(data['mean']).flatten(0,1),torch.stack(data['scale']).flatten(0,1));assert eligible.any()
        ids=torch.arange(min(4096,len(px)),device='cuda');rows=[]
        for mode in ['original_joint_clip','separate_actor_critic_clip','bounded_separate_actor_clip']:
            candidate=copy.deepcopy(model);opt=torch.optim.Adam(candidate.parameters(),lr=3e-4,eps=1e-5);opt.load_state_dict(saved['optimizer']);actor=list(candidate.actor.parameters())+[candidate.logstd];critic=list(candidate.critic.parameters());dist,value=candidate(px[ids],cx[ids]);newlog=dist.log_prob(ac[ids]).sum(-1);ratio=(newlog-lp[ids]).exp();mask=eligible[ids].float();denom=mask.sum().clamp_min(1);piloss=-(torch.minimum(ratio*advantages[ids],ratio.clamp(.8,1.2)*advantages[ids])*mask).sum()/denom;vloss=.5*(value-returns[ids]).square().mean();loss=piloss+.5*vloss-.001*(dist.entropy().sum(-1)*mask).sum()/denom;opt.zero_grad(set_to_none=True);loss.backward();actor_before=norm(actor);critic_before=norm(critic)
            if mode=='original_joint_clip':torch.nn.utils.clip_grad_norm_(candidate.parameters(),1.)
            else:torch.nn.utils.clip_grad_norm_(actor,1.);torch.nn.utils.clip_grad_norm_(critic,1.)
            actor_after=norm(actor);critic_after=norm(critic);bounded=None
            if mode=='bounded_separate_actor_clip':
                from scripts.wuji_bounded_actor_update import bounded_step
                bounded=bounded_step(candidate,opt,px,old.mean,old.scale,eligible)
            else:opt.step()
            with torch.no_grad():
                new,_=candidate(px,cx);exact=kl_divergence(old,new).sum(-1);sample_ratio=(new.log_prob(ac).sum(-1)-lp).exp();approx=(sample_ratio-1)-(new.log_prob(ac).sum(-1)-lp);shift=(new.mean-old.mean).abs()
            rows.append(dict(bounded_update=bounded,mode=mode,actor_gradient_norm_before=actor_before,critic_gradient_norm_before=critic_before,actor_gradient_norm_after=actor_after,critic_gradient_norm_after=critic_after,active_analytic_Gaussian_KL=float(exact[eligible].mean()),active_sampled_ratio_KL=float(approx[eligible].mean()),active_mean_action_shift=float(shift[eligible].mean()),active_max_action_shift=float(shift[eligible].max()),active_sampled_ratio_max=float(sample_ratio[eligible].max()),loss=float(loss)))
        report=dict(args=vars(a),checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),rows=rows,actual_control_samples=int(eligible.sum()),all_samples=len(eligible),wall_seconds=time.monotonic()-begin,scope='Actual G2 measured/known rollout followedbyonecounterfactualoptimizerstep. No deliveredcandidate, no performanceimprovementclaim, no truth actorfeatures. Original gravity/limits/PD andTABLEprefix retained.')
        (a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps(report,default=str),flush=True)
    finally:scene.close()


if __name__=='__main__':main()
