"""Run an unchanged training entry point, recording the first numerical failure.

No tensors are repaired, clamped or skipped. Guard Adam gradients/parameters and
Normal parameters in this process only; preserve the failed tensors and state.
This diagnostic adds synchronization overhead and is not a throughput baseline.
"""
import json
import os
from pathlib import Path
import runpy

import isaacgym
import torch


def main():
    output = Path(os.environ['WUJI_FINITE_AUDIT_DIR'])
    rank = int(os.environ.get('RANK', '0'))
    output.mkdir(parents=True, exist_ok=True)
    original_step = torch.optim.Adam.step
    original_sample = torch.distributions.Normal.sample
    steps = [0]

    def fail(stage, bad, payload):
        path = output / ('rank' + str(rank))
        path.mkdir(exist_ok=True)
        record = dict(stage=stage, rank=rank, pid=os.getpid(), optimizer_steps=steps[0],
                      bad=bad, intervention='Stop and archive only; no numerical repair')
        (path / 'first-nonfinite.json').write_text(json.dumps(record, indent=2) + '\n')
        torch.save(payload, path / 'first-nonfinite.pth')
        raise FloatingPointError(json.dumps(record))

    def adam_step(optimizer, *args, **kwargs):
        params = [parameter for group in optimizer.param_groups for parameter in group['params']]
        bad = [index for index, parameter in enumerate(params)
               if parameter.grad is not None and not torch.isfinite(parameter.grad).all()]
        if bad:
            fail('adam_before_step_gradient', bad, dict(optimizer=optimizer.state_dict(),
                 parameters=[parameter.detach().cpu() for parameter in params],
                 gradients=[None if parameter.grad is None else parameter.grad.detach().cpu() for parameter in params]))
        result = original_step(optimizer, *args, **kwargs)
        steps[0] += 1
        bad = [index for index, parameter in enumerate(params) if not torch.isfinite(parameter).all()]
        if bad:
            fail('adam_after_step_parameter', bad, dict(optimizer=optimizer.state_dict(),
                 parameters=[parameter.detach().cpu() for parameter in params]))
        return result

    def normal_sample(distribution, *args, **kwargs):
        bad = {}
        for name in ['loc', 'scale']:
            value = getattr(distribution, name)
            invalid = ~torch.isfinite(value)
            if name == 'scale':
                invalid |= value < 0
            if invalid.any():
                bad[name] = dict(count=int(invalid.sum()), shape=list(value.shape))
        if bad:
            fail('normal_sample', bad, dict(loc=distribution.loc.detach().cpu(), scale=distribution.scale.detach().cpu()))
        return original_sample(distribution, *args, **kwargs)

    torch.optim.Adam.step = adam_step
    torch.distributions.Normal.sample = normal_sample
    try:
        runpy.run_module('isaacgymenvs.train', run_name='__main__')
    finally:
        torch.optim.Adam.step = original_step
        torch.distributions.Normal.sample = original_sample


if __name__ == '__main__':
    main()
