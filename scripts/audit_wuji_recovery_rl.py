"""CPU checkpoint audit and optional evidence of an actual resumed first update."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def digest(model):
    h = hashlib.sha256()
    for name, value in sorted(model.items()):
        h.update(name.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--resumed-run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    state = torch.load(args.checkpoint, map_location='cpu')
    state = state[0] if 0 in state else state
    assert state['epoch'] == args.epoch
    assert state['frame'] == args.epoch * 81920
    assert state['recovery_optimizer_updates'] == args.epoch * 36
    steps = sorted({int(v['step']) for v in state['optimizer']['state'].values()})
    assert steps == [args.epoch * 36]
    assert all(torch.isfinite(v).all() for v in state['model'].values())
    assert set(state['recovery_rng']) == {'torch', 'cuda', 'numpy', 'python'}
    result = dict(checkpoint=str(args.checkpoint),
                  sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
                  epoch=args.epoch, frame=state['frame'], updates=state['recovery_optimizer_updates'],
                  adam_steps=steps, rng_keys=sorted(state['recovery_rng']),
                  model_digest=digest(state['model']))
    if args.resumed_run:
        startup = json.loads((args.resumed_run / 'startup.json').read_text())
        first = json.loads((args.resumed_run / 'learning.jsonl').read_text().splitlines()[0])
        assert startup['model_sha256'] == result['model_digest']
        assert startup['epoch'] == args.epoch and startup['frame'] == state['frame']
        assert startup['optimizer_updates'] == args.epoch * 36
        assert first['epoch'] == args.epoch + 1
        assert first['optimizer_updates'] == (args.epoch + 1) * 36
        assert first['curriculum_epoch'] == args.epoch + 1
        assert np.isfinite(list(first['metrics'].values())).all()
        result['actual_resume'] = dict(run=str(args.resumed_run), first_epoch=first['epoch'],
                                      first_updates=first['optimizer_updates'],
                                      first_curriculum_epoch=first['curriculum_epoch'])
    result.update(passed=True, scope='CPU checkpoint integrity and optional actual resume counters/model. '
                  'PhysX is not serialized; fresh physical rollout and recurrent reset. No capability claim.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
