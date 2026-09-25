"""Compare completed takeover controls without changing any physical result.

The static control uses the full-policy takeover time, not its own late report
reference. Contacts are ordered thumb/index/middle/ring/pinky; motor q uses
index/middle/pinky/ring/thumb. No force is inferred from targets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def relative_pose(obj, wrist):
    wr = Rotation.from_quat(wrist[:, 3:])
    return np.c_[wr.inv().apply(obj[:, :3] - wrist[:, :3]),
                 (wr.inv() * Rotation.from_quat(obj[:, 3:])).as_quat()]


def errors(values, ref):
    return (np.linalg.norm(values[:, :3] - ref[:3], axis=1),
            (Rotation.from_quat(ref[3:]).inv() *
             Rotation.from_quat(values[:, 3:])).magnitude())


def summarize(path, reference_trial=None):
    t = np.load(path / 'trace.npz')
    report = json.loads((path / 'report.json').read_text())
    take = json.loads((path / 'takeover.json').read_text())
    physics = json.loads((path / 'physics.json').read_text())
    operation = np.flatnonzero(t['phase'] == 'operate')
    if len(operation):
        first = int(operation[0]); refindex = first - 1
        assert first == take['step']
        ref = np.asarray(take['object_world'])
        assert np.max(np.abs(ref - t['object'][refindex])) < 1e-7
        selection = operation
    else:
        if reference_trial is None:
            raise ValueError('Static hold requires an independently fixed comparison reference')
        other = json.loads((reference_trial / 'takeover.json').read_text())
        refindex = other['step'] - 1; first = refindex + 1
        assert abs(t['time'][refindex] - other['time']) < 1e-6
        ref = t['object'][refindex]
        selection = np.arange(first, len(t['time']))
    assert len(selection) == 600, 'Expected exactly 20 seconds at 30 Hz'
    ids = physics['hand_indices']
    rel = relative_pose(t['object'], t['wrist'])
    dp, dr = errors(t['object'][selection], ref)
    hp, hr = errors(rel[selection], rel[refindex])
    contact = t['finger_knife_contacts'][selection] > 0
    slider_contact = t['finger_slider_contacts'][selection, 0] > 0
    unstable = np.flatnonzero((dp >= .01) | (dr >= .25))
    absent = np.flatnonzero(~slider_contact)
    target = t['reference_targets'][selection][:, ids]
    target_ref = t['reference_targets'][refindex, ids]
    relative_time = t['time'][selection] - t['time'][refindex]
    raw = t['raw_policy_action'] if 'raw_policy_action' in t else t['action']
    out = dict(trial=path.name, trace_sha256=hashlib.sha256((path / 'trace.npz').read_bytes()).hexdigest(),
        reference_frame=int(refindex), reference_time_s=float(t['time'][refindex]),
        samples=len(selection), reference='one fixed world pose before the 600 scored frames',
        entered_policy=bool(len(operation)), action_mode=report['args'].get('policy_action_mode','full') if len(operation) else 'no-policy',
        world_position_max_mm=float(dp.max()*1000), world_rotation_max_rad=float(dr.max()),
        hand_position_max_mm=float(hp.max()*1000), hand_rotation_max_rad=float(hr.max()),
        stable_world=bool(not len(unstable)),
        first_world_instability_since_reference_s=float(relative_time[unstable[0]]) if len(unstable) else None,
        thumb_slider_contact_fraction=float(slider_contact.mean()),
        first_thumb_slider_loss_since_reference_s=float(relative_time[absent[0]]) if len(absent) else None,
        contact_fraction_thumb_index_middle_ring_pinky=contact.mean(0).tolist(),
        slider_travel_mm=float(np.ptp(t['slider'][selection])*1000),
        slider_initial_mm=float(t['slider'][refindex]*1000),
        finger_table_contacts=int(t['finger_table_contacts'][selection].sum()),
        knife_table_contacts=int(t['knife_table_contacts'][selection].sum()),
        nonthumb_target_max_change_rad=float(np.abs(target[:, :16]-target_ref[:16]).max()),
        first_command_max_delta_rad=float(np.abs(target[0]-target_ref).max()),
        thumb4_target_start_end_rad=[float(target_ref[-1]),float(target[-1,-1])],
        thumb4_actual_start_end_rad=[float(t['q'][refindex,-1]),float(t['q'][selection[-1],-1])],
        raw_first_action=raw[first].tolist(), executed_first_action=t['action'][first].tolist(),
        operation_score=report if len(operation) else None)
    if reference_trial is not None and reference_trial != path:
        baseline = np.load(reference_trial / 'trace.npz')
        keys = ['q','arm_q','object','wrist','slider','targets','reference_targets']
        out['prefix_max_absolute_errors'] = {k:float(np.abs(t[k][:first]-baseline[k][:first]).max()) for k in keys}
        out['first_raw_actor_output_max_error_vs_full'] = float(np.abs(raw[first]-baseline['action'][first]).max()) if len(operation) else None
        out['physics_bytes_identical_to_full'] = (path/'physics.json').read_bytes() == (reference_trial/'physics.json').read_bytes()
    if (path/'gait-checks.json').exists():
        checks=json.loads((path/'gait-checks.json').read_text())
        matrix=np.asarray(checks['world_reference'])
        gait_ref=np.r_[matrix[:3,3],Rotation.from_matrix(matrix[:3,:3]).as_quat()]
        gd,gr=errors(t['object'][selection],gait_ref)
        out['same_window_original_gait_world_position_max_mm']=float(gd.max()*1000)
        out['same_window_original_gait_world_rotation_max_rad']=float(gr.max())
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',type=Path,required=True)
    p.add_argument('--control',type=Path,action='append',default=[])
    p.add_argument('--preset',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    rows=[summarize(a.full)]+[summarize(v,a.full) for v in a.control]
    if a.preset:rows.append(summarize(a.preset))
    out=dict(scope='Offline comparison, not additional physical trials',trials=rows)
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    for row in rows:print(json.dumps({k:v for k,v in row.items() if k not in ['operation_score','raw_first_action','executed_first_action']}))


if __name__=='__main__':main()
