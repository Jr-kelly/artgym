"""Audit real SAPG checkpoints after a distributed training/resume check."""
import argparse
import hashlib
import json
from pathlib import Path

import torch


def tensor_fingerprint(value):
    digest = hashlib.sha256()

    def visit(item):
        if torch.is_tensor(item):
            item = item.detach().cpu().contiguous()
            if item.is_floating_point():
                assert torch.isfinite(item).all(), 'Non-finite checkpoint tensor'
            digest.update(str((item.dtype, tuple(item.shape))).encode())
            digest.update(item.numpy().tobytes())
        elif isinstance(item, dict):
            for key in sorted(item, key=str):
                digest.update(str(key).encode())
                visit(item[key])
        elif isinstance(item, (tuple, list)):
            for entry in item:
                visit(entry)
        else:
            digest.update(repr(item).encode())

    visit(value)
    return digest.hexdigest()


def audit(path, world_size, epochs, frames, previous=None):
    checkpoint = torch.load(path, map_location='cpu')
    assert sorted(checkpoint) == list(range(world_size)), 'Missing rank state'
    reports = []
    for rank, state in sorted(checkpoint.items()):
        assert state['world_size'] == world_size
        assert state['epoch'] == epochs, (rank, state['epoch'], epochs)
        assert state['frame'] == frames, (rank, state['frame'], frames)
        steps = [int(v['step']) for v in state['optimizer']['state'].values()]
        assert steps and min(steps) > 0, 'No optimizer updates'
        reports.append(dict(
            rank=rank, epoch=state['epoch'], frame=state['frame'],
            num_actors=state['num_actors'], optimizer_steps=max(steps),
            model_sha256=tensor_fingerprint(state['model']),
            optimizer_sha256=tensor_fingerprint(state['optimizer']),
            observation_sha256=tensor_fingerprint(state['obs']),
        ))
    assert len({r['model_sha256'] for r in reports}) == 1, 'Models/normalizers diverged'
    assert len({r['optimizer_sha256'] for r in reports}) == 1, 'Optimizer states diverged'
    assert len({r['observation_sha256'] for r in reports}) == world_size, 'Duplicate rollout data'
    if previous:
        old = torch.load(previous, map_location='cpu')
        for rank, state in checkpoint.items():
            assert state['frame'] > old[rank]['frame']
            assert state['epoch'] > old[rank]['epoch']
            old_steps = max(int(v['step']) for v in old[rank]['optimizer']['state'].values())
            assert reports[rank]['optimizer_steps'] > old_steps, 'Optimizer did not continue'
            assert reports[rank]['model_sha256'] != tensor_fingerprint(old[rank]['model'])
    return dict(checkpoint=str(path), previous=str(previous) if previous else None,
                world_size=world_size, finite=True, synchronized=True,
                independent_observations=True, ranks=reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--world-size', type=int, default=4)
    parser.add_argument('--epochs', type=int, required=True)
    parser.add_argument('--frames', type=int, required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit(args.checkpoint, args.world_size, args.epochs, args.frames, args.previous)
    serialized = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + '\n')
    print(serialized)
