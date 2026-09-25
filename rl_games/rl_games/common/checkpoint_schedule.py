"""Periodic recovery snapshots and immutable policy snapshots for evaluation."""
import json
import os
from pathlib import Path

from rl_games.algos_torch import torch_ext
from rl_games.common.distributed_utils import to_cpu


def checkpoint_events(config, epoch, final=False):
    first = int(config.get('checkpoint_first_epoch', 10))
    save = int(config.get('save_frequency', 50))
    evaluate = int(config.get('evaluation_frequency', 100))
    milestone = int(config.get('checkpoint_milestone_frequency', 500))
    eval_due = final or epoch == first or (evaluate > 0 and epoch % evaluate == 0)
    milestone_due = milestone > 0 and epoch % milestone == 0
    save_due = eval_due or milestone_due or (save > 0 and epoch % save == 0)
    return save_due, eval_due, milestone_due


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    try:
        with temporary.open('w') as stream:
            json.dump(payload, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def publish_checkpoint(run_dir, state, config, final=False):
    """Called only by rank 0 after collecting every rank's resumable state."""
    run = Path(run_dir)
    rank0 = state[0]
    epoch = int(rank0['epoch'])
    save_due, eval_due, milestone = checkpoint_events(config, epoch, final)
    if not save_due:
        return
    folder = run / 'checkpoints'
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = folder / f'epoch_{epoch:06d}.pth'
    torch_ext.safe_save(state, snapshot)
    print(f'Saved recovery checkpoint {snapshot}; evaluation_due={eval_due}', flush=True)
    metadata = dict(epoch=epoch, frame=int(rank0['frame']), world_size=len(state),
                    checkpoint=str(snapshot.resolve()), milestone=milestone, final=final)
    atomic_json(snapshot.with_suffix('.json'), metadata)
    temporary = folder / f'.latest.{os.getpid()}'
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(snapshot.name)
    os.replace(temporary, folder / 'latest.pth')
    atomic_json(folder / 'latest.json', metadata)

    if eval_due:
        inbox = run / 'evaluation' / 'inbox'
        inbox.mkdir(parents=True, exist_ok=True)
        policy = inbox / snapshot.name
        # Includes all model buffers/normalizers, but no optimizer/rollout state.
        torch_ext.safe_save({0: dict(model=to_cpu(rank0['model']), epoch=epoch,
                                    frame=int(rank0['frame']))}, policy)
        atomic_json(policy.with_suffix('.json'), dict(metadata, policy_checkpoint=str(policy.resolve())))

    keep = max(1, int(config.get('checkpoint_keep_recent', 6)))
    snapshots = sorted(folder.glob('epoch_*.json'))
    for record in snapshots[:-keep]:
        info = json.loads(record.read_text())
        if not info['milestone'] and not info['final']:
            record.with_suffix('.pth').unlink(missing_ok=True)
            record.unlink()
