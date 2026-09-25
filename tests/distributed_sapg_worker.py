"""Small CPU SAPG integration fixture; exercises real optimizer/collectives.

Synthetic observations are only for distributed plumbing tests, not physics.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'rl_games'))

import gym
from hydra import compose, initialize_config_dir
import numpy as np
from omegaconf import OmegaConf
import torch
import torch.distributed as dist

import isaacgymenvs
from isaacgymenvs.learning.a2c_sapg_priv_network_builder import A2CSAPGPrivBuilder
from rl_games.algos_torch import model_builder
from rl_games.common.algo_observer import AlgoObserver
from rl_games.torch_runner import Runner


class SyntheticWujiEnv:
    def __init__(self,rank):
        self.rank=rank
        self.env=SimpleNamespace(device='cpu')
        self.steps=0
        self.frames=[]
        self.rng=torch.Generator().manual_seed(1200+rank)

    def get_env_info(self):
        return dict(observation_space=gym.spaces.Box(-10,10,(137,),dtype=np.float32),
                    action_space=gym.spaces.Box(-1,1,(20,),dtype=np.float32),agents=1,value_size=1)

    def reset(self):
        self.steps=0
        return {'obs':torch.randn(20,137,generator=self.rng)*.1+self.rank*.02}

    def step(self,actions):
        self.steps+=1
        obs=torch.randn(20,137,generator=self.rng)*.1+self.rank*.02
        reward=1-actions.square().mean(-1)
        return {'obs':obs},reward,torch.full((20,),self.steps%8==0,dtype=torch.uint8),{}

    def set_train_info(self,frames,*args):self.frames.append(frames)
    def get_env_state(self):return {}
    def set_env_state(self,state):pass


def fingerprint(model):
    return hashlib.sha256(b''.join(t.detach().cpu().numpy().tobytes() for t in model.state_dict().values())).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--epochs',type=int,default=2)
    p.add_argument('--resume',type=Path)
    p.add_argument('--weights-only',action='store_true')
    args=p.parse_args()
    torch.set_num_threads(1)
    rank=int(os.getenv('RANK','0'));world=int(os.getenv('WORLD_SIZE','1'))
    isaacgymenvs.register_omegaconf_resolvers()
    with initialize_config_dir(version_base='1.1',config_dir=str(ROOT/'isaacgymenvs/cfg')):
        cfg=compose('config',overrides=['hand=wuji_paper','object=knife_wuji_fingertip','train=wujiKnifeSAPG',
                                       'num_envs=20',f'multi_gpu={world>1}'])
    config=OmegaConf.to_container(cfg.train,resolve=True)
    net=config['params']['network'];net['mlp']['units']=[32,16];net['rnn']['units']=16
    net['sapg_priv']['encoder']['units']=[32,16]
    params=config['params']['config']
    params.update(device='cpu',name='distributed_test',full_experiment_name='distributed_test',
                  train_dir=str(args.output),minibatch_size=64,expl_coef_block_size=4,mini_epochs=1,
                  max_epochs=args.epochs,max_frames=args.epochs*20*16*world,save_frequency=1,
                  checkpoint_weights_only=args.weights_only,distributed_timeout_seconds=60)
    model_builder.register_network('actor_critic_sapg_priv',A2CSAPGPrivBuilder)
    runner=Runner(AlgoObserver());runner.load(config)
    env=SyntheticWujiEnv(rank);runner.params['config']['vec_env']=env
    agent=runner.algo_factory.create(runner.algo_name,base_name='run',params=runner.params)
    initial=fingerprint(agent.model)
    try:
        if args.resume:agent.restore(str(args.resume))
        agent.train()
        assert all(torch.isfinite(v).all() for v in agent.model.state_dict().values())
        report=dict(rank=rank,world_size=world,epoch=agent.epoch_num,frame=agent.frame,
                    frame_history=env.frames,model=fingerprint(agent.model),initial_model=initial,
                    optimizer_steps=max(int(v['step']) for v in agent.optimizer.state.values()),
                    normalizer_count=float(agent.model.running_mean_std.count),
                    device=agent.ppo_device)
        assert report['frame']==args.epochs*20*16*world
        assert report['model']!=report['initial_model'] and report['optimizer_steps']>0
        if world>1:
            reports=[None]*world
            dist.all_gather_object(reports,report)
            assert len({r['model'] for r in reports})==1, 'Ranks have different model/normalization weights'
            assert len({r['frame'] for r in reports})==1, 'Ranks have different global counters'
            assert len({r['optimizer_steps'] for r in reports})==1, 'Ranks have different optimizer counts'
            assert len({tuple(r['frame_history']) for r in reports})==1, 'Ranks use different curriculum steps'
        args.output.mkdir(exist_ok=True,parents=True)
        (args.output/f'rank-{rank}.json').write_text(json.dumps(report,indent=2))
        if agent.writer:agent.writer.close()
    finally:
        if dist.is_initialized():dist.destroy_process_group()


if __name__=='__main__':main()
