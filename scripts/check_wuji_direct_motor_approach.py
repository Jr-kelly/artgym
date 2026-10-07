"""Dense preflight of the changed thumb approach; actual physics still required."""
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--motor',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    motion=json.loads(a.motor.read_text());D=motion['diagnostics']
    source=np.load(Path(motion['source'])/'takeover.npz')
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();checker=HandIntersection();times=np.array([d['time_s'] for d in D])
    hands=np.array([d['planned_hand_q'] for d in D]);arms=np.array([d['planned_arm_q'] for d in D])
    assert np.allclose([d['expected_object_world'] for d in D],D[0]['expected_object_world'])
    O=np.array(D[0]['expected_object_world']);rows=[]
    for t in np.linspace(times[0],times[-1],2*len(D)-1):
        h=np.array([np.interp(t,times,hands[:,j]) for j in range(20)])
        arm=np.array([np.interp(t,times,arms[:,j]) for j in range(7)])
        W=k.forward(arm);L=np.linalg.inv(O)@W;gaps=g.gaps(h,L,float(source['slider_q']),'thumb')
        frames=g.w.forward(h);table_clearance=min(float((v@(W@frames[name])[:3,:3].T+(W@frames[name])[:3,3])[:,2].min()-.75) for name,parts in g.meshes.items() for v,_ in parts)
        rows.append(dict(time_s=float(t),fraction=float(np.interp(t,times,[d['fraction'] for d in D])),thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
            thumb_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1'),
            hand_margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min()),
            arm_margin_rad=float(np.minimum(arm-k.lower,k.upper-arm).min()),hand_table_clearance_m=table_clearance,self=checker.inspect(h)))
    start=np.r_[motion['rows'][0]['arm_q'],motion['rows'][0]['hand_q']]
    result=dict(rows=rows,thumb_body_gap_min_m=min(r['thumb_body_gap_m'] for r in rows),
        thumb_body_source_gap_m=rows[0]['thumb_body_gap_m'],
        hand_margin_rad=min(r['hand_margin_rad'] for r in rows),arm_margin_rad=min(r['arm_margin_rad'] for r in rows),
        self_frames=sum(bool(r['self']) for r in rows),
        max_thumb_error_m=max(d['thumb_error_m'] for d in D),
        max_support_error_m=max(max(d['support_errors_m'].values()) for d in D),
        source_motor_jump_rad=float(abs(start-source['issued_target']).max()),thumb_cap_gap_min_m=min(r['thumb_cap_gap_m'] for r in rows),
        scope='Interpolated planned actual joint poses; existing acquired heel contact may withdraw without deepening. This does not certify actual dynamic tracking/contact.')
    candidate=json.loads(Path(motion['candidate']).read_text())
    crossing=[r for r in rows if .4<=r['fraction']<=.8]
    result['separated_crossing_body_gap_min_m']=min(r['thumb_body_gap_m'] for r in crossing) if crossing else None
    result['hand_table_clearance_min_m']=min(r['hand_table_clearance_m'] for r in rows)
    if motion.get('free_thumb_joint_path'):
        # Intermediate foot positions are soft guidance for a free digit.
        # Certify actual whole-digit clearance and the terminal cap target;
        # an arbitrary free-space waypoint is not a task contact constraint.
        terminal=[d for d in D if d['fraction']>.99]
        result['terminal_thumb_error_m']=max(d['thumb_error_m'] for d in terminal)
        guidance_ok=bool(terminal) and result['terminal_thumb_error_m']<.0005
        free=[r for r in rows if .3<=r['fraction']<=.75]
        result['free_joint_crossing_body_gap_min_m']=min(r['thumb_body_gap_m'] for r in free) if free else None
        guidance_ok=guidance_ok and bool(free) and result['free_joint_crossing_body_gap_min_m']>.0038
    else:guidance_ok=result['max_thumb_error_m']<.0005
    hand_steps=np.abs(np.diff(hands,axis=0));arm_steps=np.abs(np.diff(arms,axis=0))
    result['largest_adjacent_joint_step_rad']=float(max(hand_steps.max(),arm_steps.max()))
    crossing_ok=('thumb_waypoint_schedule' not in candidate or bool(crossing) and result['separated_crossing_body_gap_min_m']>.004)
    result['preflight_pass']=bool(crossing_ok and result['thumb_cap_gap_min_m']>-.00045 and result['thumb_body_gap_min_m']>=result['thumb_body_source_gap_m']-.00005 and
        result['hand_margin_rad']>=.049 and result['arm_margin_rad']>=.039 and result['self_frames']==0 and
        guidance_ok and result['hand_table_clearance_min_m']>.0002 and result['largest_adjacent_joint_step_rad']<.18 and result['max_support_error_m']<.0008 and result['source_motor_jump_rad']<1e-6)
    a.output.write_text(json.dumps(result,indent=2));summary={key:value for key,value in result.items() if key!='rows'}
    print(json.dumps(summary));record('direct_changed_approach_dense_preflight',[str(a.motor),str(a.output)],config=summary,
        next_step='Passing changedapproach -> nativecontactcheck immediately; rejected -> firstspecificgeometryconstraint, no native onfailure')
    if not result['preflight_pass']:raise SystemExit(2)


if __name__=='__main__':main()
