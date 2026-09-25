"""Audit every predeclared placement, preserving aborts and undefined metrics.

Reads raw trajectories and immutable source manifests. Does not alter trials,
the preregistration, the running driver, or any physical/controller setting.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.g2_kinematics import transform
from scripts.run_g2_small_variations import alive


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def fraction(numerator, denominator):
    return dict(successes=numerator, attempts=denominator,
                rate=numerator / denominator if denominator else None)


def first_sustained(mask, count=3):
    indices = np.flatnonzero(np.convolve(np.asarray(mask, dtype=int), np.ones(count, dtype=int), 'valid') == count)
    return int(indices[0]) if len(indices) else None


def inspect_trial(root, spec, manifest):
    path = root / spec['name']
    proc_path = root / (spec['name'] + '-process.json')
    if not proc_path.exists():
        return dict(spec, status='pending')
    process = read(proc_path)
    if alive(process):
        return dict(spec, status='running', pid=process['pid'])
    source = Path(process['pin'])
    assert digest(source / 'SOURCE_SHA256.json') == manifest['source_manifest_sha256']
    for name, sha in read(source / 'SOURCE_SHA256.json').items():
        assert digest(source / name) == sha, (spec['name'], 'Source changed', name)
    base = manifest['base_arguments'][spec['group']]
    command = process['command']
    for flag, expected in [('--dx', base['dx'] + spec['delta_x_m']),
                           ('--dy', base['dy'] + spec['delta_y_m']),
                           ('--yaw', base['yaw'] + spec['delta_yaw_deg'])]:
        assert abs(float(command[command.index(flag) + 1]) - expected) < 1e-12
    assert command[command.index('--group') + 1] == spec['group']
    physics = path / 'physics.json'
    if physics.exists():
        assert physics.read_bytes() == (root / manifest['fixed_cases']['B'] / 'physics.json').read_bytes()
    final = read(path / 'report.json') if (path / 'report.json').exists() else None
    failure = read(path / 'failure.json') if (path / 'failure.json').exists() else None
    row = dict(spec, status='completed' if final else 'aborted', process_started=process['started'],
        source_sha256=process['source_manifest_sha256'], frozen_physics_verified=physics.exists(),
        pickup_success=bool(final and final['grasp_success']),
        whole_success=bool(final and final['whole_success']),
        whole_stable_success=bool(final and final.get('whole_stable_success')),
        termination_phase=failure.get('last_phase') if failure else None,
        exception=failure, failure_class=final.get('failure_class') if final else 'preflight_or_initialization')
    takeover_path = path / 'takeover.json'
    takeover = read(takeover_path) if takeover_path.exists() else None
    if takeover:
        row['pickup_success'] = bool(takeover['grasp_success'])
    trace_path = path / ('trace.npz' if (path / 'trace.npz').exists() else 'partial-trace.npz')
    if not trace_path.exists():
        return row
    trace = np.load(trace_path)
    count = len(trace['time'])
    dt = float(np.median(np.diff(trace['time'])))
    assert abs(dt - 1 / 30) < 1e-7
    if failure:
        assert count == failure['steps']
    assert np.max(np.ptp(trace['targets'][:, -1:], axis=0)) == 0
    if physics.exists():
        assert read(physics)['knife_dof_properties']['stiffness'] == [0.]
    row.update(trace_sha256=digest(trace_path), trace_file=trace_path.name,
        frames=count, duration_s=float(trace['time'][-1]),
        all_phase_slider_travel_m=float(np.ptp(trace['slider'])),
        operation_frames=int((trace['phase'] == 'operate').sum()),
        robot_table_contact_frames=int((trace['robot_table_contacts'] > 0).sum()),
        finger_table_contact_frames=(trace['finger_table_contacts'] > 0).sum(0).tolist(),
        operation=None, initial_lift_success=False, phase_events={})
    table_height = base['table_height']
    for phase in dict.fromkeys(trace['phase']):
        indices = np.flatnonzero(trace['phase'] == phase)
        contacts = trace['finger_knife_contacts'][indices] > 0
        row['phase_events'][str(phase)] = dict(frames=len(indices),
            opposed_contact_fraction=float((contacts[:, 0] & (contacts[:, 1:].sum(1) >= 2)).mean()),
            knife_table_frames=int((trace['knife_table_contacts'][indices] > 0).sum()),
            robot_table_frames=int((trace['robot_table_contacts'][indices] > 0).sum()),
            end_object_height_m=float(trace['object'][indices[-1], 2]))
    lift = np.flatnonzero(trace['phase'] == 'lift')
    if len(lift) >= 15:
        row['initial_lift_success'] = bool((trace['object'][lift[-15:], 2] > table_height + .10).all())
    # Intentional release and reapproach are excluded from the airborne-drop
    # detector. Distinguish event onset from the later abort/guard location.
    transfer_phases = ['stand_orient', 'stand_tip', 'stand_yaw', 'stand_lower',
                       'support_settle', 'preorient', 'seat', 'relift',
                       'transport', 'gravity_close_orient', 'gravity_close_unload',
                       'gravity_close_hold', 'gravity_close_restore', 'gravity_close_return',
                       'operation_adjust', 'settle_history']
    row['acquisition_drop'] = None
    for phase in transfer_phases:
        ix = np.flatnonzero(trace['phase'] == phase)
        if not len(ix):
            continue
        no_contact = (trace['finger_knife_contacts'][ix] > 0).sum(1) == 0
        escaped = no_contact & ((trace['knife_table_contacts'][ix] > 0) |
                                (trace['object'][ix, 2] < table_height + .05))
        lost = first_sustained(escaped)
        if lost is not None:
            i = int(ix[lost])
            row['acquisition_drop'] = dict(phase=phase, frame=i,
                time_s=float(trace['time'][i]), phase_time_s=float((lost + 1) * dt),
                criterion='Three frames with no finger contact and tabletop contact or low knife; intentional releases excluded')
            break
    if row['acquisition_drop']:
        row['failure_class'] = 'acquisition_drop_during_' + row['acquisition_drop']['phase']
    elif not final:
        row['failure_class'] = 'acquisition_guard_' + str(row['termination_phase']) if count else 'preflight_or_initialization'
        support_file = path / 'table-support-check.json'
        if row['termination_phase'] == 'support_settle' and support_file.exists():
            support = read(support_file)
            row['end_support_check'] = support
            if support['tilt_rad'] > .15 and support['center_height_m'] > table_height + .06:
                row['failure_class'] = 'end_support_tilt_exceeded'
    op = np.flatnonzero(trace['phase'] == 'operate')
    if len(op):
        assert takeover and op[0] == takeover['step']
        slider = trace['slider'][op]
        expected_goals = takeover['slider_command_origin'] + np.where((np.arange(len(op)) // 150) % 2 == 0, .04, 0.)
        assert np.max(abs(expected_goals - trace['goal'][op])) < 1e-7
        errors = [float(np.max(abs(slider[min(i + 150, len(op)) - 9:min(i + 150, len(op))] -
                                  expected_goals[min(i + 150, len(op)) - 9:min(i + 150, len(op))])))
                  for i in range(0, len(op), 150)]
        obj = trace['object'][op]
        fixed = np.array(takeover['object_world'])
        drift = np.linalg.norm(obj[:, :3] - fixed[:3], axis=1)
        rotation = (Rotation.from_quat(fixed[3:]).inv() * Rotation.from_quat(obj[:, 3:])).magnitude()
        row['operation'] = dict(slider_travel_m=float(np.ptp(slider)), endpoint_errors_m=errors,
            basic_10mm=bool(len(op) == 600 and max(errors) < .01),
            strict_2mm=bool(len(op) == 600 and max(errors) < .002),
            world_drift_max_m=float(drift.max()), world_rotation_max_rad=float(rotation.max()),
            stable_10mm_025rad=bool((drift < .01).all() and (rotation < .25).all()),
            physical_drop=final.get('physical_drop_detected') if final else None,
            completed_cycles=final.get('completed_cycles') if final else None)
        if final:
            assert np.max(abs(np.array(errors) - [e['max_error_m'] for e in final['endpoints']])) < 1e-9
            assert abs(float(drift.max()) - final['world_drift_max_m']) < 1e-9
    video = path / 'continuous.mp4'
    assert video.exists(), ('Missing required video', path)
    import imageio_ffmpeg
    frames, duration = imageio_ffmpeg.count_frames_and_secs(str(video))
    assert frames == count and abs(duration - count / 30) < .05
    row['video'] = dict(file=video.name, sha256=digest(video), frames=frames, duration_s=duration)
    return row


def paired_prefix(root, a, b):
    if any(r['status'] in ['pending', 'running'] or 'trace_file' not in r for r in [a, b]):
        return None
    ta, tb = [np.load(root / r['name'] / r['trace_file']) for r in [a, b]]
    lengths = [int(np.flatnonzero(t['phase'] == 'operate')[0]) if (t['phase'] == 'operate').any()
               else len(t['time']) for t in [ta, tb]]
    n = min(lengths)
    errors = {key: float(np.max(abs(ta[key][:n] - tb[key][:n]))) for key in
              ['q', 'arm_q', 'object', 'slider_pose', 'wrist', 'targets', 'reference_targets',
               'slider', 'finger_knife_contacts', 'finger_table_contacts']}
    return dict(placement=a['placement'], frames=n, acquisition_lengths=lengths,
                exact=all(x == 0 for x in errors.values()) and lengths[0] == lengths[1], max_errors=errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    assert not args.output.exists(), 'Retain prior snapshots'
    manifest = read(args.manifest)
    root = args.manifest.parent
    rows = [inspect_trial(root, spec, manifest) for spec in manifest['trials']]
    complete = all(r['status'] not in ['pending', 'running'] for r in rows)
    assert complete or not args.require_complete, 'Validation is still running'
    grouped = {}
    for group in ['B', 'C']:
        finished = [r for r in rows if r['group'] == group and r['status'] not in ['pending', 'running']]
        picked = [r for r in finished if r['pickup_success']]
        grouped[group] = dict(planned=10, finished=len(finished),
            initial_lift=fraction(sum(r.get('initial_lift_success', False) for r in finished), len(finished)),
            pickup_to_takeover=fraction(len(picked), len(finished)),
            operation_given_pickup=fraction(sum(r['whole_success'] for r in picked), len(picked)),
            whole=fraction(sum(r['whole_success'] for r in finished), len(finished)),
            whole_stable=fraction(sum(r['whole_stable_success'] for r in finished), len(finished)),
            failures=dict(Counter(r['failure_class'] for r in finished if r['failure_class'])))
    pairs = [paired_prefix(root, rows[i], rows[i + 1]) for i in range(0, len(rows), 2)]
    output = dict(created=datetime.now(timezone.utc).isoformat(), manifest_sha256=digest(args.manifest),
        all_finished=complete, groups=grouped, pairs=pairs, trials=rows,
        metric_scope='Operation metrics are null when policy was not reached; passive acquisition slider travel is separate. All predeclared attempts remain in whole-task denominator.',
        independence='Ten placements paired across B/C; paired acquisition failures are not twenty independent geometric samples.')
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(dict(all_finished=complete, groups=grouped)))


if __name__ == '__main__':
    main()
