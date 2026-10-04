"""Known motor-point tangential stroke, with bounded normal relief.

Virtual position targets may compress the knife, as finite PD preload does.
Original physical collision, gravity and torque limits remain active in rollout.
No motor-point depth is presented as measured or constant pressure.
"""
import argparse,json,hashlib
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry

def plan_stroke(plan,maximum_normal_relief=.0055,source_plan_sha256=None,lateral_relief=0.):
 g=DigitGeometry();h=g.w;initial=np.array(plan['close_q']);w=np.array(plan['wrist_in_knife']);n=np.array(plan['contact_normals'][0]);assert np.allclose(n,[0,1,0]);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);hull=ConvexHull(v);centers=v[hull.simplices].mean(1);normals=hull.equations[:,:3];previous=initial[16:].copy();rows=[]
 @lru_cache(maxsize=4096)
 def sample(values):
  q=initial.copy();q[16:]=values;m=w@h.forward(q)['hand_r_thumb_pad_link'];vertices=v@m[:3,:3].T+m[:3,3];pr=vertices@n;weights=np.exp(-(pr-pr.min())/.0002);point=weights@vertices/weights.sum();fc=centers@m[:3,:3].T+m[:3,3];support=fc@n<=pr.min()+.0004;facing=float((normals@m[:3,:3].T@(-n))[support].max()) if support.any() else -1.;gaps=g.self_gaps(q,'thumb',certify_clearance_m=.00010)+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);return point,facing,np.array([r['gap_lower_bound_m'] for r in gaps])
 start=sample(tuple(previous))[0].copy();lo_limit=h.lower[16:]+.005;hi_limit=h.upper[16:]-.005
 for shift in np.linspace(0,.04,41):
  desired=start+np.array([0.,0.,shift]);prior=previous.copy();clearance=.000015+.000085*min(float(shift)/.001,1.)
  def constraints(x):
   point,facing,gaps=sample(tuple(x));return np.r_[(.00015+lateral_relief-abs(point[0]-desired[0]))*1000,(.00015-abs(point[2]-desired[2]))*1000,(point[1]-start[1]+.00010)*1000,(start[1]+maximum_normal_relief-point[1])*1000,facing-.25,(gaps-clearance)*1000]
  def objective(x):
   point,_,_=sample(tuple(x));return float(np.sum(((point[[0,2]]-desired[[0,2]])*250)**2)+((point[1]-start[1])*100)**2+.02*np.sum((x-prior)**2))
  if shift==0:fit=None;motor=prior
  else:
   lo=np.maximum(lo_limit,prior-.06);hi=np.minimum(hi_limit,prior+.06);fit=minimize(objective,prior,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=100,ftol=1e-11));motor=fit.x
  point,facing,gaps=sample(tuple(motor));passed=bool(constraints(motor).min()>=-1e-4);row=dict(shift_m=float(shift),q_thumb=motor.tolist(),point_motor_nominal_knife_m=point.tolist(),nominal_normal_relief_m=float(point[1]-start[1]),facing=facing,minimum_motor_self_gap_m=float(gaps.min()),maximum_joint_step_rad=float(abs(motor-prior).max()),feasible=passed,optimizer_success=bool(fit.success) if fit is not None else True,message=fit.message if fit is not None else 'Known issued initial target retained');rows.append(row);print(json.dumps(row),flush=True);previous=motor
  if not passed:break
 ref=dict(all_feasible=len(rows)==41 and all(r['feasible'] for r in rows),known_motor_anchor=True,rows=rows,travel_seconds=4.,source_plan_sha256=source_plan_sha256,nominal_motor_start_point_m=start.tolist(),maximum_normal_relief_m=maximum_normal_relief,lateral_motor_region_halfspan_m=lateral_relief,scope=__doc__,motor_target_scope='Direct full40mm tangential virtualmotor trajectory; bounded normalrelief is not a force controller. No knife-target separation certificate, because virtualPDpreload may overlapobject; actualoriginalcollision/PD physics decides contact. Independent originalself/limit denseaudit required.')
 return ref

def main():
 p=argparse.ArgumentParser();p.add_argument('--lateral-relief',type=float,default=0.,help='Allow bounded motorpad lateralroll instead of fixedcentroid; originalself/limit and full40mmtangential normalbounds retained. Virtualmotor region is not measuredcontactpatch.');p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--maximum-normal-relief',type=float,default=.0055);a=p.parse_args();assert not a.output.exists()
 ref=plan_stroke(json.loads(a.plan.read_text()),a.maximum_normal_relief,hashlib.sha256(a.plan.read_bytes()).hexdigest(),a.lateral_relief)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(ref,indent=2));assert ref['all_feasible'],'Rejected full tangential motor path; do not execute'

if __name__=='__main__':main()
