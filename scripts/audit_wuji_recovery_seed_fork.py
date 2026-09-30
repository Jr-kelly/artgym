"""Verify a declared optimization-seed fork preserves actual parent weights/Adam."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scripts.audit_wuji_recovery_bc import equal_tree, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parent = load(args.parent)
    path = args.run / f'epoch_{parent["bc_epoch"]:06d}.pth'
    start = load(path)
    fields = ['model', 'bc_optimizer', 'bc_epoch', 'bc_updates']
    assert all(equal_tree(parent[k], start[k]) for k in fields)
    generator = torch.Generator().manual_seed(args.seed)
    assert torch.equal(start['bc_torch_rng'], generator.get_state())
    assert equal_tree(start['bc_numpy_rng'], np.random.RandomState(args.seed).get_state())
    assert not equal_tree(start['bc_torch_rng'], parent['bc_torch_rng'])
    assert not equal_tree(start['bc_cuda_rng'], parent['bc_cuda_rng'])
    cuda_seeds = [int.from_bytes(bytes(x[:8].tolist()), 'little') for x in start['bc_cuda_rng']]
    assert cuda_seeds and all(seed == args.seed for seed in cuda_seeds)
    manifest = start['bc_manifest']
    assert manifest['sampling_seed_reset']['seed'] == args.seed
    first = json.loads((args.run/'training.jsonl').read_text().splitlines()[0])
    assert first['epoch'] == parent['bc_epoch'] + 1 and first['updates'] == parent['bc_updates'] + 8
    result = dict(passed=True, seed=args.seed, preserved_parent_fields=fields,
        cpu_numpy_seed_state_exact=True, cuda_encoded_seeds=cuda_seeds,
        first_epoch=first['epoch'], first_updates=first['updates'],
        parent_sha256=hashlib.sha256(args.parent.read_bytes()).hexdigest(),
        start_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        scope='Actual saved model/Adam fork with a deliberately new optimization sampling stream. Same BC100 and expert pretraining; not an independent random network initialization.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
