"""Establish missing nominal middle support after a certified table pickup.

Uses one fixed offline held calibration; no live contact/pose controller. A
small geometric compression is an impedance hypothesis, not constant force.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pickup-plan',type=Path,required=True)
    p.add_argument('--measured-plan',type=Path,required=True)
    p.add_argument('--knife-spec',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    plan=json.loads(a.pickup_plan.read_text());measured=json.loads(a.measured_plan.read_text())
    g=DigitGeometry(knife_spec=a.knife_spec);q=np.array(measured['touch_q']);w=np.array(measured['wrist_in_knife']);slider=float(measured['planning_slider_m'])
    def gap(delta):
        sample=q.copy();sample[7]+=delta
        return min(r['gap_lower_bound_m'] for r in g.gaps(sample,w,slider,'middle') if r['hand_link']=='hand_r_middle_pad_link' and r['knife_link']=='link_0')
    # The observed missing support is lateral. Move only the distal middle
    # joint toward first contact, plus0.3mm geometric preload, within limits.
    delta=brentq(lambda x:gap(x)+.0003,-.16,0.,xtol=1e-10)
    initial=np.array(plan['close_q']);final=np.array(plan.get('post_lift_close_q',plan['close_q']));final[7]+=delta
    rows=[]
    for fraction in np.linspace(0,1,61):
        target=initial+fraction*(final-initial)
        pairs=g.self_gaps(target,'middle')+g.pair_gaps(target,[('hand_r_middle_pad_link','hand_r_base_link'),('hand_r_middle_link4','hand_r_base_link')])
        clearance=min(r['gap_lower_bound_m'] for r in pairs)
        margin=float(np.minimum(target-g.w.lower,g.w.upper-target).min())
        # Intentional middlepad/body contact is allowed; every other middle
        # link must remain separated from knife and slider in the held frame.
        knife=g.gaps(target,w,slider,'middle')
        forbidden=[r for r in knife if not (r['hand_link']=='hand_r_middle_pad_link' and r['knife_link']=='link_0')]
        knife_gap=min(r['gap_lower_bound_m'] for r in forbidden)
        rows.append(dict(fraction=float(fraction),self_gap_m=clearance,limit_margin_rad=margin,other_knife_gap_m=knife_gap,passed=clearance>=.000015-1e-7 and margin>=.005-1e-7 and knife_gap>=.000005-1e-7))
    audit=dict(delta_middle_q4_rad=float(delta),measured_pad_body_gap_initial_m=gap(0),modeled_pad_body_gap_final_m=gap(delta),negative_SAT_target_m=-.0003,negative_SAT_is_not_certified_penetration=True,all_passed=all(r['passed'] for r in rows),rows=rows,pickup_plan_sha256=hashlib.sha256(a.pickup_plan.read_bytes()).hexdigest(),measured_plan_sha256=hashlib.sha256(a.measured_plan.read_bytes()).hexdigest(),scope='Offline fixednominal postlift middlecontact hypothesis, originalmotor limits/gains; negativeSAT is not a penetration/force measurement or regulation. Table pickup/lift prefix unchanged. Dense thumb path and actual continuous physics still required.')
    (a.output/'audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps({k:v for k,v in audit.items() if k!='rows'}),flush=True)
    assert audit['all_passed'],'Rejected postlift support; do not execute'
    plan['post_lift_close_q']=final.tolist();plan['post_lift_preload_seconds']=[12.,14.];plan['middle_support_adaptation']=audit
    (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2))


if __name__=='__main__':main()
