"""Read-only stage audit, including incomplete acquisitions and their raw traces."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def audit(folder):
    failure = read(folder/'failure.json')
    report = read(folder/'report.json')
    path = folder/'trace.npz'
    if not path.exists():
        path = folder/'partial-trace.npz'
    if not path.exists():
        return dict(failure=failure, trace_missing=True,
            failure_category='preflight_parser' if failure.get('exception_type')=='ArgumentParserError' else 'missing_trace')
    trace = np.load(path)
    phases = trace['phase']
    rows = []
    for phase in dict.fromkeys(phases):
        ids = np.flatnonzero(phases == phase)
        obj = trace['object'][ids]
        rows.append(dict(phase=str(phase), frames=len(ids),
            first_s=float(trace['time'][ids[0]]), last_s=float(trace['time'][ids[-1]]),
            world_motion_from_phase_first_frame_m=float(np.linalg.norm(obj[:,:3]-obj[0,:3],axis=-1).max()),
            world_rotation_from_phase_first_frame_rad=float((Rotation.from_quat(obj[0,3:]).inv()*Rotation.from_quat(obj[:,3:])).magnitude().max()),
            slider_travel_m=float(np.ptp(trace['slider'][ids])),
            knife_table_frames=int(np.count_nonzero(trace['knife_table_contacts'][ids])),
            finger_contact_fractions=np.mean(trace['finger_knife_contacts'][ids]>0,axis=0).tolist(),
            thumb_slider_contact_fraction=float(np.mean(trace['finger_slider_contacts'][ids,0]>0))))
    lift = next((r for r in rows if r['phase']=='lift'), None)
    flip = read(folder/'air-flip-check.json')
    gait = read(folder/'gait-checks.json').get('stages',[])
    bad = [r for r in gait if not r['stable']]
    # A complete120-frame lift ending airborne and supported establishes only
    # pickup; the later grasp_success gate includes gait and cannot replace it.
    ids = np.flatnonzero(phases=='lift')
    lift_end = ids[-30:] if len(ids) else []
    pickup = bool(len(ids)>=120 and len(lift_end)==30 and
        np.all(trace['object'][lift_end,2]>.85) and
        not np.any(trace['knife_table_contacts'][lift_end]) and
        np.all(trace['finger_knife_contacts'][lift_end].sum(axis=-1)>0))
    message = failure.get('message','')
    category = ('flip_ik_precheck' if 'Air-flip IK' in message else
        'gait_support_contact' if 'Required support contact' in message else
        'gait_stability' if 'Gait fixed-reference' in message else
        'alignment_bounds' if 'One-shot alignment outside' in message else
        'other_failure' if failure else 'completed')
    return dict(trace=str(path), trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        frames=len(phases), final_phase=str(phases[-1]), failure=failure,
        failure_category=category, pickup_retained_at_lift_end=pickup,
        flip_pass=bool(flip.get('retained',False)), flip_check=flip,
        first_failed_gait_check=bad[0] if bad else None,
        gait_checks=gait, stages=rows,
        acquisition_gate_pass=bool(report.get('grasp_success',False)),
        operation_entered=bool(np.any(phases=='operate')),
        whole_success=bool(report.get('required_task_success',False)))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results',type=Path,default=Path('research/g2-local-policy-validation-v1-results.json'))
    p.add_argument('--root',type=Path,default=Path('runs/g2-local-policy-20260928'))
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();results=read(a.results);rows=[]
    for trial in results['trials']:
        if trial['status'] not in ['failed','finished']:
            continue
        row=dict(trial);row.update(audit(a.root/trial['name']));rows.append(row)
    categories={}
    for row in rows:
        key=row.get('failure_category','missing');categories[key]=categories.get(key,0)+1
    out=dict(scope='Raw acquisition-stage audit; phase-relative motion is descriptive, never a relaxed success criterion.',
        source_results_updated_utc=results['updated_utc'], planned=results['planned'],
        finished=results['finished'], audited=len(rows),
        pickup_pass=sum(r.get('pickup_retained_at_lift_end',False) for r in rows),
        flip_pass=sum(r.get('flip_pass',False) for r in rows),
        acquisition_gate_pass=results['acquisition_successes'],
        operation_entered=sum(r.get('operation_entered',False) for r in rows),
        conditional_operation_success=(results['conditional_operation_successes']/results['acquisition_successes'] if results['acquisition_successes'] else None),
        whole_success=results['whole_successes'],failure_categories=categories,
        finger_order=['thumb','index','middle','ring','pinky'],trials=rows)
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='trials'}))


if __name__=='__main__':main()
