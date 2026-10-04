"""Paired independent series-device recordings, with attribution gaps visible."""
import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    base = Path('runs/wrap-force-20261004/measurement')
    cases = [('Index under-wrap', 'index-wrap-pressure080-series-v8'),
             ('Original source2', 'source2-pressure080-series-v8')]
    fig, axes = plt.subplots(4, 2, figsize=(15, 12), sharex=True)
    rows, provenance = [], []
    for column, (label, prefix) in enumerate(cases):
        for repeat, suffix in enumerate(['', '-repeat-v26r3']):
            trial = base / (prefix + suffix)
            z = np.load(trial/'diagnostic-axial-aligned.npz')
            time = z['time_s']; mask = (time >= 16) & (time <= 36)
            valid = z['valid']; color = ['#28639f', '#cb6427'][repeat]
            name = 'Recording %d' % (repeat + 1)
            axes[0, column].plot(time[mask], np.where(valid,
                z['diagnostic_axial_signed_N'], np.nan)[mask],
                color=color, lw=.65, alpha=.8, label=name)
            axes[1, column].plot(time[mask], z['pressure_normal_N'][mask],
                color=color, lw=.65, label=name)
            axes[2, column].plot(time[mask], z['rail_guide_position_m'][mask]*1000,
                color=color, lw=.8, label=name)
            axes[3, column].plot(time[mask], valid[mask].astype(float) + .03*repeat,
                color=color, lw=.7, label=name)
            analysis = json.loads((trial/'diagnostic-axial-analysis.json').read_text())
            onsets = json.loads((trial/'diagnostic-motion-onsets.json').read_text())
            evaluation = json.loads((trial/'functional-evaluation.json').read_text())
            for row in analysis['rows']:
                direction = 1 if row['phase'].startswith('extend') else -1
                value = row['sustained_moving_directional_median_N']
                rows.append(dict(grip=label, recording=repeat+1, phase=row['phase'],
                    part=row['part'], valid_fraction=row['valid_fraction'],
                    loaded_moving_samples=row['loaded_moving_samples'],
                    signed_moving_median_N=None if value is None else direction*value,
                    normal_pressure_mean_N=row['pressure_normal_mean_N'],
                    position_minmax_mm=row['rail_guide_position_minmax_mm'],
                    velocity_minmax_mm_s=row['velocity_minmax_mm_s']))
            provenance.append(dict(trial=str(trial),
                aligned_sha256=hashlib.sha256((trial/'diagnostic-axial-aligned.npz').read_bytes()).hexdigest(),
                functional_evaluation=evaluation, observed_onsets=onsets))
        axes[0, column].set_title(label)
        axes[0, column].axhline(0, color='black', lw=.5)
        axes[3, column].set_ylim(-.1, 1.15)
        axes[3, column].set_xlabel('Simulation clock (s)')
        for ax in axes[:, column]:
            ax.set_xlim(16, 36); ax.grid(alpha=.2); ax.legend(fontsize=8)
            for clock in [21, 26, 31]: ax.axvline(clock, color='gray', lw=.5)
    for ax, text in zip(axes[:, 0], ['Valid signed B (N)', 'A: normal pressure (N)',
                                    'Position above stop (mm)', 'Attribution valid (0 / 1)']):
        ax.set_ylabel(text)
    fig.suptitle('Two independent matched recordings per grip: modified calibrated series device\n'
                 'Invalid B is absent, not zero. Neither original-scene force, hardware force, '
                 'maximum capacity nor reliable full task is established.', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, .95])
    for suffix in ['png', 'pdf', 'svg']:
        fig.savefig(a.output/('paired-series-repeat.'+suffix), dpi=160)
    plt.close(fig)
    with (a.output/'force-window-results.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    result = dict(scope=__doc__, original_direct_B_completed=False, hardware_force_completed=False,
        calibration_residual_scope='Known-load moving fixture residual, not total operating force uncertainty',
        startup_scope='Two observed pre-onset transients retained; not a repeatable breakaway capacity',
        rows=rows, provenance=provenance)
    (a.output/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(a.output)


if __name__ == '__main__': main()
