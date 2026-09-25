"""Compare actual episode returns and terminal causes of hold/replay/policy."""
import argparse,json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env,make_player,policy_observation,ROOT
import numpy as np
import torch
import yaml
from omegaconf import OmegaConf


def main():
    p=argparse.ArgumentParser();p.add_argument('--controller',choices=['replay','hold','random','checkpoint'],required=True)
    p.add_argument('--checkpoint');p.add_argument('--task',default='wuji_demo_corrected')
    p.add_argument('--envs',type=int,default=64);p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--curriculum-step',type=int,default=0);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--override',action='append',default=[]);p.add_argument('--save-expert',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    cfg=configuration(a.task,a.envs,a.override)
    (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env,player=make_player(cfg,a.checkpoint) if a.controller=='checkpoint' else (make_env(cfg),None)
    env.set_train_info(0,epoch_num=a.curriculum_step)
    preset=yaml.safe_load((ROOT/'assets/demo/wuji_knife/fingertip_preset.yaml').read_text())
    waypoints=np.asarray(preset['joint_waypoints_rad']);dt=env.dt*env.control_freq_inv
    observations=env.reset();zero=torch.zeros((a.envs,20),device=env.device)
    lengths=torch.zeros(a.envs,device=env.device);returns=lengths.clone();stages=lengths.clone()
    maxima=lengths.clone();drifts=lengths.clone();first_done=torch.zeros(a.envs,dtype=torch.bool,device=env.device)
    terms={};episodes=[];traces=[];expert_obs=[];expert_actions=[];expert_valid=[]
    # Capture terminal physical measurements before ArtManip reset overwrites them.
    original=env.compute_reward;captured={}
    def reward_capture(actions):
        original(actions)
        captured.update(slider=env.obj_dof_pos[:,0].clone(),drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1),
            stage=env.goal_achieved_step.clone(),fall=env.debug_reset_cause_fall.clone(),invalid=env.debug_reset_cause_invalid.clone(),
            goal=env.goal_indices.clone(),contact=env.contact_info.clone(),q=env.hand_dof_pos.clone(),target=env.cur_targets[:,:20].clone())
    env.compute_reward=reward_capture
    for step in range(round(a.seconds/dt)):
        action=zero
        if a.controller=='replay':
            t=step*dt;q=np.array([np.interp(t,waypoints[:,0],waypoints[:,j+1]) for j in range(20)])
            target=torch.as_tensor(q,device=env.device,dtype=torch.float32).expand(a.envs,-1)
            action=env.targets_to_actions(target).clamp(-1,1)
        elif a.controller=='random':action=torch.randn_like(zero)*.0183
        elif player:action=player.get_action(policy_observation(player,observations),is_deterministic=True)
        if a.save_expert:
            expert_obs.append(observations['obs'].clone());expert_actions.append(action.clone())
            expert_valid.append(~first_done.clone())
        observations,reward,done,info=env.step(action)
        lengths+=1;returns+=reward;stages+=captured['stage']
        maxima=torch.maximum(maxima,captured['slider']);drifts=torch.maximum(drifts,captured['drift'])
        for key in env.reward_scales:terms[key]=terms.get(key,0)+float(info[key])
        ended=torch.where(done)[0]
        for i in ended.tolist():
            episodes.append(dict(env=i,steps=int(lengths[i]),seconds=float(lengths[i]*dt),return_value=float(returns[i]),
                stages=int(stages[i]),max_slider=float(maxima[i]),max_drift=float(drifts[i]),
                fall=bool(captured['fall'][i]),invalid=bool(captured['invalid'][i]),first=not bool(first_done[i])))
        if len(ended):
            first_done[ended]=True;lengths[ended]=0;returns[ended]=0;stages[ended]=0;maxima[ended]=0;drifts[ended]=0
            if player and player.is_rnn:
                for state in player.states:state[:,ended,:]=0
        if step%max(1,round(.1/dt))==0:
            traces.append({k:v[:8].detach().cpu().numpy() for k,v in captured.items()})
    first=[r for r in episodes if r['first']]
    pending=[dict(env=i,steps=int(lengths[i]),return_value=float(returns[i]),stages=int(stages[i]),
        max_slider=float(maxima[i]),max_drift=float(drifts[i])) for i in range(a.envs) if not first_done[i]]
    result=dict(controller=a.controller,task=a.task,curriculum_step=a.curriculum_step,
        checkpoint=a.checkpoint,control_dt=dt,num_envs=a.envs,reward_scales=env.reward_scales_current,
        reward_term_sums_mean=terms,first_episodes=first,unfinished_first_episodes=pending,
        episode_count=len(episodes),fall_count=sum(r['fall'] for r in episodes),
        complete_cycle_episodes=sum(r['stages']>=2 for r in episodes),all_episodes=episodes)
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    np.savez_compressed(a.output/'trace.npz',**{k:np.stack([r[k] for r in traces]) for k in traces[0]})
    if a.save_expert:
        torch.save(dict(obs=torch.stack(expert_obs).cpu(),actions=torch.stack(expert_actions).cpu(),
            valid=torch.stack(expert_valid).cpu(),
            cfg=OmegaConf.to_container(cfg,resolve=True)),a.output/'expert.pt')
    print(json.dumps({k:v for k,v in result.items() if k not in ('first_episodes','unfinished_first_episodes','all_episodes')}))
    print('FIRST',first[:1],'UNFINISHED',pending[:1])
    env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
