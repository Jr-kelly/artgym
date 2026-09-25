"""Check FIFO wrap, label pairing, past-only sampling and private dropout RNG."""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from isaacgymenvs.utils.distill_replay import LatentReplay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    replay = LatentReplay(17, 3, 2, args.device, 77)
    global_rng = torch.get_rng_state().clone()
    gpu_rng = torch.cuda.get_rng_state(args.device).clone() if str(args.device).startswith('cuda') else None
    samples = 0
    for step in range(40):
        if replay.size:
            x, y = replay.sample(31, step)
            assert torch.equal(y[:, 0], x[:, 0] * 2 + 7)
            assert torch.equal(y[:, 1], -x[:, 0])
            assert x[:, 0].min() >= max(0, step * 5 - 17)
            assert x[:, 0].max() < step * 5
            samples += len(x)
        ids = torch.arange(step * 5, (step + 1) * 5, device=args.device, dtype=torch.float32)
        x = torch.stack([ids, ids + 1, ids + 2], -1)
        y = torch.stack([ids * 2 + 7, -ids], -1)
        replay.append(x, y, step)
        # Verify append stores its own copy, never a mutable simulator view.
        x.fill_(-900)
        y.fill_(-800)
    assert replay.size == 17 and replay.writes == 200 and replay.samples == samples
    with replay.dropout_stream():
        x = torch.ones((64, 16), device=args.device, requires_grad=True)
        a = torch.nn.functional.dropout(x, p=.05, training=True)
        a.square().sum().backward()
        assert x.grad is not None and x.grad.isfinite().all()
    with replay.dropout_stream():
        b = torch.nn.functional.dropout(torch.ones_like(x), p=.05, training=True)
    assert not torch.equal(a, b), 'Private dropout stream did not advance'
    assert torch.equal(global_rng, torch.get_rng_state())
    if gpu_rng is not None:
        assert torch.equal(gpu_rng, torch.cuda.get_rng_state(args.device))
    root = Path(__file__).resolve().parents[1]
    files = ['isaacgymenvs/utils/distill_replay.py', 'scripts/check_wuji_latent_replay.py']
    report = dict(status='passed', device=args.device, samples=samples, report=replay.report(),
                  fifo_wrap_and_label_pairing_exact=True, input_aliasing_absent=True,
                  global_rng_unchanged=True, dropout_gradient_finite=True,
                  source_sha256={p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
