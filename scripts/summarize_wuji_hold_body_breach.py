"""Describe first body-threshold failures using existing integration traces only."""
import argparse
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    run = json.loads(args.results.read_text())
    assert run['status'] == 'completed'
    rows = []
    count = run['plan']['trials_per_source']
    for item in run['results']:
        if item['protocol'] not in ['static', 'fixed5']:
            continue
        with np.load(ROOT/item['evidence']/'trace.npz') as archive:
            trace = {key: archive[key] for key in archive.files}
        for i, source in enumerate(run['plan']['sources']):
            part = slice(i*count, (i+1)*count)
            drift, rotation = trace['drift'][:, part], trace['rotation'][:, part]
            invalid = ~trace['active'][:, part] | trace['fall'][:, part] | trace['invalid'][:, part]
            def stats(mask):
                values = np.where(mask.any(0), mask.argmax(0)/30, np.nan)
                values = values[np.isfinite(values)]
                return dict(count=len(values), median_s=float(np.median(values)) if len(values) else None,
                            min_s=float(values.min()) if len(values) else None)
            rows.append(dict(model=item['model'], source=source,
                body_breach=stats((drift >= .01) | (rotation >= .25) | invalid),
                drift_breach=stats(drift >= .01), rotation_breach=stats(rotation >= .25),
                invalid_or_fall=stats(invalid)))
    args.output.write_text(json.dumps(dict(rows=rows, scope='Post-hoc descriptive timing of first strict body threshold breach on existing frozen static/fixed5 traces; no new simulation or causal root-cause claim.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
