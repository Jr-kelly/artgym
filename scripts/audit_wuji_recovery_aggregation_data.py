"""Check the actual mixed-data split and the single difference between BC arms."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def load(path):
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--initials-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    initials = json.loads(args.initials_manifest.read_text())
    manifest = json.loads((args.data / 'manifest.json').read_text())
    for entry in initials['entries']:
        ids = entry['rows']
        assert len(ids) == len(set(ids)) == 32
        assert all(i < 96 for i in ids[:24]) and all(96 <= i < 128 for i in ids[24:])
    rows = []
    for source in range(4):
        for seconds in [2, 5]:
            part = f't{seconds}/source{source}'
            paths = {arm: args.data / arm / part for arm in ['replay', 'aggregate']}
            old = Path(f'runs/unified-policy-20260930/train-data-t{seconds}/source{source}')
            new = args.collection / f'behavior-t{seconds}/source{source}'
            info = json.loads((new / 'interface.json').read_text())
            assert info['mode'] == 'behavior' and info['teacher_replay_max_mu_error'] < 1e-5
            replay_row = next(x for x in manifest['entries'] if x['source'] == source and x['seconds'] == seconds and x['arm'] == 'replay')
            for filename in ['sequences.npz', 'trace.npz']:
                original, addition = load(old / filename), load(new / filename)
                replay, aggregate = [load(paths[arm] / filename) for arm in ['replay', 'aggregate']]
                assert replay.keys() == aggregate.keys()
                for key in replay:
                    r, a, o, n = replay[key], aggregate[key], original[key], addition[key]
                    assert r.shape[:2] == a.shape[:2] == (600, 160)
                    assert np.isfinite(r).all() and np.isfinite(a).all()
                    assert np.array_equal(r[:, :96], o[:, :96]) and np.array_equal(a[:, :96], o[:, :96])
                    assert np.array_equal(r[:, 96:120], o[:, replay_row['replay_rows']])
                    assert np.array_equal(a[:, 96:120], n[:, :24])
                    assert np.array_equal(r[:, 120:], a[:, 120:])
                    assert np.array_equal(a[:, 120:152], o[:, 96:])
                    assert np.array_equal(a[:, 152:], n[:, 24:])
            rows.append(dict(source=source, seconds=seconds, fitting=120, heldout=40,
                both_keep_old_fitting96=True, shared_heldout40=True, changed_fitting24_only=True,
                sequence_sha256={arm: hashlib.sha256((path/'sequences.npz').read_bytes()).hexdigest()
                                 for arm, path in paths.items()}))
    result = dict(passed=True, rows=rows, scope='Exact recorded-array and whole-trajectory split checks; not label quality or capability. Availability is checked independently.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=True, cells=len(rows))))


if __name__ == '__main__':
    main()
