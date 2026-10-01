"""Pair independently rescored policy outcomes on identical initial states."""
import argparse
import csv
import json
from pathlib import Path


def read_trials(path, model):
    with path.open() as stream:
        rows = [row for row in csv.DictReader(stream) if row['model'] == model]
    keyed = {(row['protocol'], int(row['source']), int(row['trial'])): row for row in rows}
    assert rows and len(keyed) == len(rows)
    return keyed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--left', type=Path, required=True)
    parser.add_argument('--left-model', required=True)
    parser.add_argument('--right', type=Path, required=True)
    parser.add_argument('--right-model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    left = read_trials(args.left, args.left_model)
    right = read_trials(args.right, args.right_model)
    assert left.keys() == right.keys(), 'Cannot pair different trial lists'
    assert all(left[key]['cohort_sha256'] == right[key]['cohort_sha256'] for key in left)
    groups = sorted({key[:2] for key in left})
    rows = []
    for protocol, source in groups:
        keys = [key for key in left if key[:2] == (protocol, source)]
        for metric in ['success', 'body_stable']:
            outcomes = [(left[key][metric] == 'True', right[key][metric] == 'True') for key in keys]
            counts = dict(both_pass=sum(a and b for a, b in outcomes),
                          left_only=sum(a and not b for a, b in outcomes),
                          right_only=sum(not a and b for a, b in outcomes),
                          both_fail=sum(not a and not b for a, b in outcomes))
            assert sum(counts.values()) == len(keys)
            rows.append(dict(protocol=protocol, source=source, metric=metric, n=len(keys),
                             left_success=counts['both_pass'] + counts['left_only'],
                             right_success=counts['both_pass'] + counts['right_only'], **counts))
    result = dict(left_model=args.left_model, right_model=args.right_model,
                  left_evidence=str(args.left), right_evidence=str(args.right), rows=rows,
                  scope='Same initial-state trials paired, separately for strict/cycle success and body stability. Repeated model evaluations are correlated; this is not another optimization seed or an enlarged sample denominator.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(left=args.left_model, right=args.right_model, paired_cells=len(rows))))


if __name__ == '__main__':
    main()
