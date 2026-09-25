"""Torchrun rendezvous and device-safe synchronization for the local trainer."""
from datetime import timedelta
import os

import torch
import torch.distributed as dist


def init_distributed(config):
    rank=int(os.environ['RANK'])
    local_rank=int(os.environ['LOCAL_RANK'])
    world_size=int(os.environ['WORLD_SIZE'])
    cpu=str(config.get('device','cuda:0'))=='cpu'
    device='cpu' if cpu else f'cuda:{local_rank}'
    if not cpu:
        if local_rank>=torch.cuda.device_count():
            raise RuntimeError(f'LOCAL_RANK={local_rank} exceeds visible CUDA devices')
        torch.cuda.set_device(local_rank)
    backend='gloo' if cpu else 'nccl'
    timeout=timedelta(seconds=int(config.get('distributed_timeout_seconds',600)))
    if not dist.is_initialized():
        dist.init_process_group(backend,init_method='env://',rank=rank,world_size=world_size,timeout=timeout)
    elif dist.get_rank()!=rank or dist.get_world_size()!=world_size or dist.get_backend()!=backend:
        raise RuntimeError('Existing process group does not match the torchrun launch')
    # Full checkpoints contain optimizer and per-rank rollout state. Move these
    # to CPU and collect through Gloo rather than serializing them on GPU 0.
    checkpoint_group=dist.group.WORLD if cpu else dist.new_group(backend='gloo',timeout=timeout)
    config['device']=device
    return local_rank,rank,world_size,checkpoint_group


def broadcast_model(model):
    for value in model.state_dict().values():
        dist.broadcast(value,src=0)


def to_cpu(value):
    if torch.is_tensor(value):
        return value.detach().cpu()
    if isinstance(value,dict):
        return {k:to_cpu(v) for k,v in value.items()}
    if isinstance(value,list):
        return [to_cpu(v) for v in value]
    if isinstance(value,tuple):
        return tuple(to_cpu(v) for v in value)
    return value


def gather_checkpoint(state,group):
    collected=[None]*dist.get_world_size() if dist.get_rank()==0 else None
    dist.gather_object(to_cpu(state),collected,dst=0,group=group)
    return dict(enumerate(collected)) if collected is not None else None


def select_checkpoint_state(checkpoint,rank,world_size,weights_only=False):
    if 'model' in checkpoint:
        if world_size!=1 and not weights_only:
            raise ValueError('Single-rank checkpoint requires checkpoint_weights_only=True for multi-GPU training')
        return checkpoint
    ranks=sorted(k for k in checkpoint if isinstance(k,int))
    if not ranks or ranks!=list(range(len(ranks))):
        raise ValueError('Invalid rank-indexed checkpoint')
    if weights_only:
        return checkpoint[0]
    if len(ranks)!=world_size:
        raise ValueError(f'Checkpoint has {len(ranks)} ranks, launch has {world_size}; use checkpoint_weights_only=True')
    return checkpoint[rank]
