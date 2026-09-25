import os

import isaacgym  # noqa: F401
import hydra
import torch
from omegaconf import DictConfig

import isaacgymenvs

isaacgymenvs.register_omegaconf_resolvers()


def preprocess_train_config(cfg, config_dict):
    train_cfg = config_dict["params"]["config"]
    train_cfg["device"] = cfg.rl_device
    train_cfg["full_experiment_name"] = cfg.get("experiment") or train_cfg["name"]
    return config_dict


def _get_network_inputs(net_cfg):
    input_cfg = net_cfg.get("inputs") or net_cfg.get("input_preprocessors")
    if input_cfg is None:
        raise KeyError(
            f"network `{net_cfg.name}` requires `inputs` (or legacy `input_preprocessors`) when using dict observations"
        )
    return list(input_cfg.keys())


def _network_uses_concat(net_cfg):
    return net_cfg.name not in {"complex_net", "actor_critic_dict"}


def _validate_multi_gpu_launch(cfg):
    if not cfg.multi_gpu:
        return

    missing = [name for name in ("LOCAL_RANK", "RANK", "WORLD_SIZE") if os.getenv(name) is None]
    if missing:
        raise RuntimeError(
            "multi_gpu=True requires launching with torchrun so "
            f"{', '.join(missing)} are defined. "
            "Example: torchrun --standalone --nnodes=1 --nproc_per_node=4 "
            "-m isaacgymenvs.train task=artmanip ... multi_gpu=True"
        )


def _init_multi_gpu_runtime(cfg):
    if not cfg.multi_gpu:
        return {"enabled": False, "local_rank": 0, "global_rank": 0, "world_size": 1}

    local_rank = int(os.getenv("LOCAL_RANK", "0"))
    global_rank = int(os.getenv("RANK", "0"))
    world_size = int(os.getenv("WORLD_SIZE", "1"))

    if not torch.cuda.is_available():
        raise RuntimeError("multi_gpu=True requires CUDA, but torch.cuda.is_available() is False.")
    if local_rank<0 or local_rank>=torch.cuda.device_count():
        raise RuntimeError(f'LOCAL_RANK={local_rank} exceeds {torch.cuda.device_count()} visible GPUs')
    if world_size<2 or global_rank<0 or global_rank>=world_size:
        raise RuntimeError('Invalid torchrun rank/world size for multi-GPU training')

    torch.cuda.set_device(local_rank)
    cfg.sim_device = f"cuda:{local_rank}"
    cfg.rl_device = f"cuda:{local_rank}"
    cfg.graphics_device_id = local_rank if not cfg.headless or cfg.capture_video or cfg.task.env.enableCameraSensors else -1

    return {
        "enabled": True,
        "local_rank": local_rank,
        "global_rank": global_rank,
        "world_size": world_size,
    }


def _is_rank0(cfg):
    if not cfg.multi_gpu:
        return True
    return int(os.getenv("RANK", "0")) == 0


