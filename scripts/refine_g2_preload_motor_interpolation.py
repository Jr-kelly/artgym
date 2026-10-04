"""Repair nominal motor interpolation clearance, without altering collision assets."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--motor-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 ref=json.loads(a.reference.read_text());plan=json.loads(a.motor_plan.read_text());assert ref['motor_geometry_passed'] and ref['known_motor_anchor'];g=DigitGeometry(max_face_axes=10000);closed=np.array(plan['close_q']);old=ref['rows'];s=np.array([r['shift_m'] for r in old]);q=np.array([r['q_thumb_preloaded'] for r in old]);touch=np.array([r['q_thumb'] for r in old]);rows=[];audits=[]
 def gaps(x):
  actual=closed.copy();actual[16:]=x
  return np.array([r['gap_lower_bound_m'] for r in g.self_gaps(actual,'thumb')+g.pair_gaps(actual,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')])])
 for shift in np.linspace(0,.04,81):
  motor=np.array([np.interp(shift,s,q[:,j]) for j in range(4)]);touch_q=np.array([np.interp(shift,s,touch[:,j]) for j in range(4)]);before=float(gaps(motor).min());nominal=motor.copy();fit=None
  if shift>0 and before<.00010:
   lo=np.maximum(g.w.lower[16:]+.005,motor-.03);hi=np.minimum(g.w.upper[16:]-.005,motor+.03)
   fit=minimize(lambda x:float(np.sum((x-nominal)**2)),motor,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=lambda x:(gaps(x)-.00010)*1000)],options=dict(maxiter=50,ftol=1e-12));motor=fit.x
  after=float(gaps(motor).min());passed=after>=.000015-1e-7;rows.append(dict(shift_m=float(shift),q_thumb=touch_q.tolist(),q_thumb_preloaded=motor.tolist(),original_motor_limits_passed=bool(np.all(motor>=g.w.lower[16:]+.005-1e-7) and np.all(motor<=g.w.upper[16:]-.005+1e-7)),self_intersections=[],maximum_preloaded_joint_step_rad=float(abs(motor-np.array(rows[-1]['q_thumb_preloaded'])).max()) if rows else 0.));audits.append(dict(shift_m=float(shift),minimum_gap_before_m=before,minimum_gap_after_m=after,correction_rad=(motor-nominal).tolist(),optimizer_message=fit.message if fit is not None else None,passed=passed));print(json.dumps(audits[-1]),flush=True)
 ref['rows']=rows;ref['motor_geometry_passed']=all(r['original_motor_limits_passed'] and x['passed'] for r,x in zip(rows,audits));ref['interpolation_refinement']=dict(source_reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),target_clearance_m=.00010,original_audit_threshold_m=.000015,scope='Offline nominal motor-only interpolation repair; original collision meshes, joint limits and physical controller unchanged, no contactforce or behavioral claim',audits=audits);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(ref,indent=2));assert ref['motor_geometry_passed'],'Rejected motor interpolation repair'

if __name__=='__main__':main()
