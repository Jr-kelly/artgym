"""Known-command reverse tangential preload; not measured force control.

A6mm virtual motor lead is prescribed over the full retraction to address
finite-PD/kinematic tracking lag, rather than fitting an endpoint decimal.
Original meshes, joint limits and physical actuators remain unchanged.
"""
import argparse,json,copy,hashlib
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--lead-mm',type=float,default=6.);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert 3<=a.lead_mm<=8 and not a.output.exists();plan=json.loads(a.plan.read_text());ref=json.loads(a.reference.read_text());assert ref['all_feasible'] and ref['known_motor_anchor'] and not ref.get('posture_preload');g=DigitGeometry(max_face_axes=10000);h=g.w;initial=np.array(plan['close_q']);w=np.array(plan['wrist_in_knife']);normal=np.array([0,1,0]);v=np.concatenate([p for p,_ in g.meshes['hand_r_thumb_pad_link']]);rows=[]
 @lru_cache(maxsize=4096)
 def sample(values):
  q=initial.copy();q[16:]=values;m=w@h.forward(q)['hand_r_thumb_pad_link'];vertices=v@m[:3,:3].T+m[:3,3];projection=vertices@normal;weights=np.exp(-(projection-projection.min())/.0002);point=weights@vertices/weights.sum();gaps=g.self_gaps(q,'thumb',certify_clearance_m=.0001)+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);return point,np.array([r['gap_lower_bound_m'] for r in gaps])
 start=sample(tuple(ref['rows'][0]['q_thumb']))[0];previous=np.array(ref['rows'][-1]['q_thumb']);lead=a.lead_mm*.001
 for shift in np.linspace(.04,0,41):
  target=start+[0,0,float(shift)-lead*(1-float(shift)/.04)];prior=previous.copy()
  def constraints(x):
   point,gaps=sample(tuple(x));return np.r_[(.00015-abs(point[[0,2]]-target[[0,2]]))*1000,(point[1]-start[1]+.0001)*1000,(start[1]+.0055-point[1])*1000,(gaps-.0001)*1000]
  def objective(x):
   point,_=sample(tuple(x));return float(np.sum(((point[[0,2]]-target[[0,2]])*250)**2)+((point[1]-start[1])*100)**2+.02*np.sum((x-prior)**2))
  if shift==.04:value=prior;fit=None
  else:
   lo=np.maximum(h.lower[16:]+.005,prior-.06);hi=np.minimum(h.upper[16:]-.005,prior+.06);fit=minimize(objective,prior,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=120,ftol=1e-11));value=fit.x
  point,gaps=sample(tuple(value));passed=bool(constraints(value).min()>=-1e-4);row=dict(shift_m=float(shift),q_thumb=value.tolist(),point_motor_nominal_knife_m=point.tolist(),virtual_reverse_lead_m=float(lead*(1-shift/.04)),minimum_motor_self_gap_m=float(gaps.min()),nominal_normal_relief_m=float(point[1]-start[1]),feasible=passed,optimizer_success=bool(fit.success) if fit is not None else True,message=str(fit.message) if fit is not None else 'Same actual known full-extension target');rows.append(row);print(json.dumps(row),flush=True);previous=value
  if not passed:break
 ref=copy.deepcopy(ref);ref['reverse_rows']=list(reversed(rows));ref['reverse_motor_preload']=dict(lead_m=lead,direction_blend_seconds=.75,all_feasible=len(rows)==41 and all(r['feasible'] for r in rows),source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),scope=__doc__,input='Known requested direction and reference phase only; no slider/contact/force truth',geometry_scope='Motor point tangential reach and original thumb self only; dense direction-blend/self/limits and physical contact still required');a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(ref,indent=2));assert ref['reverse_motor_preload']['all_feasible'],'Rejected reverse fullstroke; do not execute'
if __name__=='__main__':main()
