"""Export actual learner/exploration logs, separately from frozen F/S evaluation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator


def write_csv(path, rows):
    fields = sorted({key for row in rows for key in row})
    with path.open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    primary = ['losses/entropy', 'info/kl', 'info/last_lr',
               'losses/a_loss', 'losses/c_loss', 'rewards/step']
    scalars, learning, receipts, groups = [], [], [], []
    for run in args.runs:
        rows = [json.loads(line) for line in (run / 'learning.jsonl').read_text().splitlines()]
        events = EventAccumulator(str(run / 'summaries'), size_guidance={'scalars': 0})
        events.Reload()
        tags = events.Tags()['scalars']
        assert all(tag in tags for tag in primary)
        epochs = {event.step: int(event.value) for event in events.Scalars('info/epochs')}
        selected = sorted(set(primary + [tag for tag in tags if tag.startswith(
            ('intr_rewards/', 'auxiliary_stats/')) or tag == 'episode_lengths/step']))
        series = {}
        for tag in selected:
            values = events.Scalars(tag)
            assert all(math.isfinite(v.value) for v in values), (run, tag)
            series[tag] = values
            for value in values:
                scalars.append(dict(run=str(run), tag=tag, frame=value.step,
                                    epoch=epochs[value.step], wall_time_unix=value.wall_time,
                                    value=value.value))
        lr_at_update = {v.step: v.value for v in series['info/last_lr']}
        for row in rows:
            assert row['updates_this_epoch'] == 36
            assert row['frame_after'] == row['epoch'] * 81920
            assert epochs[row['frame_after']] == row['epoch']
            assert all(math.isfinite(v) for v in row['metrics'].values())
            flat = dict(run=str(run), epoch=row['epoch'], frame=row['frame_after'],
                        optimizer_updates=row['optimizer_updates'],
                        epoch_seconds=row['wall_seconds'],
                        applied_last_update_lr=lr_at_update[row['frame_after']],
                        after_scheduler_lr=row['lr'])
            flat.update({'weight/' + key: value for key, value in row['reward_weights'].items()})
            flat.update({'sampled/' + key: value for key, value in row['metrics'].items()})
            # Base ArtManip extras are already weighted means. The optional
            # holding bonus/penalty are added explicitly by the holding task.
            flat['sampled/base_reward_sum'] = sum(row['metrics'][key] for key in row['reward_weights'])
            flat['sampled/holding_addition'] = sum(row['metrics'].get(key, 0)
                for key in ['holding/reward', 'holding/body_penalty'])
            learning.append(flat)
        receipts.append(dict(run=str(run), first_epoch=rows[0]['epoch'],
                             last_epoch=rows[-1]['epoch'], epochs=len(rows),
                             all_exported_metrics_finite=True,
                             files=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                                    for p in [run / 'learning.jsonl', *sorted((run / 'summaries').glob('*'))]
                                    if p.is_file()]))
        groups.append((run.name, series, rows))
    write_csv(args.output / 'learner-scalars.csv', scalars)
    write_csv(args.output / 'source-reward-curriculum.csv', learning)
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True)
    titles = ['Gaussian policy entropy (global)', 'Policy KL (miniepoch average)',
              'LR applied on last optimizer update', 'Actor loss', 'Critic loss',
              'Training episode reward (objectives differ)']
    for name, series, _ in groups:
        for ax, tag, title in zip(axes.flat, primary, titles):
            values = series[tag]
            ax.plot([v.step / 1e6 for v in values], [v.value for v in values],
                    label=name, linewidth=.7, alpha=.8)
            ax.set(title=title, xlabel='Cumulative environment interactions (million)')
            ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=6)
    fig.suptitle('Actual RL learner logs; not independent F/S success')
    fig.savefig(args.output / 'learner.png', dpi=150)
    fig.savefig(args.output / 'learner.pdf')
    plt.close(fig)
    fig, axes = plt.subplots(len(groups), 2, figsize=(12, max(3, len(groups) * 2.6)),
                             squeeze=False, constrained_layout=True)
    for index, (name, series, rows) in enumerate(groups):
        for tag, values in series.items():
            if tag.startswith('intr_rewards/entropy_block_'):
                axes[index, 0].plot([v.step / 1e6 for v in values], [v.value for v in values],
                                    label=tag.rsplit('_', 1)[-1], linewidth=.7)
        for key in [*rows[-1]['reward_weights'], 'holding/reward', 'holding/body_penalty']:
            if key not in rows[-1]['metrics']:
                continue
            axes[index, 1].plot([r['frame_after'] / 1e6 for r in rows],
                                [r['metrics'][key] for r in rows], label=key, linewidth=.7)
        for ax, title in zip(axes[index], ['Logged SAPG block entropy', 'Last rollout-step weighted reward components']):
            ax.set(title=name + '\n' + title, xlabel='Cumulative interactions (million)')
            ax.grid(alpha=.2)
            ax.legend(fontsize=6, ncol=3)
    fig.suptitle('Exploration and reward diagnostics, not complete-episode success')
    fig.savefig(args.output / 'exploration-rewards.png', dpi=150)
    fig.savefig(args.output / 'exploration-rewards.pdf')
    plt.close(fig)
    result = dict(runs=receipts, scalar_rows=len(scalars), learning_rows=len(learning),
                  scope='TensorBoard actual learner scalars plus last-rollout-step source/reward snapshots. '
                        'Global/SAPG-block entropy is not source-specific. Training objectives and rewards differ; '
                        'do not rank capabilities using these reward curves. F/S evidence remains independent.',
                  lr_scope='TensorBoard info/last_lr is captured on the last optimizer update. learning.jsonl lr '
                           'is self.last_lr after the final adaptive scheduler update; the values can differ.')
    (args.output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(runs=len(receipts), scalar_rows=len(scalars), learning_rows=len(learning))))


if __name__ == '__main__':
    main()
