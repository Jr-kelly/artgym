"""Export training diagnostics and compare the realized curriculum across matrix arms."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

ROOT = Path(__file__).resolve().parents[1]
TAGS = ['rewards/step', 'episode_lengths/step', 'reset_noise/scale/frame',
        'reward_curriculum/progress/frame']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--matrix', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    curves, rows, evidence = {}, [], []
    for name in args.names:
        files = list((ROOT / 'runs' / name / 'summaries').glob('events*'))
        assert len(files) == 1
        accumulator = EventAccumulator(str(files[0]), size_guidance={'scalars': 0})
        accumulator.Reload()
        curves[name] = {}
        for tag in TAGS:
            values = [(item.step, item.value) for item in accumulator.Scalars(tag)]
            assert len(values) == 1000 and values[-1][0] == 163840000
            curves[name][tag] = values
            rows.extend(dict(run=name, metric=tag, interactions=step, value=value) for step, value in values)
        evidence.append(dict(run=name, tensorboard_sha256=hashlib.sha256(files[0].read_bytes()).hexdigest(),
                             final={tag: curves[name][tag][-1][1] for tag in TAGS}))
    if args.matrix:
        assert set(args.names) == {'mg_' + arm + '_seed2801' for arm in 'ABCD'}
        for tag in TAGS[2:]:
            assert all(curves[name][tag] == curves[args.names[0]][tag] for name in args.names)
    with (args.output / 'training-scalars.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for name, values in curves.items():
        for axis, tag in zip(axes, TAGS[:2]):
            axis.plot([step / 1e6 for step, _ in values[tag]], [value for _, value in values[tag]], label=name)
    for axis, title in zip(axes, ['Training return', 'Training mean episode length (steps)']):
        axis.set_title(title)
        axis.set_xlabel('Environment interactions (millions)')
        axis.grid(alpha=.25)
    axes[0].legend(fontsize=7)
    figure.suptitle('Training diagnostics only; not frozen operation success')
    figure.savefig(args.output / 'training-curves.png', dpi=160)
    figure.savefig(args.output / 'training-curves.pdf')
    report = dict(status='exported', evidence=evidence,
                  matrix_realized_schedule_exactly_equal=True if args.matrix else None,
                  scope='Training returns and episode lengths are fit diagnostics, not strict frozen success. The realized 1000-epoch budget stops reward-curriculum progress at 0.44444445 in each listed run; this does not test asymptotic performance or a completed curriculum. Matrix schedule equality is checked only with --matrix.')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
