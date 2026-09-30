"""Actual parent/Adam/RNG and common validation checks for the aggregation pair."""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.audit_wuji_recovery_bc import equal_tree, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pair', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parent = load(args.parent)
    initial_epoch, initial_updates = parent['bc_epoch'], parent['bc_updates']
    keys = ['model', 'bc_optimizer', 'bc_torch_rng', 'bc_cuda_rng', 'bc_numpy_rng', 'bc_epoch', 'bc_updates']
    states, reports, initial_metrics = {}, [], []
    for arm in ['replay', 'aggregate']:
        directory = args.pair / arm / 'E'
        start = load(directory / f'epoch_{initial_epoch:06d}.pth')
        assert all(equal_tree(start[key], parent[key]) for key in keys)
        path = directory / f'epoch_{args.epoch:06d}.pth'
        state = load(path)
        states[arm] = state
        first = json.loads((directory / 'training.jsonl').read_text().splitlines()[0])
        assert first['epoch'] == initial_epoch + 1 and first['updates'] == initial_updates + 8
        assert state['bc_epoch'] == args.epoch and state['bc_updates'] == args.epoch * 8
        assert {int(v['step']) for v in state['bc_optimizer']['state'].values()} == {args.epoch * 8}
        assert state['bc_manifest']['args']['batch'] == 120
        assert all(group['lr'] == 1e-5 for group in state['bc_optimizer']['param_groups'])
        fixed = [name for name in parent['model'] if not any('a2c_network.' + part in name for part in
                 ['priv_encoder.', 'a_rnn.', 'a_layer_norm.', 'actor_mlp.', 'mu.'])]
        assert all(equal_tree(state['model'][key], parent['model'][key]) for key in fixed)
        initial_metrics.append(json.loads((directory/'metrics.jsonl').read_text().splitlines()[0])['validation'])
        reports.append(dict(arm=arm, checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            epoch=args.epoch, updates=state['bc_updates'], added_updates=state['bc_updates']-initial_updates,
            actual_parent_model_optimizer_rng_equal=True, fixed_tensors=len(fixed), first_epoch=first['epoch']))
    assert initial_metrics[0] == initial_metrics[1], 'Shared validation at identical start differs'
    for key in ['bc_torch_rng', 'bc_cuda_rng', 'bc_numpy_rng']:
        assert equal_tree(states['replay'][key], states['aggregate'][key])
    result = dict(passed=True, rows=reports, same_end_rng=True, same_initial_validation=True,
        parent_sha256=hashlib.sha256(args.parent.read_bytes()).hexdigest(),
        scope='Actual saved parent and continuation audit. Dataset split checked separately. No closed-loop capability claim.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
