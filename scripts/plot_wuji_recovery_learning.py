"""Export training diagnostics separately from independently scored development trials."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rl-directories', nargs='*', type=Path, default=[])
    p.add_argument('--bc-fit', type=Path)
    p.add_argument('--reports', nargs='*', type=Path, default=[])
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    receipt = {'scope': 'RL training snapshots, BC held-out recorded-history error, and independent development success are distinct evidence.'}
    if a.rl_directories:
        groups = []
        for d in a.rl_directories:
            rows = [json.loads(x) for x in (d / 'learning.jsonl').read_text().splitlines()]
            assert rows and all(r['updates_this_epoch'] == 36 for r in rows)
            assert all(r['frame_after'] == r['epoch'] * 81920 for r in rows)
            assert all(r['optimizer_updates'] == r['epoch'] * 36 for r in rows)
            assert all(np.isfinite(list(r['metrics'].values())).all() for r in rows)
            groups.append((d.name, rows))
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), constrained_layout=True)
        for name, rows in groups:
            x = [r['frame_after'] / 1e6 for r in rows]
            for s in range(4):
                for ax, key in [(axes[0, 0], 'goal_error'), (axes[0, 1], 'arrival'), (axes[1, 0], 'control_steps')]:
                    # The pilot predates control-step exposure accounting.
                    y = [r['metrics'].get(f'source{s}/{key}', np.nan) for r in rows]
                    ax.plot(x, y, color=f'C{s}', alpha=.8, label=f'source {s}' if name == groups[0][0] else None)
            axes[1, 1].plot(x, [r['reward_weights']['ObjPosDeviation'] for r in rows], label=name)
        for ax, title in zip(axes.flat, ['Last control-step mean goal error (m)', 'Last control-step fraction at goal', 'Control steps by source (reset on resume)', 'Actual position-deviation reward weight']):
            ax.set(title=title, xlabel='Cumulative environment interactions (million)')
            ax.grid(alpha=.2)
        axes[0, 0].legend()
        fig.suptitle('RL training diagnostics: sampled rollout endpoints, not closed-loop success')
        fig.savefig(a.output / 'rl-training.png', dpi=160)
        plt.close(fig)
        receipt['rl'] = [dict(run=name,first_epoch=rs[0]['epoch'],last_epoch=rs[-1]['epoch'],last_interactions=rs[-1]['frame_after'],last_updates=rs[-1]['optimizer_updates'],mean_epoch_seconds=float(np.mean([r['wall_seconds'] for r in rs])),source_visits=rs[-1]['source_visits']) for name, rs in groups]
    if a.bc_fit:
        rows = json.loads(a.bc_fit.read_text())['rows']
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
        for arm in ['M', 'E']:
            selected = [r for r in rows if r['arm'] == arm and r['split'] == 'validation']
            unique = {(r['epoch'], r['source'], r['seconds']): r for r in selected}
            epochs = sorted(set(r['epoch'] for r in unique.values()))
            for ax, metric in zip(axes, ['executed_action_mse', 'target_range_mean']):
                values = [np.mean([r[metric] for r in unique.values() if r['epoch'] == e]) for e in epochs]
                ax.plot([(e - 100) * 8 for e in epochs], values, 'o-', label=arm)
                ax.set(xlabel='Added Adam updates after BC100', ylabel=metric)
                ax.grid(alpha=.2)
                ax.legend()
        fig.suptitle('BC held-out recorded-history fit: not on-policy performance')
        fig.savefig(a.output / 'bc-validation.png', dpi=160)
        plt.close(fig)
        receipt['bc_fit'] = str(a.bc_fit)
    if a.reports:
        rows = [r for path in a.reports for r in json.loads(path.read_text())['rows'] if r['model'] not in ['historical', 'source3', 'static']]
        models = list(dict.fromkeys(r['model'] for r in rows))
        fig, axes = plt.subplots(1, 3, figsize=(max(12, len(models)*1.3), 4), constrained_layout=True)
        for ax, protocol in zip(axes, ['S2', 'S5', 'F']):
            for s in range(4):
                selected = {(r['model'],r['source']):r for r in rows if r['protocol']==protocol}
                y = [selected[(m,s)]['rate'] if (m,s) in selected else np.nan for m in models]
                ax.plot(range(len(models)), y, 'o-', label=f'source {s}')
            ax.set(title=protocol, ylim=(-.03,1.03), ylabel='Independent development success fraction')
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=60, ha='right')
            ax.grid(alpha=.2)
        axes[0].legend()
        fig.suptitle('S: full strict episode. F: at least one cycle; body/survival reported separately.')
        fig.savefig(a.output / 'development-success.png', dpi=160)
        plt.close(fig)
        receipt['development_reports'] = [str(x) for x in a.reports]
    (a.output / 'inputs.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
