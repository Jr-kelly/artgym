"""Fixed training-only initial states and matched aggregation/replay datasets."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def initials(output, seed):
    assert not output.exists()
    rng = np.random.RandomState(seed)
    entries, pieces = [], []
    for source in range(4):
        path = R / f'research/unified-policy-20260930/data/train-source{source}.npy'
        states = np.load(path)
        assert len(states) == 128
        ids = np.r_[rng.permutation(96)[:24], 96 + rng.permutation(32)[:8]]
        pieces.append(states[ids])
        entries.append(dict(source=source, original=str(path.relative_to(R)),
                            original_sha256=sha(path), rows=ids.tolist(),
                            fitting_rows=24, heldout_rows=8))
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, np.concatenate(pieces))
    output.with_suffix('.json').write_text(json.dumps(dict(seed=seed, entries=entries,
        sha256=sha(output), scope='Existing BC training split only. First24/source from original fitting96, last8 from heldout32; no development/final states.'), indent=2) + '\n')


def load(path):
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def mix(collection, output, seed):
    assert not output.exists()
    rng = np.random.RandomState(seed)
    keys = ['obs', 'previous_action', 'previous_target', 'initial_target', 'active_before',
            'mu', 'executed_action', 'target_unclipped', 'target_clipped', 'done']
    entries = []
    for source in range(4):
        for seconds in [2, 5]:
            old = R / f'runs/unified-policy-20260930/train-data-t{seconds}/source{source}'
            new = collection / f'behavior-t{seconds}/source{source}'
            original, addition = load(old / 'sequences.npz'), load(new / 'sequences.npz')
            old_trace, new_trace = load(old / 'trace.npz'), load(new / 'trace.npz')
            old_info, new_info = [json.loads((p / 'interface.json').read_text()) for p in [old, new]]
            assert original['obs'].shape[:2] == (600, 128) and addition['obs'].shape[:2] == (600, 32)
            assert old_info['checkpoint_sha256'] == new_info['checkpoint_sha256']
            assert new_info['mode'] == 'behavior' and new_info['teacher_replay_max_mu_error'] < 1e-5
            repeat = rng.permutation(96)[:24]
            for arm in ['aggregate', 'replay']:
                dest = output / arm / f't{seconds}/source{source}'
                dest.mkdir(parents=True)
                def joined(key, first, second):
                    extra = second[key][:, :24] if arm == 'aggregate' else first[key][:, repeat]
                    return np.concatenate([first[key][:, :96], extra, first[key][:, 96:], second[key][:, 24:]], axis=1)
                sequence = {k: joined(k, original, addition) for k in keys}
                trace = {k: joined(k, old_trace, new_trace) for k in ['slider', 'goal']}
                np.savez_compressed(dest / 'sequences.npz', **sequence)
                np.savez_compressed(dest / 'trace.npz', **trace)
                info = dict(old_info, steps=600, num_envs=160, sequence_sha256=sha(dest / 'sequences.npz'),
                            aggregation_arm=arm, scope='120 fitting sequences: old96 plus new24 or repeated old24. Shared heldout40: old32 plus new8.')
                (dest / 'interface.json').write_text(json.dumps(info, indent=2) + '\n')
                report = dict(protocol=json.loads((old / 'report.json').read_text())['protocol'],
                              scope='Mixed recorded histories for BC; not a single-policy rollout result')
                (dest / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                entries.append(dict(arm=arm, source=source, seconds=seconds, path=str(dest),
                    original_sha256=sha(old / 'sequences.npz'), new_sha256=sha(new / 'sequences.npz'),
                    replay_rows=repeat.tolist(), sha256=sha(dest / 'sequences.npz')))
    (output / 'manifest.json').write_text(json.dumps(dict(seed=seed, entries=entries,
        scope='Matched batch120,8updates/epoch, same heldout40. All old fitting96 retained; only20percent of fitting histories differs. Parent recipe used batch96; both new arms use120.'), indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['initials', 'mix'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--collection', type=Path)
    parser.add_argument('--seed', type=int, default=2026093051)
    args = parser.parse_args()
    if args.mode == 'initials':
        initials(args.output, args.seed)
    else:
        assert args.collection
        mix(args.collection, args.output, args.seed)


if __name__ == '__main__':
    main()
