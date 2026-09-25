"""Predeclare ten paired placements (20 B/C trials) only after fixed A/B/C pass.

The manifest is never updated in place. Runs copy a verified frozen source pin,
preserve every failure, and use a separate resumable status/result file.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/g2-tabletop-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alive(process):
    stat = Path('/proc', str(process['pid']), 'stat')
    return stat.exists() and stat.read_text().split(') ')[1][0] != 'Z'


def declare(args):
    assert not args.manifest.exists(), 'Do not overwrite a preregistration'
    names = dict(A=args.a, B=args.b, C=args.c)
    assert all(names.values())
    reports = {g: json.loads((RUN / n / 'report.json').read_text()) for g, n in names.items()}
    assert all(r['group'] == g and r['whole_stable_success'] and r['operation_steps'] == 600
               for g, r in reports.items()), 'Fixed A/B/C must pass before small variations'
    processes = {g: json.loads((RUN / (n + '-process.json')).read_text()) for g, n in names.items()}
    sources = {g: json.loads((Path(p['pin']) / 'SOURCE_SHA256.json').read_text()) for g, p in processes.items()}
    for name in ['scripts/run_g2_tabletop.py', 'scripts/g2_frozen_policy.py',
                 'scripts/g2_kinematics.py', 'scripts/g2_table_collision.py']:
        assert sources['B'][name] == sources['C'][name], ('B/C runtime differs', name)
    ignored = {'group', 'output', 'teacher', 'student'}
    path_args = {'grasp_plan', 'table_regrasp_plan', 'operation_pose', 'post_acquisition_pose'}
    for key, b in reports['B']['args'].items():
        if key in ignored:
            continue
        c = reports['C']['args'][key]
        if key in path_args and b:
            assert sha(Path(b)) == sha(Path(c)), key
        else:
            assert b == c, (key, b, c)
    assert reports['B']['teacher_sha256'] == reports['C']['teacher_sha256']
    wrists = {g: json.loads((RUN / n / 'takeover.json').read_text())['wrist_world'] for g, n in names.items()}
    for group in ['B', 'C']:
        position_error = math.sqrt(sum((a - b) ** 2 for a, b in zip(wrists['A'][:3], wrists[group][:3])))
        qa, qb = wrists['A'][3:], wrists[group][3:]
        dot = abs(sum(a * b for a, b in zip(qa, qb))) / math.sqrt(sum(a * a for a in qa) * sum(b * b for b in qb))
        angle_error = 2 * math.acos(min(1., dot))
        assert position_error < .001 and angle_error < .005, 'A must verify the same final operation wrist pose'
    rng = random.Random(args.seed)
    # Latin hypercube within ±5 mm in x/y, ±2 degrees yaw, ten shared placements.
    columns = []
    for bound in [.005, .005, 2.]:
        column = [(2 * (i + rng.random()) / 10 - 1) * bound for i in range(10)]
        rng.shuffle(column)
        columns.append(column)
    files = {}
    for group in ['B', 'C']:
        for key in path_args | {'teacher', 'student'}:
            path = reports[group]['args'].get(key)
            if path:
                files[path] = sha(Path(path))
    trials = []
    for i, (dx, dy, yaw) in enumerate(zip(*columns)):
        for group in ['B', 'C']:
            trials.append(dict(name=args.manifest.stem + '-%02d-' % i + group,
                placement=i, group=group, delta_x_m=dx, delta_y_m=dy, delta_yaw_deg=yaw))
    manifest = dict(created=datetime.now(timezone.utc).isoformat(), seed=args.seed,
        fixed_cases=names, source_pin=processes['C']['pin'], source_manifest_sha256=sha(Path(processes['C']['pin']) / 'SOURCE_SHA256.json'),
        commands={g: p['command'] for g, p in processes.items() if g in ['B', 'C']},
        base_arguments={g: reports[g]['args'] for g in ['B', 'C']}, input_sha256=files,
        trials=trials, condition='Normal %sm tabletop; same frozen acquisition, control and policies; C ideal initialization' % reports['B']['args']['table_height'],
        metrics='10mm endpoint criterion, full stability and drop separate; 2mm diagnostic; fixed takeover drift reference',
        interpretation='20 predeclared task attempts: ten placements, paired teacher/student. Keep all planning and physical failures. No tuning on these cases.')
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(manifest=str(args.manifest),sha256=sha(args.manifest),trials=len(trials))))


def status(manifest):
    rows = []
    for trial in manifest['trials']:
        path = RUN / trial['name']
        proc = RUN / (trial['name'] + '-process.json')
        row = dict(trial)
        if proc.exists() and alive(json.loads(proc.read_text())):
            row['status'] = 'running'
        elif (path / 'report.json').exists():
            report = json.loads((path / 'report.json').read_text())
            row.update(status='completed', grasp_success=report['grasp_success'],
                whole_success=report['whole_success'], whole_stable_success=report.get('whole_stable_success', False),
                failure_class=report.get('failure_class'), slider_travel_m=report.get('slider_travel_m'),
                endpoints=report.get('endpoints'), world_drift_max_m=report.get('world_drift_max_m'),
                world_rotation_max_rad=report.get('world_rotation_max_rad'), physical_drop=report.get('physical_drop_detected'))
        elif proc.exists() or (RUN / 'source-pins' / trial['name']).exists():
            failure = path / 'failure.json'
            details = json.loads(failure.read_text()) if failure.exists() else dict(message='Inspect retained launcher/initialization log')
            takeover = path / 'takeover.json'
            grasp = json.loads(takeover.read_text())['grasp_success'] if takeover.exists() else False
            row.update(status='failed', grasp_success=grasp, whole_success=False, whole_stable_success=False,
                       failure_class=details.get('last_phase', 'preflight_or_initialization'), failure=details)
        else:
            row['status'] = 'pending'
        rows.append(row)
    return rows


def execute(args):
    manifest = json.loads(args.manifest.read_text())
    assert sha(Path(manifest['source_pin']) / 'SOURCE_SHA256.json') == manifest['source_manifest_sha256']
    for name, digest in manifest['input_sha256'].items():
        assert sha(Path(name)) == digest, ('Frozen input changed', name)
    results = args.manifest.with_name(args.manifest.stem + '-results.json')
    while True:
        rows = status(manifest)
        running = sum(r['status'] == 'running' for r in rows)
        for row in rows:
            if running >= args.concurrency:
                break
            if row['status'] != 'pending':
                continue
            command = manifest['commands'][row['group']]
            options = command[command.index('--output') + 2:].copy()
            base = manifest['base_arguments'][row['group']]
            for flag, value in [('--dx', base['dx'] + row['delta_x_m']),
                                ('--dy', base['dy'] + row['delta_y_m']),
                                ('--yaw', base['yaw'] + row['delta_yaw_deg'])]:
                if flag in options:
                    options[options.index(flag) + 1] = str(value)
                else:
                    options += [flag, str(value)]
            subprocess.run([sys.executable, '-m', 'scripts.launch_g2_trial', '--name', row['name'],
                '--source-root', manifest['source_pin'], '--', *options], cwd=ROOT, check=True)
            running += 1
        rows = status(manifest)
        groups = {}
        for group in ['B', 'C']:
            finished = [r for r in rows if r['group'] == group and r['status'] in ['completed', 'failed']]
            picked = [r for r in finished if r['grasp_success']]
            groups[group] = dict(finished_attempts=len(finished), planned_attempts=10,
                acquisition_successes=len(picked), conditional_operation_attempts=len(picked),
                conditional_operation_successes=sum(r['whole_success'] for r in picked),
                whole_successes=sum(r['whole_success'] for r in finished),
                whole_stable_successes=sum(r['whole_stable_success'] for r in finished))
        out = dict(updated=datetime.now(timezone.utc).isoformat(), manifest_sha256=sha(args.manifest),
            groups=groups, trials=rows, all_finished=all(r['status'] in ['completed', 'failed'] for r in rows),
            denominator='All predeclared placements count, including planning failures; conditional operation denominator counts successful acquisitions only')
        results.write_text(json.dumps(out, indent=2) + '\n')
        if out['all_finished']:
            print(json.dumps(out['groups']))
            return
        time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['declare', 'run'])
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--a')
    parser.add_argument('--b')
    parser.add_argument('--c')
    parser.add_argument('--seed', type=int, default=2026092501)
    parser.add_argument('--concurrency', type=int, default=2, choices=[1, 2])
    args = parser.parse_args()
    (declare if args.mode == 'declare' else execute)(args)


if __name__ == '__main__':
    main()
