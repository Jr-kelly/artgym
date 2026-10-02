"""Offline continuous rolling-pad IK, preserving original collision/limit checks.

Uses an initial calibrated grasp and endpoint hypothesis. No physics or force
claim. Hard per-knot joint-change bounds prevent a point-valid IK branch jump.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--joint-step',type=float,default=.04);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise FileExistsError(a.output)
 j=json.loads(a.plan.read_text());g=DigitGeometry(knife_spec=a.knife_spec);h=g.w;w=np.array(j['wrist_in_knife']);q0=np.array(j['touch_q']);n=np.array(j['contact_normals'][0]);end=np.array(j['stroke_endpoint']['thumb_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);rows=[];previous=q0[16:].copy()
 def evaluate(x,shift):
  q=q0.copy();q[16:]=x;t=w@h.forward(q)['hand_r_thumb_pad_link'];points=v@t[:3,:3].T+t[:3,3];proj=points@n;weight=np.exp(-(proj-proj.min())/.0002);weight/=weight.sum();point=weight@points;facing=float(t[:3,0]@(-n));knife=min(r['gap_lower_bound_m'] for r in g.gaps(q,w,j['planning_slider_m']+shift));selfgap=min(r['gap_lower_bound_m'] for r in g.self_gaps(q,'thumb'));return point,facing,knife,selfgap
 start=evaluate(previous,0.)[0]
 for shift in np.linspace(0,.04,41):
  desired=start+np.array([0.,0.,shift]);reference=q0[16:]*(1-shift/.04)+end*(shift/.04);prior=previous.copy();lo=np.maximum(h.lower[16:]+.08,prior-a.joint_step);hi=np.minimum(h.upper[16:]-.08,prior+a.joint_step)
  def objective(x):
   point,*_=evaluate(x,shift);return float(((point-desired)*250)**2@np.ones(3)+.05*np.sum((x-reference)**2))
  def constraints(x):
   point,facing,knife,selfgap=evaluate(x,shift);return np.r_[(.0001-np.linalg.norm(point-desired))*1000,facing-.25,(knife-.000005)*1000,(selfgap-.000015)*1000]
  fit=minimize(objective,np.clip(reference,lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=160,ftol=1e-11));point,facing,knife,selfgap=evaluate(fit.x,shift);ok=bool(constraints(fit.x).min()>=-1e-4);rows.append(dict(shift_m=float(shift),q_thumb=fit.x.tolist(),point_error_m=float(np.linalg.norm(point-desired)),pad_facing_cosine=facing,minimum_knife_gap_m=knife,minimum_self_gap_m=selfgap,maximum_joint_step_rad=float(abs(fit.x-prior).max()),feasible=ok,optimizer_success=bool(fit.success),message=fit.message));previous=fit.x
  if not ok:break
 result=dict(source=str(a.plan),scope='Offline continuous rolling-pad IK hypothesis; measured pressure, servo tracking and physics remain unverified',rows=rows,joint_step_rad=a.joint_step,all_feasible=bool(len(rows)==41 and all(r['feasible'] for r in rows)),target_travel_m=.04,travel_seconds=4.,hold_seconds=1.);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(all_feasible=result['all_feasible'],knots=len(rows),last=rows[-1])));assert result['all_feasible'],'Do not execute an incomplete/rejected trajectory'
if __name__=='__main__':main()
