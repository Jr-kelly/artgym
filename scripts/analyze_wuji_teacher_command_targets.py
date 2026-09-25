"""Describe expert absolute joint targets before considering a new action parameterization.

No model is fitted, no policy is evaluated, and no simulation is advanced.
This describes existing teacher demonstrations; it cannot establish a deployable
open-loop trajectory or the superiority of absolute-target imitation.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.wuji_kinematics import WujiKinematics

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    manifest_path = ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    states_path = ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'
    states = np.load(states_path)
    kin = WujiKinematics()
    results = []
    for item, seconds in zip(manifest['sources'][:2], [2, 5]):
        assert item['physics_collection_policy'] == 'teacher'
        pair = ROOT/'runs'/item['path'].split('/runs/', 1)[1]
        assert digest(pair) == item['sha256']
        trace = pair.with_name('trace.npz')
        report = json.loads(pair.with_name('report.json').read_text())
        assert report['recorded_steps'] == 600 and report['num_envs'] == 332
        assert report['protocol']['stage_steps'] == seconds*30
        with np.load(trace) as z:
            targets = z['target'][:, :300].astype(np.float64)
            actions = z['action'][:, :300].astype(np.float64)
            goals = z['goal'][:, :300]
            alive = z['active'][:, :300] & ~z['fall'][:, :300] & ~z['invalid'][:, :300]
        assert targets.shape == actions.shape == (600, 300, 20)
        initial = states[:300, 20:40].astype(np.float64)
        incoming = np.concatenate([initial[None], targets[:-1]], axis=0)
        # Boundaries can clip the command; report that effect rather than
        # wrongly treating every action as an unconstrained integrator.
        emitted_delta = targets[:, :, 16:]-incoming[:, :, 16:]
        unconstrained_delta = .025*actions[:, :, 16:]
        delta_residual = emitted_delta-unconstrained_delta
        reproduced = np.clip(incoming[:, :, 16:]+unconstrained_delta, kin.lower[16:], kin.upper[16:])
        reproduction_error = float(np.abs(reproduced-targets[:, :, 16:]).max())
        assert reproduction_error < 1e-6, reproduction_error
        stages = []
        for start in range(0, 600, seconds*30):
            stop = start+seconds*30
            assert np.all(goals[start:stop] == goals[start:start+1])
            stages.append(dict(phase=(start//(seconds*30)) % 2, goals=goals[start], start=start, stop=stop,
                target=targets[stop-9:stop].mean(0), alive=alive[:stop].all(0)))
        groups = []
        for grasp in range(3):
            rows = np.arange(100*grasp, 100*(grasp+1))
            conditions = []
            for phase in [0, 1]:
                selected = [s for s in stages if s['phase'] == phase]
                values = np.stack([s['target'][rows, 16:]-initial[rows, 16:] for s in selected])
                valid = np.stack([s['alive'][rows] for s in selected])
                complete = valid.all(0)
                cycle_span = np.ptp(values[:, complete], axis=0)
                conditions.append(dict(command_phase=phase, stages=len(selected), complete_rows=int(complete.sum()),
                    actual_goal_range_m=[float(selected[0]['goals'][rows].min()), float(selected[0]['goals'][rows].max())],
                    thumb_target_from_initial_mean_rad=values[:, complete].mean((0, 1)).tolist(),
                    across_states_and_cycles_std_rad=values[:, complete].std((0, 1)).tolist(),
                    same_state_cycle_span_median_rad=np.median(cycle_span, axis=0).tolist(),
                    same_state_cycle_span_q90_rad=np.quantile(cycle_span, .9, axis=0).tolist()))
            groups.append(dict(grasp=grasp, conditions=conditions))
        mask = np.broadcast_to(alive[..., None], delta_residual.shape)
        results.append(dict(seconds=seconds, groups=groups, trace_sha256=digest(trace),
            report_sha256=digest(pair.with_name('report.json')),
            path=str(trace.relative_to(ROOT)),
            command_with_limits_reproduction_max_error_rad=reproduction_error,
            thumb_unconstrained_integration_max_error_rad=float(np.abs(delta_residual[mask]).max()),
            thumb_command_clip_components=int((np.abs(delta_residual[mask]) > 1e-6).sum()),
            alive_transitions=int(alive.sum()),
            thumb_saturated_action_fraction=float((np.abs(actions[:, :, 16:][mask]) >= .999999).mean()),
            clip_fraction_by_thumb_joint=[float((np.abs(delta_residual[...,j][alive]) > 1e-6).mean()) for j in range(4)]))
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rows=results, no_fitting=True, no_new_physics=True, scope=__doc__,
        initial_states_sha256=digest(states_path), source_sha256=digest(Path(__file__)),
        implication='Absolute-target prediction removes the explicit summation of action errors, but can still fail from inaccurate predictions and contact dynamics. Expert target variation is descriptive, not proof of observability or successful imitation.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
