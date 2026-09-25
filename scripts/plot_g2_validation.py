"""Standalone diagnostic plots from saved raw trajectories; never alter videos."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def load(root, name):
    path = root / name
    return np.load(path / ('trace.npz' if (path / 'trace.npz').exists() else 'partial-trace.npz'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    data = json.loads(args.audit.read_text())
    root = args.audit.parent
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    nominal = load(root, 'B-axis3-post-up5-teacher-v65')
    for trace, label, color, alpha, width in [(nominal, 'Fixed B65', 'black', 1., 2.)] + [
        (load(root, r['name']), 'Placement %02d' % r['placement'], 'tab:red', .45, 1.)
        for r in data['trials'] if r['group'] == 'B' and 'trace_file' in r]:
        mask = trace['time'] < 24.1
        t = trace['time'][mask]
        contacts = trace['finger_knife_contacts'][mask] > 0
        axes[0, 0].plot(t, trace['object'][mask, 2], color=color, alpha=alpha, lw=width, label=label)
        axes[0, 1].plot(t, contacts.sum(1), color=color, alpha=alpha, lw=width)
    for ax in axes[0]:
        ax.axvspan(13, 18, color='tab:orange', alpha=.10)
        ax.set_xlabel('Time from tabletop start (s)')
        ax.grid(alpha=.2)
    axes[0, 0].axhline(.75, color='gray', ls='--', label='Table height')
    axes[0, 0].set_ylabel('Knife body height (m)')
    axes[0, 0].set_title('Acquisition: fixed case vs all finished placements (B)')
    axes[0, 0].legend(fontsize=7, ncol=2)
    axes[0, 1].set_ylabel('Fingers contacting knife')
    axes[0, 1].set_title('Shading: 5 s turn toward end-standing pose')
    for group, name, color in [('B', 'B-axis3-post-up5-teacher-v65', 'tab:blue'),
                               ('C ideal init', 'C-axis3-post-up5-student-ideal-v66', 'tab:green')]:
        trace = load(root, name)
        ix = np.flatnonzero(trace['phase'] == 'operate')
        t = np.arange(len(ix)) / 30
        lower = float(trace['goal'][ix].min())
        axes[1, 0].plot(t, (trace['slider'][ix] - lower) * 1000, label=group, color=color)
        axes[1, 1].plot(t, abs(trace['slider'][ix] - trace['goal'][ix]) * 1000, label=group, color=color)
    axes[1, 0].step(t, (trace['goal'][ix] - lower) * 1000, where='post', color='black', ls='--', label='External command')
    axes[1, 0].set_ylabel('Slider displacement from lower limit (mm)')
    axes[1, 0].set_title('Fixed B/C: frozen learned actions after real acquisition')
    axes[1, 1].axhline(10, color='black', ls='--', label='10 mm')
    axes[1, 1].axhline(2, color='gray', ls=':', label='2 mm diagnostic')
    axes[1, 1].set_ylabel('Absolute endpoint error (mm)')
    axes[1, 1].set_title('Only shaded final 0.3 s windows score endpoints')
    for ax in axes[1]:
        for end in [5, 10, 15, 20]:
            ax.axvspan(end - .3, end, color='tab:orange', alpha=.18)
        ax.set_xlabel('Time since frozen-policy takeover (s)')
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('G2 + Wuji: raw continuous-state diagnostic', fontsize=15)
    fig.savefig(args.output, dpi=170)
    plt.close(fig)
    print(args.output)


if __name__ == '__main__':
    main()
