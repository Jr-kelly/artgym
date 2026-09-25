"""Compare hold, learned policy and explicitly scripted anchored IK control.

All groups keep a free knife and a passive slider. The anchored IK group tests
whether a continuous contact path is dynamically feasible; it is not a learned
policy result and must never be reported as RL or student success.
"""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
from isaacgymenvs.student_eval_utils import run_grasp_evaluation_loop
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_conjugate
import numpy as np
import torch
from omegaconf import OmegaConf

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--grasp-index',type=int,default=2)
    p.add_argument('--controller-set',choices=['path','interventions'],default='path')
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    records=json.loads((ROOT/'runs/wuji-goal/diagnostics/reach-continuity-000.json').read_text())['records']
    record=next(r for r in records if r['split']=='test' and r['grasp_index']==a.grasp_index)
    if not record['continuous']['passed']:raise ValueError('This diagnostic needs a complete anchored IK path')
    path=np.asarray(record['continuous']['thumb_path_rad'])
    state=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_fingertip/000/test/valid_grasps.npy')[a.grasp_index]
    n=32;cfg=configuration('wuji_acquisition_fingertip_subset',3*n,
        ['object=knife_wuji_fingertip_acquisition000','test=True'],train='wujiAcquisitionSAPG',seed=1717)
    env,player=make_player(cfg,a.checkpoint);dt=env.dt*env.control_freq_inv
    env.configure_fixed_grasp_consecutive_evaluation('000',state,goal_sequence=tuple(cfg.object.task.goals),episodes_per_grasp=3*n)
    frames=[];original_reward=env.compute_reward
    def capture(actions):
        active=env.eval_active_mask.clone();original_reward(actions)
        rotation=2*torch.asin(torch.linalg.vector_norm(quat_mul(env.object_rot,quat_conjugate(env.init_object_rot))[:,:3],dim=1).clamp(0,1))
        data=dict(active=active,slider_travel=env.obj_dof_pos[:,0]-env.init_obj_dof_pos[:,0],
            drift=torch.linalg.vector_norm(env.object_pos-env.init_object_pos,dim=1),rotation=rotation,
            events=env.goal_achieved_step.clone(),contact=env.contact_info.clone(),q=env.hand_dof_pos.clone(),
            targets=env.cur_targets[:,:20].clone())
        frames.append({k:v.detach().cpu().numpy() for k,v in data.items()})
    env.compute_reward=capture
    original_action=player.get_action;step=[0]
    # Exact0.3 s dwell after the4 s outbound path and after returning.
    times=np.r_[np.arange(41)*.1,4.3,4.3+np.arange(1,41)*.1,8.6]
    waypoints=np.concatenate([path[:41],path[40:41],path[41:],path[-1:]],axis=0)
    def action(observation,is_deterministic=True):
        result=original_action(observation,is_deterministic=is_deterministic).clone()
        if a.controller_set=='interventions':
            result[n:2*n,:16]=0
            result[2*n:,:16]=0
            result[2*n:,16:]*=.25
            return result
        result[:n]=0 # zero actions preserve the cached support and thumb targets
        t=(step[0]*dt)%times[-1]
        q=np.asarray([np.interp(t,times,waypoints[:,j]) for j in range(4)])
        targets=env.init_targets[:,:20].clone()
        targets[:,16:20]+=torch.as_tensor(q-state[16:20],device=env.device,dtype=targets.dtype)
        scripted=env.targets_to_actions(targets).clamp(-1,1)
        result[2*n:]=scripted[2*n:];step[0]+=1
        return result
    player.get_action=action
    try:
        stats=run_grasp_evaluation_loop(player,env,deterministic=True,progress_interval_sec=15)
        trace={k:np.stack([f[k] for f in frames]) for k in frames[0]}
        np.savez_compressed(a.output/'trace.npz',**trace)
        groups={}
        group_names=(['learned_cp100','learned_fixed_support','learned_fixed_support_quarter_thumb']
            if a.controller_set=='interventions' else ['hold_zero_action','learned_cp100','scripted_anchored_ik'])
        for group,name in enumerate(group_names):
            ids=range(group*n,(group+1)*n);cycles=[stats['consecutive_success_cycles'][i] for i in ids]
            strict=0
            for i in ids:
                events=np.flatnonzero(trace['events'][:,i]*trace['active'][:,i]);end=events[1]+1 if len(events)>1 else len(trace['active'])
                strict+=int(cycles[i-group*n]>=1 and trace['drift'][:end,i].max()<.01 and trace['rotation'][:end,i].max()<.25)
            groups[name]=dict(successful_trials=sum(c>=1 for c in cycles),total_trials=n,strict_first_cycle_trials=strict,
                mean_cycles=float(np.mean(cycles)),max_travel_mm=float(trace['slider_travel'][:,group*n:(group+1)*n][trace['active'][:,group*n:(group+1)*n]].max()*1000),
                completion_reasons=[stats['completion_reason'][i] for i in ids])
        report=dict(grasp_index=a.grasp_index,groups=groups,protocol=__doc__,seed=1717,controller_set=a.controller_set,
            path_times_seconds=times.tolist(),
            checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),ik_record=record)
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
        print(json.dumps(groups),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
