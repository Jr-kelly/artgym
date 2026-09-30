"""Plot the preregistered development failure from its original physical trace."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.record_wuji_recovery import R, D, record
from scripts.wuji_timed_command_metrics import score_timed_trace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze = json.loads((D / 'final-freeze.json').read_text())
    example = freeze['video']['failure_example']
    path = R / example['report']
    assert sha(path) == example['report_sha256']
    report = json.loads(path.read_text())
    assert report['checkpoint_sha256'] == freeze['models'][freeze['overall_candidate']]['sha256']
    assert report['protocol']['kind'] == 'S' and report['protocol']['stage_steps'] == 150
    index = report['initial_state_rows'].index(example['failure_row'])
    with np.load(path.parent / 'trace.npz') as archive:
        trace = {k: archive[k] for k in archive.files}
    score = score_timed_trace(trace, 150, 9, 600)
    assert score['records'] == report['records']
    outcome = score['records'][index]
    assert not outcome['stable_full_all_endpoints']
    assert len(trace['slider']) == 600
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    record('fixed_development_failure_plot_started', evidence=str(path.relative_to(R)),
           checkpoint_sha256=report['checkpoint_sha256'], row=example['failure_row'],
           next='Plot original recorded failure; do not infer that a separate local resimulation reproduces it')
    time = np.arange(600) / 30
    slider = trace['slider'][:, index]
    goal = trace['goal'][:, index]
    error = 1000 * (slider - goal)
    initial = goal[0] - .04
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(time, (slider - initial) * 1000, label='Slider', color='#176bb0')
    axes[0].step(time, (goal - initial) * 1000, where='post', label='Command', color='#333333', linestyle='--')
    axes[0].set_ylabel('Relative slider (mm)')
    axes[0].legend(loc='upper right', ncol=2)
    axes[1].plot(time, error, color='#176bb0')
    axes[1].axhline(2, color='#b83a32', linestyle='--')
    axes[1].axhline(-2, color='#b83a32', linestyle='--', label='Strict error bounds')
    axes[1].set_ylabel('Slider error (mm)')
    axes[1].legend(loc='upper right')
    axes[2].plot(time, trace['drift'][:, index] / .01, label='Translation / 10 mm')
    axes[2].plot(time, trace['rotation'][:, index] / .25, label='Rotation / 0.25 rad')
    axes[2].axhline(1, color='#b83a32', linestyle='--', label='Body limit')
    axes[2].set_ylabel('Fraction of body limit')
    axes[2].set_xlabel('Recorded time (seconds)')
    axes[2].legend(loc='upper right', ncol=3, fontsize=9)
    for stage, held in enumerate(outcome['endpoints_held']):
        for axis in axes:
            axis.axvspan((stage + 1) * 5 - .3, (stage + 1) * 5,
                         color='#56a164' if held else '#d94b42', alpha=.25)
    for axis in axes:
        axis.set_xlim(0, 20)
        axis.grid(alpha=.2)
    fig.suptitle('Original development failure: source 3, fixed row 97, S5\n'
                 'All targets attained; first endpoint hold failed; body stable', fontsize=12)
    fig.text(.1, .022, 'Recorded H200 trace, privileged teacher Eagg6100. Shaded windows: final 0.3 s of each stage.\n'
             'Frozen before final evaluation. This figure is neither a new rollout nor rendered physical motion.', fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .93))
    for extension in ['png', 'pdf']:
        fig.savefig(args.output / ('original-failure.' + extension), dpi=180)
    plt.close(fig)
    with (args.output / 'original-failure.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time_seconds', 'slider_m', 'goal_m', 'error_mm', 'body_drift_m', 'body_rotation_rad'])
        writer.writerows(zip(time, slider, goal, error, trace['drift'][:, index], trace['rotation'][:, index]))
    provenance = dict(report=str(path.relative_to(R)), report_sha256=sha(path),
        trace_sha256=sha(path.parent / 'trace.npz'), checkpoint_sha256=report['checkpoint_sha256'],
        freeze_sha256=sha(D / 'final-freeze.json'), selected_initial_row=example['failure_row'],
        record=outcome, independent_rescore=True,
        scope='Preregistered original development failure; no final selection or new physical evaluation.')
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    record('fixed_development_failure_plot_completed', evidence=str(args.output),
           checkpoint_sha256=report['checkpoint_sha256'], result=outcome,
           next='Retain original failure regardless of separate fixed-video resimulation outcome')
    print(json.dumps(provenance))


if __name__ == '__main__':
    main()
