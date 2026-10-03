"""Explicit exploration intervention; deterministic actor means unchanged."""
import argparse, copy, hashlib, json
from pathlib import Path
import isaacgym  # Shared model imports Gym; its loader must precede torch.
import torch


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--logstd',type=float,default=-1.5);a=p.parse_args()
    assert not a.output.exists()
    from scripts.wuji_robust_learning import ResidualActorCritic
    saved=torch.load(a.checkpoint,map_location='cpu');before=copy.deepcopy(saved)
    # Early valid P50/P0 artifacts predate the public_dim metadata field.
    public_dim=saved['model']['actor.0.weight'].shape[1]
    critic_dim=saved['model']['critic.0.weight'].shape[1]
    assert critic_dim==public_dim+27
    model=ResidualActorCritic(public_dim,critic_dim)
    model.load_state_dict(saved['model']);names=[name for name,_ in model.named_parameters()]
    index=names.index('logstd');ids=saved['optimizer']['param_groups'][0]['params'];assert len(ids)==len(names)
    saved['model']['logstd'].fill_(a.logstd)
    # Only this deliberately changed exploration parameter gets fresh moments;
    # all actor means, critic parameters and other optimizer states remain.
    saved['optimizer']['state'].pop(ids[index],None)
    changed=[k for k in saved['model'] if not torch.equal(saved['model'][k],before['model'][k])];assert changed==['logstd']
    assert torch.equal(saved['rng_cpu'],before['rng_cpu'])
    for x,y in zip(saved['rng_cuda'],before['rng_cuda']):assert torch.equal(x,y)
    saved['exploration_intervention']=dict(parent=str(a.checkpoint),parent_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),logstd=a.logstd,changed_model_parameters=changed,optimizer_scope='Fresh logstd moments only; all actor/critic means and other Adam states retained',rng_scope='Original CPU/CUDA/NumPy sampling state retained',new_training_updates=0,scope='Training exploration change only; deterministic policy is exactly the parent. Physical motor gains, increments, effort/limits and observations unchanged.')
    a.output.parent.mkdir(parents=True,exist_ok=True);torch.save(saved,a.output)
    h=hashlib.sha256(a.output.read_bytes()).hexdigest();a.output.with_suffix('.sha256').write_text(h+'\n');a.output.with_suffix('.intervention.json').write_text(json.dumps(dict(**saved['exploration_intervention'],sha256=h),indent=2))
    print(json.dumps(saved['exploration_intervention']))


if __name__=='__main__':main()
