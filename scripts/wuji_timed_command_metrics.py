"""Score externally scheduled manipulation from pre-reset physical samples."""
import numpy as np


def score_timed_trace(trace, stage_steps, hold_steps, expected_steps):
    if expected_steps % (2*stage_steps) or hold_steps > stage_steps:
        raise ValueError('The protocol requires complete open/close command pairs')
    total, num_envs = trace['active'].shape
    records = []
    for env in range(num_envs):
        active = trace['active'][:, env].astype(bool)
        valid = active & ~trace['fall'][:, env].astype(bool) & ~trace['invalid'][:, env].astype(bool)
        reached = (np.abs(trace['slider'][:, env]-trace['goal'][:, env]) < .002) & valid
        stages, endpoint, times = [], [], []
        for start in range(0, expected_steps, stage_steps):
            hits = reached[start:start+stage_steps]
            streak = 0
            arrival = None
            for offset, hit in enumerate(hits):
                streak = streak+1 if hit else 0
                if streak >= hold_steps and arrival is None:
                    arrival = start+offset
            stages.append(arrival is not None)
            endpoint.append(len(hits) == stage_steps and bool(hits[-hold_steps:].all()))
            times.append(arrival)
        first = bool(stages[0] and stages[1])
        first_end = times[1]+1 if first else total
        finite_pose = np.isfinite(trace['drift'][:, env]) & np.isfinite(trace['rotation'][:, env])
        pose_ok = finite_pose & (trace['drift'][:, env] < .01) & (trace['rotation'][:, env] < .25)
        alive_full = total == expected_steps and bool(valid.all())
        records.append(dict(env=env, stages_attained=stages, endpoints_held=endpoint,
            first_cycle=first, first_cycle_strict=first and bool(pose_ok[:first_end].all()),
            all_commands_attained=bool(all(stages)), all_endpoints_held=bool(all(endpoint)),
            stable_full=alive_full and bool(pose_ok.all()) and first,
            stable_full_all_endpoints=alive_full and bool(pose_ok.all()) and bool(all(endpoint)),
            alive_full=alive_full, fall=bool(trace['fall'][:, env][active].any()),
            invalid=bool(trace['invalid'][:, env][active].any()),
            max_drift_m=float(trace['drift'][:, env][active].max()),
            max_rotation_rad=float(trace['rotation'][:, env][active].max())))
    keys = ['first_cycle', 'first_cycle_strict', 'all_commands_attained', 'all_endpoints_held',
            'stable_full', 'stable_full_all_endpoints', 'alive_full']
    return dict(num_envs=num_envs, recorded_steps=total,
                **{key:sum(record[key] for record in records) for key in keys}, records=records)
