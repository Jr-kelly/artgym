"""Export frozen final counts as separate S, body and functional comparison figures."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    frozen = json.loads(args.freeze.read_text())
    assert report['independent_rescore'] == 'passed'
    models = list(frozen['models'])
    cells = {(r['model'], r['protocol'], r['source']): r for r in report['rows']}
    assert len(cells) == len(report['rows']) == len(models) * 12
    assert all(r['n'] == 128 for r in cells.values())
    assert not args.output.exists(), 'Keep previously exported figures immutable'
    args.output.mkdir(parents=True)
    specifications = [
        ('strict', [('S2', 'success', 'S2: strict 20-second success'), ('S5', 'success', 'S5: strict 20-second success')]),
        ('body', [('S2', 'body_stable', 'S2: body stable for all 20 seconds'), ('S5', 'body_stable', 'S5: body stable for all 20 seconds')]),
        ('functional', [('F', 'success', 'F: at least one full open-close cycle'), ('F', 'body_stable', 'F: body stable for all 40 seconds')]),
    ]
    records = []
    for filename, panels in specifications:
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 9.6), sharey=True)
        for axis, (protocol, metric, title) in zip(axes, panels):
            values = np.array([[cells[name, protocol, source][metric] / 128 for source in range(4)] for name in models])
            heat = axis.imshow(values, cmap='cividis', vmin=0, vmax=1, aspect='auto')
            axis.set_title(title, fontsize=11)
            axis.set_xticks(range(4), ['Source 0', 'Source 1', 'Source 2', 'Source 3'])
            axis.set_yticks(range(len(models)), models, fontsize=9)
            axis.set_xticks(np.arange(-.5, 4, 1), minor=True)
            axis.set_yticks(np.arange(-.5, len(models), 1), minor=True)
            axis.grid(which='minor', color='white', linewidth=.4)
            axis.tick_params(which='minor', bottom=False, left=False)
            for i, name in enumerate(models):
                for source in range(4):
                    count = cells[name, protocol, source][metric]
                    axis.text(source, i, f'{count}/128', ha='center', va='center', fontsize=8,
                              color='white' if values[i, source] < .45 else 'black')
                    records.append(dict(figure=filename, model=name, protocol=protocol, metric=metric,
                                        source=source, count=count, n=128, rate=count / 128))
        fig.subplots_adjust(left=.18, right=.9, top=.91, bottom=.11, wspace=.08)
        bar = fig.add_axes([.92, .2, .018, .62])
        fig.colorbar(heat, cax=bar, label='Observed fraction')
        fig.suptitle('Frozen final comparison: one policy per named model', fontsize=13)
        fig.text(.18, .066, 'Fixed simulated knife, trained grasp neighborhoods, privileged teachers. Sources 0/1 are nearby records.', fontsize=8)
        fig.text(.18, .046, 'Historical/source3 are expert references. Counts alone do not establish the full relative-expert S gate.', fontsize=8)
        fig.text(.18, .026, 'S2, S5 and F are separate physical episodes. Wilson intervals and exact gates are reported in the final tables.', fontsize=8)
        for extension in ['png', 'pdf']:
            fig.savefig(args.output / (filename + '.' + extension), dpi=200)
        plt.close(fig)
    with (args.output / 'counts.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (args.output / 'provenance.json').write_text(json.dumps(dict(
        report_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
        freeze_sha256=hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        models=models, scope='Counts only; no new scoring, checkpoint selection or physical evaluation.'), indent=2) + '\n')


if __name__ == '__main__':
    main()
