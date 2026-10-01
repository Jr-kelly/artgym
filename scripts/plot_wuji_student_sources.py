"""Per-source frozen development trends from independently rescored episodes."""
import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('research/unified-student-20261001'))
    args = parser.parse_args()
    colors = {'S0': '#2266bb', 'SC-real': '#218c55', 'SC-masked': '#9257b5', 'SA-real': '#c83737'}
    rows = []
    for path in sorted(args.root.glob('*-development-analysis/report.json')):
        for row in json.loads(path.read_text())['rows']:
            match = re.fullmatch(r'(S0|SC-real|SC-masked|SA-real)-(\d+)', row['model'])
            if match and row['protocol'] in ['S2', 'S5']:
                rows.append(dict(row, method=match[1], update=int(match[2])))
    figure, axes = plt.subplots(4, 3, figsize=(13, 11), sharex=True, sharey=True)
    for source in range(4):
        for method, color in colors.items():
            selected = [r for r in rows if r['source'] == source and r['method'] == method]
            for column, protocol in enumerate(['S2', 'S5']):
                points = sorted((r['update'], r['success'] / r['n']) for r in selected if r['protocol'] == protocol)
                if points:
                    axes[source, column].plot(*zip(*points), marker='o', markersize=3, color=color, label=method)
            body = {}
            for row in selected:
                body.setdefault(row['update'], []).append(row['body_stable'] / row['n'])
            points = sorted((update, min(values)) for update, values in body.items() if len(values) == 2)
            if points:
                axes[source, 2].plot(*zip(*points), marker='o', markersize=3, color=color, label=method)
        for column in range(3):
            axis = axes[source, column]
            axis.set_ylim(-.03, 1.03)
            axis.grid(alpha=.2)
            axis.axhline(.95 if column == 2 else .8, color='black', linestyle='--', linewidth=.8)
            if column == 0:
                axis.set_ylabel(f'Source {source}\nEpisode proportion')
            if source == 3:
                axis.set_xlabel('Actual optimizer updates')
    for axis, title in zip(axes[0], ['S2 strict success', 'S5 strict success', 'Minimum S2/S5 body stability']):
        axis.set_title(title)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc='upper center', ncol=4, bbox_to_anchor=(.5, .95))
    figure.suptitle('Frozen development, 32 episodes/source/protocol; all checkpoints retained', y=.99)
    figure.text(.02, .014, 'Dashed lines: absolute thresholds only. The full gate also limits paired losses against the teacher.\nSources 0/1 share one nearby grasp cluster; repeated checkpoint evaluations are correlated.', fontsize=9)
    figure.tight_layout(rect=[0, .05, 1, .93])
    destination = args.root / 'figures'
    destination.mkdir(exist_ok=True)
    figure.savefig(destination / 'source-learning-curves.png', dpi=160)
    figure.savefig(destination / 'source-learning-curves.svg')
    plt.close(figure)


if __name__ == '__main__':
    main()
