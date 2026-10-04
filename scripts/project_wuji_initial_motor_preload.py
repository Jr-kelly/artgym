"""Project an initial estimated motor plan into original self geometry.

Only predeclared known targets and original robot meshes are read. Intentional
object compression remains a finite-PD hypothesis, never measured pressure.
"""
import argparse,copy,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def project(plan):
 g=DigitGeometry(max_face_axes=10000);h=g.w;result=copy.deepcopy(plan);reports=[]
 def gaps(q):
  return np.array([r['gap_lower_bound_m'] for f in FINGERS for r in g.self_gaps(q,f,certify_clearance_m=.0001)])
 # Projection first repairs thumb/underside interactions. The index target
 # forms the same side contact after lift and is checked with that repair.
 for key,ids in [('close_q',np.array([16,17,18,19])),('post_lift_close_q',np.array([0,1,2,3,16,17,18,19]))]:
  target=np.asarray(result[key]).copy()
  if key=='post_lift_close_q':target[16:]=result['close_q'][16:]
  nominal=target.copy();before=gaps(nominal);lo=np.maximum(h.lower[ids]+.005,nominal[ids]-.06);hi=np.minimum(h.upper[ids]-.005,nominal[ids]+.06)
  def full(x):q=nominal.copy();q[ids]=x;return q
  def constraints(x):return (gaps(full(x))-.0001)*1000
  if constraints(nominal[ids]).min()>=-1e-7:fit=None;value=nominal
  else:
   fit=minimize(lambda x:float(np.sum(((x-nominal[ids])/.02)**2)),np.clip(nominal[ids],lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':120,'ftol':1e-10});value=full(fit.x)
  after=gaps(value);passed=bool(after.min()>=.0001-1e-7);reports.append(dict(target=key,minimum_self_before_m=float(before.min()),minimum_self_after_m=float(after.min()),maximum_motor_change_rad=float(abs(value-nominal).max()),passed=passed,optimizer_success=bool(fit.success) if fit is not None else True,message=str(fit.message) if fit is not None else 'Already clear'));result[key]=value.tolist()
  if not passed:break
 # Known closure waypoints retain the same touch stage, repaired motor close.
 result['close_waypoints'][-1]['q']=result['close_q'];result['initial_motor_self_projection']=dict(reports=reports,passed=len(reports)==2 and all(r['passed'] for r in reports),scope='Original self geometry at motor endpoints only; dense closing/transfer/fullstroke and actual continuous physics still required. Bounded target correction changes preload, not constant pressure.')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--observation',type=Path,required=True);p.add_argument('--operating-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();j=json.loads(a.observation.read_text());motor=project(j['motor_plan']);a.output.mkdir(parents=True,exist_ok=False);(a.output/'motor-plan.json').write_text(json.dumps(motor,indent=2));op=json.loads(a.operating_plan.read_text());op.update(close_q=motor['post_lift_close_q'],initial_geometry_estimate=j['estimate']);(a.output/'operating-plan.json').write_text(json.dumps(op,indent=2));print(json.dumps(motor['initial_motor_self_projection']),flush=True);assert motor['initial_motor_self_projection']['passed'],'Reject original self collision; do not execute'
if __name__=='__main__':main()
