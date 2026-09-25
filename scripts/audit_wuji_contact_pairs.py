"""Resolve actual knife/hand contact pairs in successful and failed grasps.

CPU tensor pipeline is necessary for Isaac Gym rigid-contact inspection; physics
still runs in GPU PhysX. This is a short diagnostic, not the formal GPU-pipeline
policy evaluation. Both original validation grasps remain excluded from training.
"""
import argparse,json
from pathlib import Path
from collections import defaultdict
from scripts.wuji_goal_common import configuration,make_player,policy_observation
from isaacgym import gymapi
import numpy as np
import torch
from omegaconf import OmegaConf

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    repeats=8;n=4*repeats
    cfg=configuration('wuji_acquisition_fingertip_subset',n,
        ['object=knife_wuji_fingertip_acquisition000','test=True','pipeline=cpu'],train='wujiAcquisitionSAPG',seed=1818)
    env,player=make_player(cfg,a.checkpoint)
    pool=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_fingertip/000/test/valid_grasps.npy')
    env.configure_fixed_grasp_consecutive_evaluation('000',pool[0],goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=n)
    env.eval_grasp_states[2*repeats:]=torch.as_tensor(pool[2],device=env.device)
    handle=env.envs[0];names={}
    for actor_name in ['hand','object']:
        actor=env.gym.find_actor_handle(handle,actor_name)
        if actor<0:raise ValueError('Unknown actor name: '+actor_name)
        for name in env.gym.get_actor_rigid_body_names(handle,actor):
            index=env.gym.find_actor_rigid_body_index(handle,actor,name,gymapi.DOMAIN_ENV)
            names[index]=(actor_name,name)
    groups=['grasp0_hold','grasp0_policy','grasp2_hold','grasp2_policy']
    records={key:defaultdict(lambda:dict(samples=0,total_force=0.,max_force=0.)) for key in groups}
    traces=[];obs=env.reset();seen=[0]*4
    try:
        for step in range(60):
            active=env.eval_active_mask.clone()
            with torch.no_grad():action=player.get_action(policy_observation(player,obs),is_deterministic=True)
            action[:repeats]=0;action[2*repeats:3*repeats]=0
            obs,_,done,_=env.step(action)
            if player.is_rnn:
                ids=done.nonzero(as_tuple=False).squeeze(-1)
                for state in player.states:state[:,ids,:]=0
            traces.append(dict(step=step,travel_mm=((env.obj_dof_pos-env.init_obj_dof_pos)*1000).cpu().tolist(),
                active=active.cpu().tolist(),done=done.cpu().tolist()))
            if step%3!=2:continue
            env.gym.fetch_results(env.sim,True)
            for i,handle in enumerate(env.envs):
                if not active[i] or done[i]:continue
                group=groups[i//repeats];seen[i//repeats]+=1;sample={}
                for contact in env.gym.get_env_rigid_contacts(handle):
                    pair=[names.get(int(contact['body0'])),names.get(int(contact['body1']))]
                    if any(x is None for x in pair) or pair[0][0]==pair[1][0]:continue
                    force=float(contact['lambda'])
                    if force<=1e-6:continue
                    key=' <-> '.join(sorted(x[1] for x in pair));sample[key]=sample.get(key,0.)+force
                for key,force in sample.items():
                    r=records[group][key];r['samples']+=1;r['total_force']+=force;r['max_force']=max(r['max_force'],force)
        result={}
        for index,group in enumerate(groups):
            result[group]={key:dict(contact_fraction=r['samples']/max(seen[index],1),
                mean_force_over_all_samples=r['total_force']/max(seen[index],1),max_force=r['max_force']) for key,r in records[group].items()}
        report=dict(protocol=__doc__,samples_per_group=seen,contacts=result,traces=traces,
            body_names={str(k):v for k,v in names.items()})
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
        print(json.dumps(result),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
