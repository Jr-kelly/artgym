"""Animate a deterministically selected original development failure; never rerun physics."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.package_wuji_student_video import verify_video
from scripts.record_wuji_student_goal import D, R, record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze = json.loads((D / 'final-freeze.json').read_text())
    primary = next(m for m in freeze['models'] if m['role'] == 'primary')
    model = primary['name']
    plan = json.loads((D / 'video-plan.json').read_text())
    assert plan['failure_trace_rule'] == 'first_failed_development_episode_sorted_S2_S5_source_trial'
    with (D / (model + '-development-analysis') / 'trials.csv').open() as stream:
        trials = [r for r in csv.DictReader(stream) if r['model'] == model and r['protocol'] in ['S2', 'S5'] and r['success'] == 'False']
    assert trials, 'No development S failure for this model; do not invent a failure example'
    chosen = min(trials, key=lambda r: (['S2', 'S5'].index(r['protocol']), int(r['source']), int(r['trial'])))
    directory = R / 'runs/unified-student-20261001' / (model + '-development') / (model + '-' + chosen['protocol'])
    report = json.loads((directory / 'report.json').read_text())
    assert report['unified_student_sha256'] == primary['sha256']
    assert report['initial_states_sha256'] == chosen['cohort_sha256']
    with np.load(directory / 'trace.npz') as archive:
        trace = {key: archive[key] for key in archive.files}
    assert trace['active'].shape == (600, 128)
    index = int(chosen['source']) * 32 + int(chosen['trial'])
    assert not report['records'][index]['stable_full_all_endpoints']
    assert not args.output.exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    receipt = dict(model=model, checkpoint_sha256=primary['sha256'], protocol=chosen['protocol'],
        source=int(chosen['source']), trial=int(chosen['trial']), initial_state_row=index,
        cohort_sha256=chosen['cohort_sha256'], trace_sha256=hashlib.sha256((directory / 'trace.npz').read_bytes()).hexdigest(),
        selection_rule=plan['failure_trace_rule'], independent_trial=chosen,
        scope='Animated original H200 development trajectory, with no physics rerun and no new statistical sample. Not a camera rendering or hardware experiment.')
    record('frozen_primary_failure_trace_selected', **receipt,
           next='Animate the selected existing trajectory and decode every frame; do not replace the episode')
    time = np.arange(600) / 30
    active = trace['active'][:, index].astype(bool)
    base = trace['goal'][0, index] - .04
    slider = np.where(active, (trace['slider'][:, index] - base) * 1000, np.nan)
    goal = (trace['goal'][:, index] - base) * 1000
    error = np.where(active, np.abs(trace['slider'][:, index] - trace['goal'][:, index]) * 1000, np.nan)
    drift = np.where(active, trace['drift'][:, index] * 1000, np.nan)
    rotation = np.where(active, trace['rotation'][:, index], np.nan)
    fig, axes = plt.subplots(4, 1, figsize=(10, 8), dpi=120, sharex=True)
    fig.subplots_adjust(top=.86, bottom=.16, hspace=.30)
    body_label = 'PASS' if chosen['body_stable'] == 'True' else 'FAIL'
    fig.suptitle(f'{model} | {chosen["protocol"]} | source {chosen["source"]}, trial {chosen["trial"]} | STRICT FAIL, BODY {body_label}\n'
                 f'Original H200 development trace | checkpoint {primary["sha256"][:12]}', fontsize=13)
    axes[0].step(time, goal, where='post', color='black', linestyle='--', label='External command')
    axes[0].fill_between(time, goal - 2, goal + 2, color='gray', alpha=.15, step='post')
    signals = [slider, error, drift, rotation]
    labels = ['Slider (mm)', 'Absolute error (mm)', 'Body drift (mm)', 'Body rotation (rad)']
    limits = [None, 2, 10, .25]
    lines, cursors = [], []
    period = report['protocol']['stage_steps']
    for ax, values, label, limit in zip(axes, signals, labels, limits):
        finite = values[np.isfinite(values)]
        low = min(float(finite.min()), 0)
        high = max(float(finite.max()), limit or 40)
        margin = max((high - low) * .12, .01)
        ax.set_ylim(low - margin, high + margin)
        ax.set_ylabel(label, fontsize=9)
        ax.grid(alpha=.2)
        ax.plot(time, values, color='lightgray', linewidth=1)
        line, = ax.plot([], [], color='#2266bb', linewidth=1.6)
        lines.append(line)
        cursors.append(ax.axvline(0, color='black', linewidth=.8))
        if limit is not None:
            ax.axhline(limit, color='#bb2222', linestyle='--', linewidth=1)
    for end in range(period, 601, period):
        axes[1].axvspan((end - 9) / 30, end / 30, color='orange', alpha=.15)
    axes[0].legend(loc='upper right', fontsize=8)
    axes[-1].set_xlim(0, 20)
    axes[-1].set_xlabel('Recorded physical time (seconds)')
    status = fig.text(.12, .035, '', fontsize=10)
    with imageio.get_writer(args.output, fps=30, codec='libx264', quality=8, macro_block_size=1,
                            ffmpeg_params=['-pix_fmt', 'yuv420p', '-movflags', '+faststart']) as writer:
        for frame in range(600):
            for line, cursor, values in zip(lines, cursors, signals):
                line.set_data(time[:frame + 1], values[:frame + 1])
                cursor.set_xdata([time[frame], time[frame]])
            status.set_text(f't = {time[frame]:.2f} s | error = {error[frame]:.3f} mm | active = {bool(active[frame])}\n'
                            'Orange windows: final nine samples must remain below 2 mm. No new simulation or hardware result.')
            fig.canvas.draw()
            writer.append_data(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    plt.close(fig)
    receipt['video_verification'] = verify_video(args.output)
    args.output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n')
    record('frozen_primary_failure_trace_video_verified', evidence=str(args.output.with_suffix('.json')),
           video_sha256=receipt['video_verification']['sha256'],
           next='Include this original failure evidence alongside the fixed four-source rendered comparison')
    print(json.dumps(receipt['video_verification']))


if __name__ == '__main__':
    main()
