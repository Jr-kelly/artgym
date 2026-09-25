"""Shared, explicit environment/player construction for Wuji acquisition audits."""
from pathlib import Path
import isaacgym  # Must precede torch.
import torch
from hydra import compose, initialize_config_dir
from omegaconf import OmegaConf
import isaacgymenvs

ROOT=Path(__file__).resolve().parents[1]


def configuration(task='wuji_demo_corrected',envs=64,overrides=(),train='wujiDemoAlignedSAPG',seed=20260922):
    isaacgymenvs.register_omegaconf_resolvers()
    with initialize_config_dir(version_base='1.1',config_dir=str(ROOT/'isaacgymenvs/cfg')):
        return compose(config_name='config',overrides=[f'task={task}','hand=wuji_paper',
            'object=knife_wuji_demo_aligned',f'train={train}',f'num_envs={envs}',
            'headless=True','pipeline=gpu','graphics_device_id=-1','force_render=False',
            'num_subscenes=0','multi_gpu=False',f'seed={seed}']+list(overrides))


def make_env(cfg):
    return isaacgymenvs.make(seed=cfg.seed,task=cfg.task.name,num_envs=cfg.task.env.numEnvs,
        sim_device=cfg.sim_device,rl_device=cfg.rl_device,graphics_device_id=cfg.graphics_device_id,
        headless=True,force_render=False,cfg=cfg)


def make_player(cfg,checkpoint):
    from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
    from isaacgymenvs.learning import a2c_sapg_priv_network_builder
    from isaacgymenvs.utils.rlgames_utils import RLGPUEnv
    from isaacgymenvs.utils.player_utils import init_player_rnn_for_batch
    from rl_games.algos_torch import model_builder
    from rl_games.common import env_configurations,vecenv
    from rl_games.torch_runner import Runner
    env_configurations.register('rlgpu',dict(vecenv_type='RLGPU',env_creator=lambda **kw:make_env(cfg)))
    vecenv.register('RLGPU',lambda config_name,num_actors,**kw:RLGPUEnv(config_name,num_actors,**kw))
    model_builder.register_network('actor_critic_sapg_priv',a2c_sapg_priv_network_builder.A2CSAPGPrivBuilder)
    config=preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True))
    blocks=_infer_expl_num_blocks(Path(checkpoint))
    if blocks:config['params']['config'].setdefault('player',{})['expl_num_blocks']=blocks
    runner=Runner();runner.load(config);player=runner.create_player();player.restore(str(checkpoint))
    if blocks and player.intr_reward_coef_embd is not None:
        player.intr_reward_coef_embd[:]=50.0  # Same deterministic block as the official evaluator.
    player.has_batch_dimension=True
    env=player.env.env
    init_player_rnn_for_batch(player,env.num_envs)
    return env,player


def policy_observation(player, observations):
    """Match BasePlayer.env_reset/env_step, including the SAPG coefficient ID."""
    obs = player.obs_to_torch(observations)
    if player.intr_reward_coef_embd is not None:
        obs = torch.cat((obs, player.intr_reward_coef_embd), dim=1)
    return obs