@hydra.main(version_base="1.1", config_name="config", config_path="./cfg")
def launch_rlg_hydra(cfg: DictConfig):
    import gym
    from datetime import datetime

    import isaacgymenvs

    from isaacgymenvs.learning import a2c_dict_network_builder, a2c_sapg_priv_network_builder
    from isaacgymenvs.tasks import isaacgym_task_map
    from isaacgymenvs.utils.reformat import omegaconf_to_dict, print_dict
    from isaacgymenvs.utils.rlgames_utils import (
        ComplexObsRLGPUEnv,
        RLGPUAlgoObserver,
        RLGPUEnv,
    )
    from isaacgymenvs.utils.utils import set_np_formatting, set_seed
    from rl_games.algos_torch import model_builder
    from rl_games.common import env_configurations, vecenv
    from rl_games.torch_runner import Runner

    _validate_multi_gpu_launch(cfg)
    knife_dataset = str(cfg.get('asset_dir') or cfg.object.asset.asset_root).rstrip('/').split('/')[-1]
    if knife_dataset == 'knife_wuji_official_approved':
        from scripts.check_official_wuji_transfer import validate
        declared=list(cfg.task.env.get('officialAcquisitionSubset',[]))
        if (str(cfg.task.name)!='wuji_acquisition' or not declared or
                list(cfg.object.asset.instance_id_list)!=declared):
            raise ValueError('Declare the exact official Wuji migration subset before training')
        for instance in declared:
            validate(str(instance),require_train=True)
    if knife_dataset in {'knife_wuji_paper', 'knife_wuji_fingertip'}:
        import json
        from pathlib import Path
        from scripts.validate_paper_grasps import check_dataset
        if knife_dataset == 'knife_wuji_fingertip':
            from scripts.filter_wuji_fingertip_grasps import check_dataset
        manifest = json.loads((Path(__file__).resolve().parents[1] / 'assets/objects' / knife_dataset / 'manifest.json').read_text())
        acquisition_instance=cfg.task.env.get('acquisitionGraspGate')
        if acquisition_instance is not None:
            acquisition_instance=str(acquisition_instance)
            if (str(cfg.task.name)!='wuji_acquisition' or knife_dataset!='knife_wuji_fingertip'
                    or list(cfg.object.asset.instance_id_list)!=[acquisition_instance]
                    or acquisition_instance not in manifest['train_ids']):
                raise ValueError('Acquisition subset must explicitly name one validated training geometry')
            from scripts.check_wuji_transfer_data import validate
            validate(acquisition_instance)
        elif list(cfg.object.asset.instance_id_list) != manifest['train_ids']:
            raise ValueError('Paper knife training must use exactly the 30 training geometries, excluding 030–034')
        if cfg.hand.get('self_collision_mode') != 'digit_filtered':
            raise ValueError('Paper knife training requires hand=wuji_paper for validated self-collision filtering')
        if acquisition_instance is None:
            check_dataset()
    dist_runtime = _init_multi_gpu_runtime(cfg)
    if dist_runtime['enabled']:
        train_cfg=cfg.train.params.config
        actors=int(cfg.task.env.numEnvs)
        if actors*int(train_cfg.horizon_length)%int(train_cfg.minibatch_size):
            raise ValueError('Per-rank rollout batch must be divisible by minibatch_size')
        if str(train_cfg.expl_type).startswith('mixed_expl') and actors%int(train_cfg.expl_coef_block_size):
            raise ValueError('Per-rank environment count must be divisible by the SAPG block size')
        print(f"Rank {dist_runtime['global_rank']}/{dist_runtime['world_size']}: "
              f"simulation={cfg.sim_device}, policy={cfg.rl_device}, environments={actors}",flush=True)
    cfg_dict = omegaconf_to_dict(cfg)
    if _is_rank0(cfg):
        print_dict(cfg_dict)
    set_np_formatting()
    cfg.seed = set_seed(
        cfg.seed,
        torch_deterministic=cfg.torch_deterministic,
        rank=dist_runtime["global_rank"],
    )
    run_name = f"{cfg.get('experiment') or cfg.task_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    def create_env(**kwargs):
        env = isaacgymenvs.make(
            cfg.seed,
            cfg.task_name,
            cfg.task.env.numEnvs,
            cfg.sim_device,
            cfg.rl_device,
            cfg.graphics_device_id,
            cfg.headless,
            cfg.multi_gpu,
            cfg.capture_video,
            cfg.force_render,
            cfg,
            **kwargs,
        )
        if cfg.capture_video:
            env.is_vector_env = True
            env = gym.wrappers.RecordVideo(
                env,
                f"videos/{run_name}",
                step_trigger=lambda step: step % cfg.capture_video_freq == 0,
                video_length=cfg.capture_video_len,
            )
        return env

    env_configurations.register(
        "rlgpu",
        {
            "vecenv_type": "RLGPU",
            "env_creator": lambda **kwargs: create_env(**kwargs),
        },
    )

    env_cls = isaacgym_task_map[cfg.task_name]
    dict_cls = (
        (hasattr(env_cls, "dict_obs_cls") and env_cls.dict_obs_cls)
        or cfg.task.env.get("use_dict_obs", False)
    )

    if dict_cls:
        obs_spec = {}
        actor_net_cfg = cfg.train.params.network
        obs_spec["obs"] = {
            "names": _get_network_inputs(actor_net_cfg),
            "concat": _network_uses_concat(actor_net_cfg),
            "space_name": "observation_space",
        }
        if "central_value_config" in cfg.train.params.config:
            critic_net_cfg = cfg.train.params.config.central_value_config.network
            obs_spec["states"] = {
                "names": _get_network_inputs(critic_net_cfg),
                "concat": _network_uses_concat(critic_net_cfg),
                "space_name": "state_space",
            }
        vecenv.register("RLGPU", lambda config_name, num_actors, **kwargs: ComplexObsRLGPUEnv(config_name, num_actors, obs_spec, **kwargs))
    else:
        vecenv.register("RLGPU", lambda config_name, num_actors, **kwargs: RLGPUEnv(config_name, num_actors, **kwargs))

    rlg_config_dict = preprocess_train_config(cfg, omegaconf_to_dict(cfg.train))

    model_builder.register_network("actor_critic_dict", a2c_dict_network_builder.A2CBuilder)
    model_builder.register_network("actor_critic_sapg_priv", a2c_sapg_priv_network_builder.A2CSAPGPrivBuilder)
    runner = Runner(RLGPUAlgoObserver())
    runner.load(rlg_config_dict)
    runner.reset()
    try:
        runner.run(
            {
                "train": not cfg.test,
                "play": cfg.test,
                "checkpoint": cfg.checkpoint,
                "sigma": cfg.sigma if cfg.sigma != "" else None,
            }
        )
    finally:
        if torch.distributed.is_initialized():
            torch.distributed.destroy_process_group()


if __name__ == "__main__":
    launch_rlg_hydra()
