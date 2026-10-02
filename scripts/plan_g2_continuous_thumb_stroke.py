"""Offline continuous rolling-pad IK, preserving original collision/limit checks.

Uses an initial calibrated grasp and endpoint hypothesis. No physics or force
claim. Hard per-knot joint-change bounds prevent a point-valid IK branch jump.
"""
import argparse,json
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--joint-step',type=float,default=.04);p.add_argument('--thumb-base-margin',type=float,default=.08,help='Geometric reserve for original thumb base-joint limit; no motor-limit change');a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise FileExistsError(a.output)
 j=json.loads(a.plan.read_text());g=DigitGeometry(knife_spec=a.knife_spec);h=g.w;w=np.array(j['wrist_in_knife']);q0=np.array(j['touch_q']);n=np.array(j['contact_normals'][0]);end=np.array(j['stroke_endpoint']['thumb_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);rows=[];previous=q0[16:].copy()
 fixed=h.forward(q0);others=[]
 for link,meshes in g.meshes.items():
  if any('_'+f+'_' in link for f in ['index','middle','ring','pinky']):
   t=fixed[link]
   for vertices,axes in meshes:
    vertices=vertices@t[:3,:3].T+t[:3,3];center=vertices.mean(0);others.append((vertices,axes@t[:3,:3].T,center,float(np.linalg.norm(vertices-center,axis=1).max())))
 parts={float(shift):g.knife_geometry.collision_parts(j['planning_slider_m']+float(shift)) for shift in np.linspace(0,.04,41)}
 @lru_cache(maxsize=2048)
 def sample(values,shift):
  q=q0.copy();q[16:]=values;frames=h.forward(q);t=w@frames['hand_r_thumb_pad_link'];points=v@t[:3,:3].T+t[:3,3];proj=points@n;weight=np.exp(-(proj-proj.min())/.0002);weight/=weight.sum();point=weight@points;facing=float(t[:3,0]@(-n));knife=np.inf;selfgap=np.inf
  for link,meshes in g.meshes.items():
   if '_thumb_' not in link:continue
   for vertices,axes in meshes:
    fk=frames[link];vh=vertices@fk[:3,:3].T+fk[:3,3];nh=axes@fk[:3,:3].T;center=vh.mean(0);radius=float(np.linalg.norm(vh-center,axis=1).max());vo=vh@w[:3,:3].T+w[:3,3];no=nh@w[:3,:3].T
    for part in parts[shift]:
     ax=np.r_[no,part['normals']];pa=vo@ax.T;pb=part['vertices']@ax.T;knife=min(knife,float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()))
    for vb,nb,cb,rb in others:
     gap=float(np.linalg.norm(center-cb)-radius-rb)
     if gap<=.000015:
      ax=np.r_[nh,nb];pa=vh@ax.T;pb=vb@ax.T;gap=float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
     selfgap=min(selfgap,gap)
  return point,facing,knife,selfgap
 def evaluate(x,shift):return sample(tuple(x),float(shift))
 start=evaluate(previous,0.)[0]
 base_lower=h.lower[16:]+.08;base_upper=h.upper[16:]-.08
 base_lower[0]=h.lower[16]+a.thumb_base_margin;base_upper[0]=h.upper[16]-a.thumb_base_margin
 if a.thumb_base_margin>.08:
  old=previous.copy()
  def initial_constraints(x):
   point,facing,knife,selfgap=evaluate(x,0.)
   return np.r_[(.0001-np.linalg.norm(point-start))*1000,facing-.25,(knife-.000005)*1000,(selfgap-.000015)*1000]
  initial=minimize(lambda x:float(np.sum(((evaluate(x,0.)[0]-start)*250)**2)+.05*np.sum((x-old)**2)),np.clip(old,base_lower,base_upper),method='SLSQP',bounds=list(zip(base_lower,base_upper)),constraints=[dict(type='ineq',fun=initial_constraints)],options=dict(maxiter=160,ftol=1e-11))
  initial_audit=dict(old_thumb_q=old.tolist(),candidate_thumb_q=initial.x.tolist(),requested_base_margin_rad=a.thumb_base_margin,optimizer_success=bool(initial.success),minimum_constraint=float(initial_constraints(initial.x).min()),message=initial.message,scope='Geometry-only pressure-headroom hypothesis; no force or physics evidence')
  a.output.with_suffix('.initial-audit.json').write_text(json.dumps(initial_audit,indent=2));print(json.dumps(initial_audit),flush=True)
  assert initial_constraints(initial.x).min()>=-1e-4,'Rejected initial posture; do not execute'
  previous=initial.x;q0[16:]=previous;j['touch_q']=q0.tolist()
  a.output.with_suffix('.plan.json').write_text(json.dumps(j,indent=2))
  start=evaluate(previous,0.)[0]
 for shift in np.linspace(0,.04,41):
  desired=start+np.array([0.,0.,shift]);reference=q0[16:]*(1-shift/.04)+end*(shift/.04);prior=previous.copy();lo=np.maximum(base_lower,prior-a.joint_step);hi=np.minimum(base_upper,prior+a.joint_step)
  def objective(x):
   point,*_=evaluate(x,shift);return float(((point-desired)*250)**2@np.ones(3)+.05*np.sum((x-reference)**2))
  def constraints(x):
   point,facing,knife,selfgap=evaluate(x,shift);return np.r_[(.0001-np.linalg.norm(point-desired))*1000,facing-.25,(knife-.000005)*1000,(selfgap-.000015)*1000]
  fit=minimize(objective,np.clip(reference,lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=160,ftol=1e-11));point,facing,knife,selfgap=evaluate(fit.x,shift);ok=bool(constraints(fit.x).min()>=-1e-4);rows.append(dict(shift_m=float(shift),q_thumb=fit.x.tolist(),point_error_m=float(np.linalg.norm(point-desired)),pad_facing_cosine=facing,minimum_knife_gap_m=knife,minimum_self_gap_m=selfgap,maximum_joint_step_rad=float(abs(fit.x-prior).max()),feasible=ok,optimizer_success=bool(fit.success),message=fit.message));previous=fit.x
  with a.output.with_suffix('.knots.jsonl').open('a') as stream:stream.write(json.dumps(rows[-1])+'\n')
  if len(rows)%5==0:print(json.dumps(dict(knots=len(rows),shift_m=float(shift),feasible=ok)),flush=True)
  if not ok:break
 result=dict(source=str(a.plan),scope='Offline continuous rolling-pad IK hypothesis; measured pressure, servo tracking and physics remain unverified',rows=rows,joint_step_rad=a.joint_step,all_feasible=bool(len(rows)==41 and all(r['feasible'] for r in rows)),target_travel_m=.04,travel_seconds=4.,hold_seconds=1.);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(all_feasible=result['all_feasible'],knots=len(rows),last=rows[-1])));assert result['all_feasible'],'Do not execute an incomplete/rejected trajectory'
if __name__=='__main__':main()
