"""Describe all body-stable >10mm opening misses from original development traces."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scripts.wuji_kinematics import WujiKinematics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    hand = WujiKinematics()
    assert all('thumb' in name for name in hand.names[16:])
    rows, provenance = [], []
    for protocol in ['S2', 'S5']:
        root = Path('runs/unified-student-20261001')
        directories = {'student': root / (args.model + '-development') / (args.model + '-' + protocol),
                       'teacher': root / ('teacher-official-' + protocol)}
        traces, reports = {}, {}
        for role, directory in directories.items():
            with np.load(directory / 'trace.npz') as archive:
                traces[role] = {key: archive[key] for key in archive.files}
            reports[role] = json.loads((directory / 'report.json').read_text())
            provenance.append(dict(role=role, protocol=protocol, directory=str(directory),
                trace_sha256=hashlib.sha256((directory / 'trace.npz').read_bytes()).hexdigest(),
                checkpoint_sha256=reports[role]['unified_student_sha256'] or reports[role]['checkpoint_sha256']))
        assert reports['student']['initial_states_sha256'] == reports['teacher']['initial_states_sha256']
        trace = traces['student']
        assert trace['active'].shape == (600, 128)
        valid = trace['active'] & ~trace['fall'] & ~trace['invalid']
        body = valid.all(0) & (trace['drift'] < .01).all(0) & (trace['rotation'] < .25).all(0)
        error = np.abs(trace['slider'] - trace['goal'])
        period = reports['student']['protocol']['stage_steps']
        opened = [end for stage, end in enumerate(range(period, 601, period)) if stage % 2 == 0]
        peak = np.stack([error[end - 9:end].max(0) for end in opened]).max(0)
        selected = np.flatnonzero(body & (peak > .01))
        for index in selected:
            for role, trace in traces.items():
                for stage, end in enumerate(range(period, 601, period)):
                    start = end - period
                    sl = slice(start, end)
                    target = trace['target'][sl, index, 16:]
                    q = trace['q'][sl, index, 16:]
                    action = trace['action'][sl, index, 16:]
                    near_limit = np.minimum(np.abs(target - hand.lower[16:]), np.abs(target - hand.upper[16:])) < 1e-4
                    error = np.abs(trace['slider'][sl, index] - trace['goal'][sl, index])
                    rows.append(dict(role=role, protocol=protocol, source=int(index // 32), trial=int(index % 32),
                        initial_state_row=int(index), stage=stage, direction='open' if stage % 2 == 0 else 'close',
                        endpoint_peak_mm=float(error[-9:].max() * 1000),
                        slider_range_mm=float(np.ptp(trace['slider'][sl, index]) * 1000),
                        thumb_action_mean=action.mean(0).tolist(),
                        thumb_clipped_action_fraction=(np.abs(action) >= .9999).mean(0).tolist(),
                        thumb_target_at_joint_limit_fraction=near_limit.mean(0).tolist(),
                        thumb_tracking_rms_rad=np.sqrt(np.mean((target - q) ** 2, axis=0)).tolist(),
                        thumb_contact_fraction=float(trace['contact'][sl, index, 0].mean()),
                        thumb_contact_force_mean_N=float(np.linalg.norm(trace['contact_force'][sl, index, 0], axis=1).mean()),
                        max_drift_mm=float(trace['drift'][sl, index].max() * 1000),
                        max_rotation_rad=float(trace['rotation'][sl, index].max())))
    result = dict(model=args.model, selection='All full-body-stable development episodes with any opening last-nine-sample error >10mm; fixed descriptive threshold, no gate change',
        rows=rows, provenance=provenance, thumb_dof_names=hand.names[16:],
        contact_definition='Simulator net pad contact-force threshold, thumb at force_links index0; does not identify slider-specific contact or establish real tactile availability',
        scope='Original paired development trajectories; teacher and student execute separately and their states diverge. No counterfactual teacher label on learner states, new simulation, extra sample, or causal attribution.')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(stage_rows=len(rows), selected_episodes=len({(r['protocol'], r['initial_state_row']) for r in rows}))))


if __name__ == '__main__':
    main()
