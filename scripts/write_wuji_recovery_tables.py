"""Readable per-source tables from already independently rescored evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=['development', 'confirmation', 'final'], required=True)
    args = parser.parse_args()
    cells = {}
    for path in args.reports:
        report = json.loads(path.read_text())
        assert report['independent_rescore'] == 'passed'
        for row in report['rows']:
            key = row['model'], row['protocol'], row['source']
            assert key not in cells or cells[key] == row, 'Conflicting cohorts or cells'
            cells[key] = row
    expected_n = dict(development=32, confirmation=64, final=128)[args.phase]
    assert all(r['n'] == expected_n for r in cells.values())
    def order(name):
        match = re.fullmatch(r'(.*?)(\d+)', name)
        return (match[1], int(match[2])) if match else (name, 0)
    models = sorted({key[0] for key in cells}, key=order)
    lines = [f'# {args.phase}: per-source physical evaluation', '',
             f'Each cell is successes/{expected_n} with a 95% Wilson interval. Sources 0/1 are nearby records; 0/1, 2 and 3 form three base-configuration clusters. These episodes test the fixed simulated knife in trained grasp neighborhoods.', '',
             'All policies are privileged teachers. Each named unified model uses one weight set for all sources. Historical/source3 expert rows are references; their responsible sources are 0–2/3 respectively. No student or hardware result is represented.', '',
             'S2/S5: separate 20-second fixed-clock episodes, every stage’s last nine samples within 2 mm, full survival/validity and body displacement <10 mm/rotation <0.25 rad. F: separate 40-second episodes, 10 mm tolerance with 1.5-second arrival hold before switching; at least one full open-close cycle. F success alone does not imply full-episode body stability.', '']
    for metric, title in [('success', 'Strict S success or functional F cycles'),
                          ('body_stable', 'Body stable over the full declared episode'),
                          ('alive', 'Valid and alive over the full declared episode')]:
        lines += [f'## {title}', '', '| Model | Protocol | Source 0 | Source 1 | Source 2 | Source 3 |',
                  '|---|---|---|---|---|---|']
        for model in models:
            for protocol in ['S2', 'S5', 'F']:
                rows = [cells[model, protocol, source] for source in range(4)]
                values = []
                for row in rows:
                    if metric == 'success':
                        low, high = row['wilson95']
                    else:
                        from scripts.summarize_wuji_unified import wilson
                        low, high = wilson(row[metric], row['n'])
                    values.append(f'{row[metric]}/{row["n"]} [{low:.3f}, {high:.3f}]')
                lines.append('| ' + ' | '.join([model, protocol, *values]) + ' |')
        lines += ['']
    lines += ['## Phase holding and first body breach', '',
              'The four values in each cell follow source order 0/1/2/3. Phase fractions are descriptive repeated stages, not independent episode counts. Breach time is capped at observed duration when no breach occurs.', '',
              '| Model | Protocol | Endpoint hold fraction / F mean cycles | Mean first body breach (s) |',
              '|---|---|---|---|']
    for model in models:
        for protocol in ['S2', 'S5', 'F']:
            rows = [cells[model, protocol, source] for source in range(4)]
            metric = 'cycles_mean' if protocol == 'F' else 'phase_hold_rate'
            lines.append('| ' + ' | '.join([model, protocol,
                ', '.join(f'{r[metric]:.3f}' for r in rows),
                ', '.join(f'{r["body_first_breach_mean_sec"]:.2f}' for r in rows)]) + ' |')
    lines += ['', '## Evidence', '',
              'Per-episode CSVs and cluster summaries accompany each report. Reports also retain open/close arrival, holding, overshoot/retreat, saturation, joint limits, full drift/rotation, early termination and raw trace hashes.', '']
    for path in args.reports:
        lines.append(f'- `{path}` — SHA256 `{hashlib.sha256(path.read_bytes()).hexdigest()}`')
    args.output.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
