"""Separate per-source changing-rollout loss from fixed-history target error."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    root = Path('research/unified-student-20261001')
    with (root / 'fit-versus-closedloop.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    figure, axes = plt.subplots(4, 2, figsize=(11, 10), sharex=True, sharey='col')
    for source in range(4):
        for method, color in [('SC-real', '#218c55'), ('SA-real', '#c83737')]:
            selected = [r for r in rows if r['model'].startswith(method + '-') and int(r['source']) == source]
            own = sorted((int(r['optimizer_step']), float(r['own_rollout_latent_mse_tail100']))
                         for r in selected if r['teacher_history_protocol'] == 'S2' and r['own_rollout_latent_mse_tail100'])
            if own:
                axes[source, 0].plot(*zip(*own), marker='o', markersize=3, color=color, label=method)
            for protocol, style in [('S2', '-'), ('S5', '--')]:
                points = sorted((int(r['optimizer_step']), float(r['holdout_target_mse_rad2']))
                                for r in selected if r['teacher_history_protocol'] == protocol)
                if points:
                    axes[source, 1].plot(*zip(*points), marker='o', markersize=3,
                                        color=color, linestyle=style, label=method + ' ' + protocol)
        for axis in axes[source]:
            axis.set_yscale('log')
            axis.grid(alpha=.2)
        axes[source, 0].set_ylabel('Source ' + str(source) + '\nLatent MSE')
        axes[source, 1].set_ylabel('Target MSE (rad²)')
    axes[0, 0].set_title('Own-rollout loss, last 100 updates\nChanging states; not a fixed holdout')
    axes[0, 1].set_title('Frozen teacher-history executed-target error\nSolid: S2; dashed: S5')
    axes[0, 0].legend(fontsize=8)
    axes[0, 1].legend(fontsize=8)
    for axis in axes[-1]:
        axis.set_xlabel('Actual optimizer updates')
    figure.suptitle('Wuji student: per-source fitting evidence, separate from closed-loop gates')
    figure.text(.02, .015, 'Only existing matched methods are shown. Frozen history samples were never optimized.\n'
                'Times and checkpoints are correlated; these curves do not enlarge episode denominators.', fontsize=9)
    figure.tight_layout(rect=[0, .05, 1, .96])
    destination = root / 'figures'
    destination.mkdir(exist_ok=True)
    for suffix in ['png', 'svg']:
        figure.savefig(destination / ('source-fitting-curves.' + suffix), dpi=160)
    plt.close(figure)


if __name__ == '__main__':
    main()
