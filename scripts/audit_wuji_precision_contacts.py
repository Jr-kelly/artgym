"""Exact contact-pair diagnostic on predeclared saved perturbations.

CPU tensors are required by get_env_rigid_contacts; PhysX remains on the GPU.
This is a diagnostic change of batch/pipeline, not the original100trial score.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from scripts.wuji_goal_common import configuration, make_player
from isaacgym import gymapi
from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
from omegaconf import OmegaConf
import numpy as np
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--initial-states',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rows',type=int,nargs='+',default=[0,2,76]);p.add_argument('--repeats',type=int,default=4)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    initial=np.load(a.initial_states);indices=np.repeat(a.rows,a.repeats);n=len(indices)
    cfg=configuration('wuji_acquisition_precision',n,['object=knife_wuji_acquisition_precision',
        'test=True','pipeline=cpu','task.env.episodeLength=360'],train='wujiAcquisitionSAPG',seed=3030)
    env,player=make_player(cfg,a.checkpoint)
    env.configure_fixed_grasp_consecutive_evaluation('000',initial[indices[0]],
        goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=n)
    env.eval_grasp_states[:]=torch.as_tensor(initial[indices],device=env.device)
    body_names={}
    for actor_name in ['hand','object']:
        actor=env.gym.find_actor_handle(env.envs[0],actor_name)
        for name in env.gym.get_actor_rigid_body_names(env.envs[0],actor):
            idx=env.gym.find_actor_rigid_body_index(env.envs[0],actor,name,gymapi.DOMAIN_ENV)
            body_names[idx]=(actor_name,name)
    frames=[];contacts=[];original=env.compute_reward;latest={}
    def capture(actions):
        active=env.eval_active_mask.clone();stage=env.eval_goal_stage.clone();original(actions)
        angle=2*torch.asin(torch.norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=-1).clamp(0,1))
        latest.clear();latest.update(active=active,stage=stage,slider=env.obj_dof_pos[:,0].clone(),
            event=env.goal_achieved_step.clone(),q=env.hand_dof_pos.clone(),target=env.cur_targets[:,:20].clone(),
            rotation=angle,drift=torch.norm(env.object_pos-env.init_object_pos,dim=-1))
        frames.append({k:v.detach().cpu().numpy() for k,v in latest.items()})
    env.compute_reward=capture
    try:
        obs=player.env_reset(player.env);started=time.monotonic();last_log=started
        for step in range(360):
            if env.is_grasp_evaluation_complete():break
            with torch.no_grad():action=player.get_action(obs,is_deterministic=True)
            obs,_,done,_=player.env_step(player.env,action)
            if player.is_rnn:
                ids=done.nonzero(as_tuple=False).squeeze(-1)
                for state in player.states:state[:,ids,:]=0
            env.gym.fetch_results(env.sim,True)
            for i,handle in enumerate(env.envs):
                if not latest['active'][i] or done[i]:continue
                pairs={}
                for contact in env.gym.get_env_rigid_contacts(handle):
                    pair=[body_names.get(int(contact['body0'])),body_names.get(int(contact['body1']))]
                    if any(v is None for v in pair) or pair[0][0]==pair[1][0]:continue
                    magnitude=float(contact['lambda'])
                    if magnitude<=1e-6:continue
                    key=' <-> '.join(sorted(v[1] for v in pair));pairs[key]=pairs.get(key,0.)+magnitude
                contacts.append(dict(step=step,env=i,initial_row=int(indices[i]),stage=int(latest['stage'][i]),pairs=pairs))
            if time.monotonic()-last_log>20:
                print(json.dumps(dict(step=step,active=int(env.eval_active_mask.sum()),seconds=time.monotonic()-started)),flush=True);last_log=time.monotonic()
        trace={k:np.stack([r[k] for r in frames]) for k in frames[0]};np.savez_compressed(a.output/'trace.npz',**trace)
        stats=env.get_grasp_consecutive_evaluation_stats()
        result=dict(protocol=__doc__,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
            initial_states_sha256=hashlib.sha256(a.initial_states.read_bytes()).hexdigest(),
            audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=a.rows,repeats=a.repeats,
            environment_initial_rows=indices.tolist(),stats=stats,contacts=contacts,
            contact_magnitude='Raw IsaacGym RigidContact.lambda summed over a hand/object body pair; no calibrated force claim.')
        (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
        print(json.dumps(dict(cycles=stats['consecutive_success_cycles'],reasons=stats['completion_reason'])),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
