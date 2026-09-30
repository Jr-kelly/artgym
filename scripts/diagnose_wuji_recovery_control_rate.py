"""Compare recorded expert target demands with the reference target-rate limit.

This cannot establish task infeasibility: another target trajectory may succeed.
"""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    precheck = json.loads((root / 'runs/artmanip-recovery-20260930/reference-precheck/report.json').read_text())
    increment = precheck['effective_step']
    dt = precheck['control_dt']
    rows = []
    for seconds in [2, 5]:
        period = seconds * 30
        for source in range(4):
            directory = root / f'runs/unified-policy-20260930/train-data-t{seconds}/source{source}'
            with np.load(directory / 'sequences.npz') as z:
                target = z['target_clipped']
                previous = z['previous_target']
                initial = z['initial_target'][0]
                active = z['active_before'].astype(bool)
            demand = np.abs(target - previous)
            endpoint_active = active[period - 9]
            endpoint = target[period - 9, endpoint_active]
            minimum_seconds = np.max(np.abs(endpoint - initial[endpoint_active]), axis=-1) / (increment / dt)
            row = dict(source=source, seconds=seconds, episodes=target.shape[1],
                first_hold_sample_active_episodes=int(endpoint_active.sum()),
                first_hold_sample_reference_min_seconds_median=float(np.median(minimum_seconds)),
                first_hold_sample_reference_min_seconds_p95=float(np.quantile(minimum_seconds, .95)),
                first_hold_sample_exceeds_available_time=int((minimum_seconds > seconds - .3 + dt).sum()))
            for name, sl in [('all', slice(None)), ('thumb', slice(16, 20)), ('support', slice(0, 16))]:
                d = demand[:, :, sl][active]
                row[name + '_component_rate_violation_fraction'] = float((d > increment + 1e-6).mean())
                row[name + '_step_rate_violation_fraction'] = float((d > increment + 1e-6).any(-1).mean())
                row[name + '_target_increment_p95_rad'] = float(np.quantile(d, .95))
            rows.append(row)
    result = dict(reference_increment_rad=increment, control_dt=dt,
        reference_target_rate_rad_per_sec=increment / dt, rows=rows,
        scope='Existing expert training/heldout recorded trajectories only, no new simulation or policy test. '
        'Local target differences use the actual expert previous target. The first-hold target is a witness '
        'trajectory, not a necessary target for solving the slider task. Exceeding the reference rate only '
        'rules out exact reproduction of that target demand, not alternative successful trajectories. '
        'No control gain or evaluation threshold is changed.')
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
