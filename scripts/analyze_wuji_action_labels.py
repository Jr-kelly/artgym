"""Decompose measured action-label errors; do not infer success from MSE."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    state = json.loads((args.directory / 'status.json').read_text())
    completed = [x['name'] for x in state['stages'] if x['status'] == 'completed']
    rows = []
    for name in completed:
        if name == 'runtime':
            continue
        folder = args.directory / name
        report = json.loads((folder / 'report.json').read_text())
        check = json.loads((folder / 'label-probe-report.json').read_text())
        assert check['status'] == 'passed' and check['checks']['actual_student_actions'] == 199200
        with np.load(folder / 'trace.npz') as a:
            physics = {k:a[k] for k in ['active', 'fall', 'invalid', 'slider', 'goal', 'drift', 'rotation']}
        assert score_timed_trace(physics, report['protocol']['stage_steps'], 9, 600)['records'] == report['records']
        with np.load(folder / 'action-label-trace.npz') as a:
            trace = {k:a[k] for k in a.files}
        assert trace['student_mu'].shape == (600, 332, 20)
        assert np.array_equal(physics['active'], trace['active'])
        with np.load(folder / 'trace.npz') as a:
            assert np.array_equal(a['action'], trace['student_action'])
        finite = np.isfinite(trace['teacher_mu']).all(-1) & np.isfinite(trace['student_mu']).all(-1)
        assert finite[trace['active']].all()
        midpoint = (float(trace['goal'].max()) + float(trace['goal'].min())) / 2
        for lo, size, grasp in [(0, 100, 'source'), (100, 100, 'row16'), (200, 100, 'row15'), (300, 32, 'fourth')]:
            ids = slice(lo, lo + size)
            alive = np.array([x['alive_full'] for x in report['records'][ids]])
            for population in ['active', 'full_survivors']:
                for command in ['all', 'open', 'close']:
                    mask = trace['active'][:, ids].copy()
                    if population == 'full_survivors':
                        mask &= alive[None, :]
                    if command != 'all':
                        mask &= (trace['goal'][:, ids] > midpoint) == (command == 'open')
                    if not mask.any():
                        continue
                    student, teacher = [trace[k][:, ids][mask].astype(np.float64) for k in ['student_mu', 'teacher_mu']]
                    student_action, teacher_action = [trace[k][:, ids][mask].astype(np.float64) for k in ['student_action', 'teacher_action']]
                    targets = (trace['student_mapped_target'][:, ids][mask] - trace['teacher_mapped_target'][:, ids][mask]).astype(np.float64)
                    raw = (student - teacher) ** 2
                    clamped = (student_action - teacher_action) ** 2
                    total = float(raw.sum())
                    rows.append(dict(candidate=name, grasp=grasp, population=population, command=command,
                        transitions=int(mask.sum()), raw_mse=float(raw.mean()),
                        raw_support_mse=float(raw[:, :16].mean()), raw_thumb_mse=float(raw[:, 16:].mean()),
                        support_share_of_raw_squared_error=float(raw[:, :16].sum() / total) if total else 0.,
                        clamped_mse=float(clamped.mean()), clamped_support_mse=float(clamped[:, :16].mean()),
                        clamped_thumb_mse=float(clamped[:, 16:].mean()),
                        raw_error_share_with_identical_executed_action=float(raw[student_action == teacher_action].sum() / total) if total else 0.,
                        teacher_saturation_fraction=float((np.abs(teacher) >= 1).mean()),
                        student_saturation_fraction=float((np.abs(student) >= 1).mean()),
                        teacher_thumb_saturation_fraction=float((np.abs(teacher[:, 16:]) >= 1).mean()),
                        student_thumb_saturation_fraction=float((np.abs(student[:, 16:]) >= 1).mean()),
                        mapped_support_target_rmse_mrad=float(np.sqrt((targets[:, :16] ** 2).mean()) * 1000),
                        mapped_thumb_target_rmse_mrad=float(np.sqrt((targets[:, 16:] ** 2).mean()) * 1000),
                        per_joint_raw_mse=raw.mean(0).tolist(), per_joint_clamped_mse=clamped.mean(0).tolist(),
                        per_joint_signed_executed_error=(student_action - teacher_action).mean(0).tolist()))
    args.output.write_text(json.dumps(dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        directory=str(args.directory), complete=state['status'] == 'completed', candidates=completed,
        rows=rows, scope='Read-only developer diagnostic of frozen models. Teacher labels have own RNN history. Active-state and survivor-conditioned results separately reported. All scores rescored from original trace; no independent success or causal claim.'), indent=2) + '\n')
    print(json.dumps([x for x in rows if x['population'] == 'active' and x['command'] == 'all' and x['grasp'] != 'fourth']))


if __name__ == '__main__':
    main()
