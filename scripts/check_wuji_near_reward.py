"""Verify the actual Gaussian near-endpoint reward at randomized command times.

Only its coefficient changes. Goal arrival bonus, other reward equations,
physics, action mapping and observations retain the migration configuration.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
import numpy as np
from omegaconf import OmegaConf
import torch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coefficient',type=float,choices=[.1,5.],required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    checkpoint=root/'runs/wuji-goal/verified-policies/teacher-official-timed2-cp10/teacher.pth'
    cfg=configuration('wuji_acquisition_official_variable_timed',32,
        ['hand=wuji_paper_official_actuator','object=knife_wuji_precision_near01','test=False',
         'object.reward.GoalDistance2='+str(args.coefficient)],train='wujiAcquisitionSAPG',seed=20261023)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env,player=make_player(cfg,checkpoint)
    original=env.compute_reward
    checks=dict(transitions=0,near_reward_checks=0,positive_near_steps=0,clock_switches=0,short=0,long=0)

    def reward(actions):
        goal=env.goal_obj_dof_pos.clone();deadline=env.command_deadline.clone()
        error=torch.norm(env.obj_dof_pos-goal,p=1,dim=-1)
        valid=~env.truncated_envs&torch.isfinite(env.obj_dof_pos).all(-1)
        expected=torch.exp(-(error/cfg.object.task.success_threshold)**2)*valid*args.coefficient
        original(actions)
        assert env.reward_scales_current['GoalDistance2']==args.coefficient
        assert env.reward_scales_current['Success']==50
        assert torch.allclose(env.extras['GoalDistance2'],expected.mean(),rtol=1e-5,atol=1e-6)
        due=(env.progress_buf>=deadline)&(env.reset_buf==0)
        assert torch.equal((goal!=env.goal_obj_dof_pos).any(-1),due)
        intervals=env.command_deadline[due]-env.progress_buf[due]
        assert ((intervals==60)|(intervals==150)).all()
        checks['short']+=int((intervals==60).sum());checks['long']+=int((intervals==150).sum())
        checks['clock_switches']+=int(due.sum());checks['near_reward_checks']+=1
        checks['positive_near_steps']+=int(expected.mean()>0)

    env.compute_reward=reward
    try:
        for handle,obj in zip(env.envs,env.object_handles):
            hand=env.gym.find_actor_handle(handle,'hand')
            properties=env.gym.get_actor_dof_properties(handle,hand)
            for key in ['stiffness','damping','armature']:
                assert np.allclose(properties[key],cfg.hand.dof_props[key],atol=1e-7,rtol=1e-6)
            assert np.allclose(env.gym.get_actor_dof_properties(handle,obj)['damping'],.3)
        obs=player.env_reset(player.env);init_player_rnn_for_batch(player,32)
        for step in range(200):
            with torch.no_grad():action=player.get_action(obs,is_deterministic=True)
            obs,rew,done,_=player.env_step(player.env,action)
            assert torch.isfinite(rew).all()
            if player.is_rnn:
                ids=done.nonzero(as_tuple=False).squeeze(-1)
                for state in player.states:state[:,ids,:]=0
            checks['transitions']+=32
        assert checks['near_reward_checks']==200 and all(checks[k]>0 for k in ['short','long','positive_near_steps'])
        paths=['scripts/check_wuji_near_reward.py','isaacgymenvs/tasks/artmanip.py',
               'isaacgymenvs/tasks/wuji_variable_timed_acquisition.py','isaacgymenvs/tasks/wuji_timed_acquisition.py']
        result=dict(status='passed',coefficient=args.coefficient,checks=checks,scope=__doc__,
            checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            sources={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
