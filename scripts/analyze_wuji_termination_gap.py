"""Describe strict-body failures before native termination in frozen traces.

This is a trajectory diagnostic, not a counterfactual rollout or a training
reward measurement. Evaluation deliberately suppresses arrival rewards.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from scripts.wuji_timed_command_metrics import score_timed_trace


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(trace, stage_steps, hold_steps=9, dt=1 / 30):
    valid = trace['active'].astype(bool) & ~trace['fall'].astype(bool) & ~trace['invalid'].astype(bool)
    pose = np.isfinite(trace['drift']) & np.isfinite(trace['rotation'])
    pose &= (trace['drift'] < .01) & (trace['rotation'] < .25)
    total, count = valid.shape
    body_step = valid & pose
    body = body_step.all(axis=0)
    alive = valid.all(axis=0)
    first = np.where(body, total, np.argmax(~body_step, axis=0))
    # Includes the first violating sample. A sample is a post-physics transition.
    since = np.arange(total)[:, None] >= first[None, :]
    allowed_after = since & valid
    outside_after = allowed_after & ~pose
    inside_after = allowed_after & pose
    near = np.isfinite(trace['slider']) & np.isfinite(trace['goal'])
    near &= np.abs(trace['slider'] - trace['goal']) < .002
    recovered = np.zeros(count, dtype=bool)
    endpoint_after = np.zeros(count, dtype=int)
    for end in range(hold_steps, total + 1):
        recovered |= inside_after[end-hold_steps:end].all(axis=0)
    for end in range(stage_steps, total + 1, stage_steps):
        window = slice(end - hold_steps, end)
        # The whole endpoint window must follow the first violation.
        endpoint_after += (allowed_after[window] & near[window]).all(axis=0)
    records = []
    for i in range(count):
        records.append(dict(
            row=i, alive_full=bool(alive[i]), strict_body_full=bool(body[i]),
            first_strict_failure_seconds=None if body[i] else float((first[i] + 1) * dt),
            valid_seconds_since_first_failure=float(allowed_after[:, i].sum() * dt),
            outside_strict_seconds_since_first_failure=float(outside_after[:, i].sum() * dt),
            inside_strict_seconds_after_failure=float(inside_after[:, i].sum() * dt),
            recovered_for_nine_frames=bool(recovered[i]),
            final_nine_frames_recovered=bool(inside_after[-hold_steps:, i].all()),
            held_endpoints_after_first_failure=int(endpoint_after[i]),
            within_2mm_seconds_while_outside_body_limit=float((near[:, i] & outside_after[:, i]).sum() * dt)))
    return records


def aggregate(rows, success):
    failed = [r for r in rows if not r['strict_body_full']]
    failures = len(failed)
    def quantiles(key):
        return np.quantile([r[key] for r in failed], [.1, .5, .9]).tolist() if failed else None
    return dict(count=len(rows), success=sum(success), strict_body=sum(r['strict_body_full'] for r in rows),
                alive=sum(r['alive_full'] for r in rows), strict_body_failures=failures,
                strict_failure_but_native_alive=sum(r['alive_full'] for r in failed),
                recovered_for_nine_frames=sum(r['recovered_for_nine_frames'] for r in failed),
                final_nine_frames_recovered=sum(r['final_nine_frames_recovered'] for r in failed),
                any_held_endpoint_after_failure=sum(r['held_endpoints_after_first_failure'] > 0 for r in failed),
                first_failure_seconds_q10_q50_q90=quantiles('first_strict_failure_seconds'),
                valid_seconds_since_failure_q10_q50_q90=quantiles('valid_seconds_since_first_failure'),
                outside_seconds_since_failure_q10_q50_q90=quantiles('outside_strict_seconds_since_first_failure'),
                valid_seconds_since_failure_total=sum(r['valid_seconds_since_first_failure'] for r in failed),
                outside_seconds_since_failure_total=sum(r['outside_strict_seconds_since_first_failure'] for r in failed),
                within_2mm_while_outside_body_seconds_total=sum(r['within_2mm_seconds_while_outside_body_limit'] for r in failed))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    audit = json.loads(args.audit.read_text())
    assert audit['status'] == 'verified_complete' and audit['completed'] == 44
    conditions = {}
    for name, verified in audit['results'].items():
        folder = args.root / 'runs/wuji-goal/verification' / name
        assert sha(folder / 'trace.npz') == verified['trace_sha256']
        cfg = yaml.safe_load((folder / 'config.yaml').read_text())
        native = cfg['object']['task']
        assert native['pos_devia_threshold'] == .05 and native['rot_devia_threshold'] == 1.57
        with np.load(folder / 'trace.npz') as z:
            trace = {k: z[k] for k in ['active', 'fall', 'invalid', 'drift', 'rotation', 'slider', 'goal']}
        report = json.loads((folder / 'report.json').read_text())
        stage_steps = report['protocol']['stage_steps']
        assert trace['active'].shape == (600, 332)
        rescored = score_timed_trace(trace, stage_steps, 9, 600)
        assert rescored['records'] == report['records']
        records = describe(trace, stage_steps)
        flags = [r['stable_full_all_endpoints'] for r in rescored['records']]
        groups = {label: aggregate(records[start:stop], flags[start:stop])
                  for label, start, stop in [('trained300', 0, 300), ('A', 0, 100), ('B', 100, 200),
                                             ('C', 200, 300), ('fourth32', 300, 332)]}
        assert groups['trained300']['success'] == verified['success']
        assert groups['trained300']['strict_body'] == verified['body']
        conditions[name] = dict(groups=groups, records=records, checkpoint_sha256=verified['checkpoint_sha256'],
                                trace_sha256=verified['trace_sha256'], config_sha256=sha(folder / 'config.yaml'))
    result = dict(status='verified_all44_offline', source_sha256=sha(Path(__file__)),
                  input_audit=str(args.audit), input_audit_sha256=sha(args.audit),
                  thresholds=dict(strict_position_m=.01, strict_rotation_rad=.25,
                                  native_position_m=.05, native_rotation_rad=1.57),
                  conditions=conditions, new_physics_transitions=0,
                  scope='Observed first-seed development trajectories, not independent validation. '
                        'Counts describe the unchanged native rollout. Early termination changes future '
                        'states, exploration and returns and cannot be simulated by truncating these traces. '
                        'Near-goal time is an opportunity, not measured training reward. '
                        'Existing absolute-pose costs remain in training. No new model selected.')
    args.output.mkdir(parents=True)
    (args.output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    with (args.output / 'counts.csv').open('w') as f:
        writer = csv.writer(f)
        fields = ['success', 'strict_body', 'alive', 'strict_failure_but_native_alive',
                  'recovered_for_nine_frames', 'any_held_endpoint_after_failure',
                  'valid_seconds_since_failure_total', 'outside_seconds_since_failure_total',
                  'within_2mm_while_outside_body_seconds_total']
        writer.writerow(['condition', 'group', 'count'] + fields)
        for name, condition in conditions.items():
            for group, row in condition['groups'].items():
                writer.writerow([name, group, row['count']] + [row[k] for k in fields])
    print(json.dumps(dict(status=result['status'], conditions=len(conditions), output=str(args.output))))


if __name__ == '__main__':
    main()
