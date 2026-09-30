"""Apply the preregistered training-only repair; evaluation files are not read."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--reports', type=Path, nargs=2, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    reports = [json.loads(path.read_text()) for path in a.reports]
    assert {r['task'] for r in reports} == {'wuji_artmanip_reference', 'wuji_artmanip_clock_hold'}
    assert all(r['training_states_sha256'] == sha(a.input) for r in reports)
    bad_sets = [{i for row in r['rows'] for i in row['bad_pool_rows']} for r in reports]
    assert bad_sets[0] == bad_sets[1], 'Task physical disagreement requires diagnosis before repair'
    bad = bad_sets[0]
    original = np.load(a.input, allow_pickle=False)
    assert original.shape == (512, 75)
    repaired = original.copy()
    used = set()
    mapping = []
    for row in sorted(bad):
        source = row // 128
        replacement = next(i for i in range(source * 128, (source + 1) * 128)
                           if i not in bad and i not in used)
        used.add(replacement)
        repaired[row] = original[replacement]
        mapping.append(dict(row=row, source=source, replacement_from_row=replacement))
    assert all(np.array_equal(original[i], repaired[i]) for i in range(512) if i not in bad)
    np.save(a.output, repaired)
    result = dict(input=str(a.input), input_sha256=sha(a.input), output=str(a.output),
        sha256=sha(a.output), mapping=mapping,
        source_distinct_counts=[len(np.unique(repaired[s * 128:(s + 1) * 128], axis=0)) for s in range(4)],
        reports=[dict(path=str(path), sha256=sha(path)) for path in a.reports],
        scope='Training-only duplicated stable rows; source/reset probabilities and512 slots retained. '
        'All evaluation populations unchanged. Original baseline remains on its original pool. '
        'Both new objective-comparison arms must use this identical repaired pool, after static verification.')
    a.output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
