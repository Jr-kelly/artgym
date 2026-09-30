"""Development trajectories, separating full success, phase hold and body stability."""
import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--reports', type=Path, nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    cells = {}
    for path in a.reports:
        report = json.loads(path.read_text())
        assert report['independent_rescore'] == 'passed'
        for row in report['rows']:
            key = (row['model'], row['protocol'], row['source'])
            if key in cells:
                assert cells[key] == row, 'Conflicting duplicate evaluation cells'
            cells[key] = row
    rows = list(cells.values())
    fields = sorted({k for r in rows for k in r})
    with (a.output / 'development-cells.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    patterns = [('BC', r'([ME])(\d+)', 'Additional BC Adam updates after historical BC100', 100),
                ('RL', r'(rl(?:hold|clean)?)(\d+)', 'Total training interactions (million)', None),
                ('Aggregation', r'(Eagg|Ereplay)(\d+)', 'Additional BC Adam updates after shared E5700', 5700)]
    for title, pattern, xlabel, bc_parent in patterns:
        selected = [r for r in rows if re.fullmatch(pattern, r['model'])]
        if not selected:
            continue
        fig, axes = plt.subplots(3, 3, figsize=(13, 10), constrained_layout=True)
        for col, protocol in enumerate(['S2', 'S5', 'F']):
            metrics = ['rate', 'phase_hold_rate' if protocol != 'F' else 'cycles_mean', 'body_rate']
            names = ['Full strict success' if protocol != 'F' else 'At least one full cycle',
                     'Phase endpoint hold' if protocol != 'F' else 'Mean completed cycles',
                     'Body stable over full episode']
            series = sorted({(re.fullmatch(pattern, r['model'])[1], r['source']) for r in selected})
            for family, source in series:
                group = [r for r in selected if r['protocol'] == protocol and r['source'] == source
                         and re.fullmatch(pattern, r['model'])[1] == family]
                group.sort(key=lambda r: int(re.fullmatch(pattern, r['model'])[2]))
                epochs = [int(re.fullmatch(pattern, r['model'])[2]) for r in group]
                xs = [(e - bc_parent) * 8 for e in epochs] if bc_parent is not None else [e * .08192 for e in epochs]
                style = {'M': '--', 'E': '-', 'Eagg': '-', 'Ereplay': '--', 'rl': '-', 'rlhold': '--', 'rlclean': ':'}[family]
                for row_index, metric in enumerate(metrics):
                    ax = axes[row_index, col]
                    ax.plot(xs, [r[metric] for r in group], style, marker='o', markersize=3,
                            color=f'C{source}', label=f'{family}, source {source}')
                    ax.set(title=f'{protocol}: {names[row_index]}', xlabel=xlabel)
                    if metric != 'cycles_mean':
                        ax.set_ylim(-.03, 1.03)
                    ax.grid(alpha=.2)
            axes[0, col].legend(fontsize=7, ncol=2)
        fig.suptitle(f'{title} independent development episodes; no final cohort results\n'
                     'F and S are separate physical episodes. Functional cycles do not imply stable holding.')
        fig.savefig(a.output / f'{title.lower()}-development.png', dpi=150)
        fig.savefig(a.output / f'{title.lower()}-development.pdf')
        plt.close(fig)
    (a.output / 'inputs.json').write_text(json.dumps(dict(reports=[str(p) for p in a.reports],
        unique_cells=len(rows), scope='Independent development only; source0/1 are nearby records, '
        'not independent morphologies. Sample counts and Wilson intervals are in development-cells.csv.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
