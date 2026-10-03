"""Certify a nominal postlift motor corridor for proprioceptive support search."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--pickup-plan',type=Path,required=True);p.add_argument('--measured-plan',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    plan=json.loads(a.pickup_plan.read_text());measured=json.loads(a.measured_plan.read_text());g=DigitGeometry(knife_spec=a.knife_spec);initial=np.array(plan['close_q']);w=np.array(measured['wrist_in_knife']);slider=measured['planning_slider_m'];rows=[]
    for delta in np.linspace(0,-.30,101):
        target=initial.copy();target[7]+=delta
        pair=g.self_gaps(target,'middle')+g.pair_gaps(target,[('hand_r_middle_pad_link','hand_r_base_link'),('hand_r_middle_link4','hand_r_base_link')]);selfgap=min(r['gap_lower_bound_m'] for r in pair);limit=float(np.minimum(target-g.w.lower,g.w.upper-target).min());knife=g.gaps(target,w,slider,'middle');other=[r for r in knife if not(r['hand_link']=='hand_r_middle_pad_link' and r['knife_link']=='link_0')];gap=min(r['gap_lower_bound_m'] for r in other);passed=selfgap>=.000015-1e-7 and limit>=.005-1e-7 and gap>=.000005-1e-7
        rows.append(dict(delta_rad=float(delta),middle_q4_motor_rad=float(target[7]),self_gap_m=selfgap,limit_margin_rad=limit,other_knife_gap_m=gap,passed=passed))
        if not passed:break
    certified=[r for r in rows if r['passed']];assert len(certified)>1
    result=dict(joint_name='hand_r_middle_joint4',hand_index=7,motor_upper_rad=float(initial[7]),motor_lower_rad=certified[-1]['middle_q4_motor_rad'],search_interval_seconds=[12.,16.],motor_step_rad=.004,filtered_deflection_threshold_rad=.020,consecutive_contact_proxy_frames=5,filter_frames=5,rows=rows,all_requested_corridor_passed=len(rows)==101 and rows[-1]['passed'],pickup_plan_sha256=hashlib.sha256(a.pickup_plan.read_bytes()).hexdigest(),measured_plan_sha256=hashlib.sha256(a.measured_plan.read_bytes()).hexdigest(),scope='Nominalheld motor/self/forbiddenknife corridor; intendedmiddlepad/body contact allowed. Originalgains/limits. Runtime uses measuredq andissuedtargetonly, no object/contacttruth. Jointlag is a contact/load proxy, not exactknifeownership or constant/measuredforce. Actualphysics support required.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


if __name__=='__main__':main()
