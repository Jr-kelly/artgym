"""Recompute arrival-triggered open/close cycles from pre-reset physics samples."""
import numpy as np


def score_arrival_trace(trace, expected_steps, tolerance_m):
    active = trace['active'].astype(bool)
    finite = np.isfinite(trace['slider']) & np.isfinite(trace['goal'])
    valid = active & finite & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
    error = np.abs(trace['slider'] - trace['goal'])
    # The inherited consecutive evaluator suppresses new arrival credit on
    # the horizon-ending step. Reaching the horizon still counts as survival.
    timeout = trace.get('timeout', np.zeros_like(valid)).astype(bool)
    hits = valid & ~timeout & (error < tolerance_m)
    if not np.array_equal(hits, trace['achieved'].astype(bool)):
        raise AssertionError('Runtime arrival flags disagree with physical samples')
    stage = trace['stage'].astype(int)
    if not np.all(stage[0] == 0):
        raise AssertionError('Every trial must start with extension')
    expected_next = np.where(hits[:-1], 1-stage[:-1], stage[:-1])
    comparing = active[1:] & valid[:-1]
    if not np.array_equal(stage[1:][comparing], expected_next[comparing]):
        raise AssertionError('A command switched without the required physical arrival')
    # Never credit anything after the first invalid/fall/inactive sample.
    uninterrupted = np.logical_and.accumulate(valid, axis=0)
    cycle_hits = hits & (stage == 1) & uninterrupted
    pose = (np.isfinite(trace['drift']) & np.isfinite(trace['rotation']) &
            (trace['drift'] < .01) & (trace['rotation'] < .25))
    records = []
    for i in range(active.shape[1]):
        times = np.flatnonzero(cycle_hits[:, i])
        selected = active[:, i]
        records.append(dict(env=i, cycles=int(len(times)),
            cycle_completion_steps=times.tolist(),
            first_cycle=bool(len(times)), three_cycles=bool(len(times) >= 3),
            alive_full=bool(len(active) == expected_steps and valid[:, i].all()),
            strict_body_full=bool(len(active) == expected_steps and
                                  valid[:, i].all() and pose[:, i].all()),
            physical_slider_min_m=float(trace['slider'][selected, i].min()),
            physical_slider_max_m=float(trace['slider'][selected, i].max()),
            max_drift_m=float(trace['drift'][selected, i].max()),
            max_rotation_rad=float(trace['rotation'][selected, i].max())))
    return dict(num_envs=len(records), recorded_steps=len(active),
                cycles_mean=float(np.mean([r['cycles'] for r in records])),
                **{k: sum(r[k] for r in records) for k in
                   ('first_cycle', 'three_cycles', 'alive_full', 'strict_body_full')},
                records=records)
