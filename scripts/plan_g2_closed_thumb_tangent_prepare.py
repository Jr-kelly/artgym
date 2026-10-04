"""Continuous closed-slider tangential preparation and a shared motor path.

The6mm virtual lead is reached through actual finite-PD motor movement after
pickup, then a single path is used in both directions. This avoids invalid
joint-space blends. Rail command remains40mm, no force/slider feedback or
positive rail actuation; normal relief is not constant force.
"""
import argparse,copy,json,hashlib
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--lead-mm',type=float,default=6.);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert 3<=a.lead_mm<=8 and not a.output.exists();plan=json.loads(a.plan.read_text());ref=json.loads(a.reference.read_text());assert ref['all_feasible'] and ref['known_motor_anchor'] and not ref.get('posture_preload');g=DigitGeometry(max_face_axes=10000);h=g.w;initial=np.array(plan['close_q']);w=np.array(plan['wrist_in_knife']);v=np.concatenate([p for p,_ in g.meshes['hand_r_thumb_pad_link']]);hull=ConvexHull(v);centers=v[hull.simplices].mean(1);normals=hull.equations[:,:3];rows=[];lead=a.lead_mm*.001
 @lru_cache(maxsize=4096)
 def sample(values):
  q=initial.copy();q[16:]=values;m=w@h.forward(q)['hand_r_thumb_pad_link'];vertices=v@m[:3,:3].T+m[:3,3];projection=vertices[:,1];weights=np.exp(-(projection-projection.min())/.0002);point=weights@vertices/weights.sum();fc=centers@m[:3,:3].T+m[:3,3];support=fc[:,1]<=projection.min()+.0004;facing=float((normals@m[:3,:3].T@[0,-1,0])[support].max()) if support.any() else -1.;gaps=g.self_gaps(q,'thumb',certify_clearance_m=.0001)+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);return point,facing,np.array([r['gap_lower_bound_m'] for r in gaps])
 previous=np.array(ref['rows'][0]['q_thumb']);assert np.allclose(previous,initial[16:]);start=sample(tuple(previous))[0]
 for shift in np.linspace(0,-lead,31):
  target=start+[0,0,float(shift)];prior=previous.copy()
  def constraints(x):
   point,facing,gaps=sample(tuple(x));return np.r_[(.00015-abs(point[[0,2]]-target[[0,2]]))*1000,(point[1]-start[1]+.0001)*1000,(start[1]+.0055-point[1])*1000,(gaps-.0001)*1000,facing-.25]
  def objective(x):
   point,_,_=sample(tuple(x));return float(np.sum(((point[[0,2]]-target[[0,2]])*250)**2)+((point[1]-start[1])*100)**2+.02*np.sum((x-prior)**2))
  if shift==0:value=prior;fit=None
  else:
   lo=np.maximum(h.lower[16:]+.005,prior-.03);hi=np.minimum(h.upper[16:]-.005,prior+.03);fit=minimize(objective,prior,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=120,ftol=1e-11));value=fit.x
  point,facing,gaps=sample(tuple(value));passed=bool(constraints(value).min()>=-1e-4);row=dict(virtual_shift_m=float(shift),q_thumb=value.tolist(),point_motor_nominal_knife_m=point.tolist(),supporting_facet_facing_cosine=facing,minimum_motor_self_gap_m=float(gaps.min()),nominal_normal_relief_m=float(point[1]-start[1]),feasible=passed,optimizer_success=bool(fit.success) if fit is not None else True,message=str(fit.message) if fit is not None else 'Original known closed motor retained');rows.append(row);print(json.dumps(row),flush=True);previous=value
  if not passed:break
 passed=len(rows)==31 and all(r['feasible'] for r in rows);result=dict(all_feasible=passed,preparation_rows=rows,scope=__doc__,source_reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest())
 if passed:
  extended=[]
  for r in list(reversed(rows))+[dict(virtual_shift_m=r['shift_m'],q_thumb=r['q_thumb'],feasible=r['feasible']) for r in ref['rows'][1:]]:
   extended.append(dict(shift_m=float((r['virtual_shift_m']+lead)/(.04+lead)*.04),q_thumb=r['q_thumb'],virtual_shift_m=r['virtual_shift_m'],feasible=r['feasible']))
  extended[0]['shift_m']=0.;extended[-1]['shift_m']=.04;reference=copy.deepcopy(ref);reference.update(rows=extended,closed_tangential_prepare_m=lead,virtual_motor_travel_m=.04+lead,scope=__doc__);result['reference']=reference
  operation=copy.deepcopy(plan);operation['close_q'][16:]=rows[-1]['q_thumb'];result['operation_plan']=operation
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));assert passed,'Rejected continuous tangential preparation, no execution'
if __name__=='__main__':main()
