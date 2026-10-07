"""Necessary offline motor/touch reference guard, not actual contact acceptance."""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--knots',type=Path,required=True);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
    m=json.loads(a.reference.read_text());kn=json.loads(a.knots.read_text());g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');k=G2Kinematics();H=HandIntersection()
    z=np.load(a.source/'takeover.npz');O=transform(z['object_state'][:3],z['object_state'][3:7]);q0=z['robot_q'][7:];duration=m['rows'][-1]['time_s'];q1=np.asarray(m['target_hand_q']);rows=[]
    tt=np.asarray([r['time_s'] for r in kn]);ring=np.asarray([r['touch_q'] for r in kn])
    for i,r in enumerate(m['rows']):
        if i%3 and i!=len(m['rows'])-1:continue
        u=r['time_s']/duration;f=u**3*(10-15*u+6*u*u);q=(1-f)*q0+f*q1;q[12:16]=[np.interp(r['time_s'],tt,ring[:,j]) for j in range(4)]
        W=k.forward(r['arm_q']);L=np.linalg.inv(O)@W
        gaps=[b for digit in ['thumb','ring'] for b in g.gaps(q,L,float(z['slider_q']),digit,certify_clearance_m=.0003)]
        forbidden=[b for b in gaps if b['gap_lower_bound_m']<-.0005 and (not b['hand_link'].endswith(('link4','pad_link')) or b['knife_link']=='link_1' and '_ring_' in b['hand_link'])]
        rows.append({'time_s':r['time_s'],'intersections':H.inspect(q),'forbidden_body_parts':forbidden,'touch_q':q.tolist()})
    motor=np.asarray([r['hand_q'] for r in m['rows']]);limit_violations=np.argwhere((motor<g.w.lower-1e-6)|(motor>g.w.upper+1e-6));maximum_rate=float(abs(np.diff(motor,axis=0)).max()*30)
    summary={'frames_checked':len(rows),'touch_self_frames':sum(bool(r['intersections']) for r in rows),'forbidden_part_frames':sum(bool(r['forbidden_body_parts']) for r in rows),
             'original_target_limit_violations':len(limit_violations),'max_motor_rate_rad_s':maximum_rate,'max_contact_domain_error_m':max(r['point_error_m'] for r in kn),
             'scope':'Offline touch/motor screening. Actual native body/hand contacts, preload, carrying and full action remain unverified'}
    (a.reference.parent/'dense-guard.json').write_text(json.dumps({'summary':summary,'rows':rows,'target_limit_entries':limit_violations.tolist()},indent=2))
    record('retained_transition_reference_dense_guard',[str(a.reference.parent/'dense-guard.json')],summary,next_step='Clear actualtouchgeometry and originalmotorrate -> native changedcontactlayout once; blocked -> firstexactconstraint only')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
