"""Independently check actual anchored motor targets and dense interpolation."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--motor-plan',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=161);a=p.parse_args();assert not a.output.exists()
    ref=json.loads(a.reference.read_text());assert ref['all_feasible'] and ref.get('known_motor_anchor');plan=json.loads(a.motor_plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec=a.knife_spec);closed=np.array(plan['close_q']);shifts=np.array([r['shift_m'] for r in ref['rows']]);q=np.array([r['q_thumb'] for r in ref['rows']]);rows=[]
    for shift in np.linspace(0,.04,a.samples):
        actual=closed.copy();actual[16:]+=np.array([np.interp(shift,shifts,q[:,i]) for i in range(4)])-q[0]
        gaps=g.self_gaps(actual,'thumb')+g.pair_gaps(actual,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);minimum=min(r['gap_lower_bound_m'] for r in gaps);margin=float(np.minimum(actual-g.w.lower,g.w.upper-actual).min());rows.append(dict(shift_m=float(shift),motor_thumb=actual[16:].tolist(),minimum_original_limit_margin_rad=margin,minimum_thumb_self_gap_m=minimum,passed=margin>=.005-1e-7 and minimum>=.000015-1e-7))
    # Exact runtime schedule at30Hz, before its0.025rad/step rate limiter.
    u=np.linspace(0,1,121);travel=.04*(u*u*u*(10-15*u+6*u*u));targets=np.array([[np.interp(s,shifts,q[:,i]) for i in range(4)] for s in travel]);peak=float(abs(np.diff(targets,axis=0)).max());result=dict(reference=str(a.reference),reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),motor_plan=str(a.motor_plan),motor_plan_sha256=hashlib.sha256(a.motor_plan.read_bytes()).hexdigest(),rows=rows,all_passed=all(r['passed'] for r in rows),peak_scheduled_step_rad=peak,original_rate_limit_rad=.025,rate_limit_required=peak>.025,scope='Motor target limit and conservative full-face SAT self-clearance only; intentional contact preload is not force regulation. Continuous physics, body support and real contact remain unverified.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}));assert result['all_passed'],'Rejected dense motor path; do not execute'


if __name__=='__main__':main()
