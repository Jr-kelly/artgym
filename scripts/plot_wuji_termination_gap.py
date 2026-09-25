"""Plot the fixed, audited failure categories without selecting a checkpoint."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.analysis.read_text())
    assert result['status'] == 'verified_all44_offline'
    args.output.mkdir(exist_ok=False)
    keys = ['frozen-cp25', 'reset1x-cp100', 'reset2x-cp100']
    labels = ['Original teacher', '1x resets: final100', '2x resets: final100']
    categories = ['Strict task success', 'Body stable; endpoint failure',
                  'Native alive; strict body failure', 'Native fall / invalid']
    colors = ['#32845a', '#e8bc43', '#b77ab6', '#8b939f']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, seconds in zip(axes, [2, 5]):
        counts = []
        for key in keys:
            row = result['conditions'][f'reset-range20260923-{key}-wider-{seconds}s-local-v3']['groups']['trained300']
            values = [row['success'], row['strict_body']-row['success'],
                      row['alive']-row['strict_body'], 300-row['alive']]
            assert sum(values) == 300 and min(values) >= 0
            counts.append(values)
        bottom = np.zeros(3)
        for i, (category, color) in enumerate(zip(categories, colors)):
            values = np.array(counts)[:, i]
            bars = ax.bar(np.arange(3), values, bottom=bottom, color=color, label=category, width=.65)
            for j, (bar, value) in enumerate(zip(bars, values)):
                if value >= 7:
                    ax.text(bar.get_x()+bar.get_width()/2, bottom[j]+value/2, str(value),
                            ha='center', va='center', fontsize=9, color='white' if i == 0 else 'black')
            bottom += values
        ax.set(title=f'Wider development resets, {seconds}s commands', ylim=(0, 310),
               ylabel='Trials out of 300', xticks=np.arange(3), xticklabels=labels)
        ax.tick_params(axis='x', labelsize=9)
        ax.set_axisbelow(True)
        ax.yaxis.grid(alpha=.2)
    fig.suptitle('Training can improve native survival without meeting the full strict task', fontsize=13)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(handles, names, loc='lower center', bbox_to_anchor=(.5, .055), ncol=2, fontsize=9)
    fig.text(.5, .012, 'Same 3 trained grasp families; observed development data; fourth grasp: 0/32 in all conditions. '
             'No new training or physics for this analysis.', ha='center', fontsize=8)
    fig.subplots_adjust(top=.85, bottom=.25, wspace=.20)
    for suffix in ['png', 'pdf']:
        fig.savefig(args.output/('failure-categories.'+suffix), dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
