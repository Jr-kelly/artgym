"""Endpoint margins from original physical traces; no instrumented-label attribution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path('runs/unified-student-20261001')
    research = Path('research/unified-student-20261001')
    rows, provenance = [], []
    for model in args.models:
        with (research / (model + '-development-analysis') / 'trials.csv').open() as stream:
            trials = [r for r in csv.DictReader(stream) if r['model'] == model]
        for protocol in ['S2', 'S5']:
            directory = root / (model + '-development') / (model + '-' + protocol)
            report = json.loads((directory / 'report.json').read_text())
            with np.load(directory / 'trace.npz') as archive:
                trace = {k: archive[k] for k in archive.files}
            assert trace['active'].shape == (600, 128)
            valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
            body = valid.all(0) & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
            errors = np.abs(trace['slider'] - trace['goal'])
            period = report['protocol']['stage_steps']
            provenance.append(dict(model=model, protocol=protocol, directory=str(directory),
                checkpoint_sha256=report['unified_student_sha256'],
                cohort_sha256=report['initial_states_sha256'],
                trace_sha256=hashlib.sha256((directory / 'trace.npz').read_bytes()).hexdigest()))
            for source in range(4):
                ids = slice(source * 32, (source + 1) * 32)
                selected = [r for r in trials if r['source'] == str(source) and r['protocol'] == protocol]
                assert len(selected) == 32
                for stage, end in enumerate(range(period, 601, period)):
                    peak = errors[end - 9:end, ids].max(0)
                    alive = valid[end - 9:end, ids].all(0)
                    held = alive & (peak < .002)
                    assert int(held.sum()) == sum(r['endpoint_holds'][stage] == '1' for r in selected)
                    stable_miss = body[ids] & ~held
                    def quantiles(mask):
                        return (1000 * np.quantile(peak[mask], [0, .25, .5, .75, 1])).tolist() if mask.any() else None
                    rows.append(dict(model=model, protocol=protocol, source=source, stage=stage,
                        direction='open' if stage % 2 == 0 else 'close', n=32,
                        held=int(held.sum()), valid_last9=int(alive.sum()),
                        full_body_stable=int(body[ids].sum()),
                        full_body_stable_but_hold_failed=int(stable_miss.sum()),
                        stable_failed_peak_mm_quantiles=quantiles(stable_miss),
                        valid_peak_mm_quantiles=quantiles(alive),
                        stable_failed_below3mm=int((stable_miss & (peak < .003)).sum()),
                        stable_failed_below5mm=int((stable_miss & (peak < .005)).sum())))
    result = dict(rows=rows, provenance=provenance,
        scope='Original already-scored development traces; every stage count checked against independent trial CSV. '
              'No new episodes, diagnostic rerun or teacher-label attribution. Stages are correlated. '
              'The strict threshold remains2mm;3/5mm counts only describe failure margins.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(stage_source_cells=len(rows), original_traces=len(provenance))))


if __name__ == '__main__':
    main()
