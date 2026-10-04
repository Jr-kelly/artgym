"""Bounded common pickup motor projection against original robot/table meshes.

Inputs are a known table localization and an initial-estimate motor plan.
No physical asset ID, live object state or contact force is read. The resulting
preload is a finite-PD hypothesis and requires dense checks and free physics.
"""
import argparse,copy,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry

def project(plan,localization,planning_table_clearance_m=.0005):
 g=DigitGeometry(max_face_axes=512);h=g.w;result=copy.deepcopy(plan)
 wrist=np.asarray(localization['object_world_matrix'])@np.asarray(plan['wrist_in_knife'])
 ids=np.array([h.names.index('hand_r_pinky_joint'+str(i)) for i in range(1,5)])
 opened=np.asarray(plan['open_q']);touch=np.asarray(plan['touch_q']);close=np.asarray(plan['close_q']);start=np.r_[opened[ids],touch[ids],close[ids]]
 lo=np.tile(h.lower[ids]+.005,3);hi=np.tile(h.upper[ids]-.005,3);lo=np.maximum(lo,start-.08);hi=np.minimum(hi,start+.08)
 def targets(x):
  o=opened.copy();t=touch.copy();c=close.copy();o[ids]=x[:4];t[ids]=x[4:8];c[ids]=x[8:];return o,t,c
 def table(q):
  frames=h.forward(q);values=[]
  for name,meshes in g.meshes.items():
   if '_pinky_' not in name:continue
   mat=wrist@frames[name]
   for v,n in meshes:
    v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];p=(v-[.60,-.25,.725])@axes.T;r=abs(axes)@np.array([.30,.40,.025]);values.append(float(np.maximum(p.min(0)-r,-r-p.max(0)).max()))
  return values
 def constraints(x):
  o,t,c=targets(x);values=[]
  for first,last in [(o,t),(t,c)]:
   for u in np.linspace(0,1,5):
    q=(1-u)*first+u*last;values.extend((np.asarray(table(q))-planning_table_clearance_m)*1000)
    values.extend((np.array([r['gap_lower_bound_m'] for r in g.self_gaps(q,'pinky',certify_clearance_m=.0001)])-.0001)*1000)
  return np.asarray(values)
 # Penalize moving the initial soft contact and changing its facing, rather
 # than pretending that the motor correction specifies a physical force.
 def pose(q):
  m=h.forward(q)['hand_r_pinky_pad_link'];return m[:3,:3]@h.contact_points['pinky']+m[:3,3],m[:3,0]
 before=[pose(opened),pose(touch),pose(close)]
 def objective(x):
  o,t,c=targets(x);value=np.sum(((x-start)/.025)**2)
  for q,(p,n) in zip([o,t,c],before):
   a,b=pose(q);value+=np.sum(((a-p)/.0007)**2)+np.sum(((b-n)/.1)**2)
  return float(value)
 fit=minimize(objective,start,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[{'type':'ineq','fun':constraints}],options={'maxiter':120,'ftol':1e-9})
 o,t,c=targets(fit.x);result['open_q']=o.tolist();result['touch_q']=t.tolist();result['close_q']=c.tolist()
 post=np.asarray(result['post_lift_close_q']);post[ids]=c[ids];result['post_lift_close_q']=post.tolist()
 for wp in result['close_waypoints']:
  if np.allclose(wp['q'],opened):wp['q']=o.tolist()
  if np.allclose(wp['q'],touch):wp['q']=t.tolist()
 result['close_waypoints'][-1]['q']=c.tolist()
 report=dict(planning_table_clearance_m=planning_table_clearance_m,passed=bool(constraints(fit.x).min()>=-1e-6),optimizer_success=bool(fit.success),message=str(fit.message),maximum_motor_change_rad=float(abs(fit.x-start).max()),pad_position_changes_m=[float(np.linalg.norm(pose(q)[0]-before[i][0])) for i,q in enumerate([o,t,c])],minimum_constraint_mm=float(constraints(fit.x).min()),scope='Two five-sample open/touch/close bounded pinky segments, original robot hull vertices retained; dense full-axis closure, approach, transfer and actual physics required. No force regulation or object repositioning.')
 result['initial_table_motor_projection']=report;return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();result=project(json.loads(a.plan.read_text()),json.loads(a.localization.read_text()));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result['initial_table_motor_projection']),flush=True);assert result['initial_table_motor_projection']['passed']
if __name__=='__main__':main()
