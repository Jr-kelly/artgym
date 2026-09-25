"""Actual PhysX checks of sampled command deadlines and inherited evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
import torch
from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
from omegaconf import OmegaConf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixed-control',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    override=['hand=wuji_paper_official_actuator','object=knife_wuji_precision_near01','test=False']
    if args.fixed_control:override+=['task.env.trainingCommandDurationsSec=[2.0,2.0]']
    cfg=configuration('wuji_acquisition_official_variable_timed',32,override,train='wujiAcquisitionSAPG',seed=20261015)
    OmegaConf.save(cfg,args.output/'config.yaml',resolve=True)
    env,player=make_player(cfg,args.checkpoint)
    counts=dict(training_transitions=0,deadline_switches=0,off_deadline_arrivals=0,evaluation_arrivals=0,
                short_intervals=0,long_intervals=0)
    original=env.compute_reward

    def checked(actions):
        goal=env.goal_obj_dof_pos.clone();deadline=env.command_deadline.clone()
        original(actions)
        changed=(env.goal_obj_dof_pos!=goal).any(-1)
        if env.eval_mode:
            assert torch.equal(changed,env.goal_achieved_step.bool())
            counts['evaluation_arrivals']+=int(changed.sum())
        else:
            due=(env.progress_buf>=deadline)&(env.reset_buf==0)
            assert torch.equal(changed,due),'A command switched before/after its declared deadline'
            arrived=env.goal_achieved_step.bool()&~due
            assert not changed[arrived].any()
            new=env.command_deadline[due]-env.progress_buf[due]
            assert ((new==60)|(new==150)).all()
            if args.fixed_control:assert (new==60).all()
            counts['short_intervals']+=int((new==60).sum());counts['long_intervals']+=int((new==150).sum())
            counts['training_transitions']+=env.num_envs
            counts['deadline_switches']+=int(due.sum())
            counts['off_deadline_arrivals']+=int(arrived.sum())
        assert torch.isfinite(env.rew_buf).all()

    env.compute_reward=checked
    try:
        for mode,steps in [('training',350),('evaluation',125)]:
            if mode=='evaluation':env.configure_grasp_consecutive_evaluation('000',goal_sequence=tuple(cfg.object.task.goals),grasp_split='train',episodes_per_grasp=32)
            obs=player.env_reset(player.env);init_player_rnn_for_batch(player,env.num_envs)
            for step in range(steps):
                actions=player.get_action(obs,is_deterministic=True)
                obs,_,done,_=player.env_step(player.env,actions)
                if player.is_rnn:
                    ids=done.nonzero(as_tuple=False).squeeze(-1)
                    for state in player.states:state[:,ids,:]=0
            print(json.dumps(dict(mode=mode,counts=counts)),flush=True)
        assert counts['training_transitions']==11200
        assert all(counts[key]>0 for key in ['deadline_switches','off_deadline_arrivals','evaluation_arrivals','short_intervals'])
        assert counts['long_intervals']==0 if args.fixed_control else counts['long_intervals']>0
        sources=[Path(__file__),Path('isaacgymenvs/tasks/wuji_variable_timed_acquisition.py'),Path('isaacgymenvs/tasks/wuji_timed_acquisition.py')]
        result=dict(status='passed',counts=counts,fixed_control=args.fixed_control,
                    checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                    sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},scope=__doc__)
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
