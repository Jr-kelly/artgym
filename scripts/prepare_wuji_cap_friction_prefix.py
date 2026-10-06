"""Actual reachable top-cap finite motor drag; full-supported flat start."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
p=Path('runs/flat-table-20261006/preparation/cap-friction-prefix-v88r1');p.mkdir(parents=True,exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/arm-cap-friction-v87/candidate.json'));k=G2Kinematics();O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());contact=k.forward(np.array(s['arm_q']));above=contact.copy();above[2,3]+=.12;press=contact.copy();press[2,3]-=.004;drag=press.copy();drag[:2,3]-=.06;lift=drag.copy();lift[2,3]+=.12;outside=lift.copy();outside[:2,3]=[.17,-.70];old=json.load(open('runs/flat-table-20261006/preparation/push-corner-v10/prefix.json'));q,er=k.solve(above,np.array(s['arm_q']));hq=np.array(s['hand_q']);rows=[];errors=[];keys=[(0,above),(1,above),(3,contact),(4,press),(9,drag),(11,lift),(13,outside)]
for (ta,A),(tb,B) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);M=A.copy();M[:3,3]=(1-u)*A[:3,3]+u*B[:3,3];q,e=k.solve_near(M,q);errors.append(e);
  if e['position_m']>.005:print('badsegment',ta,tb,t,e,flush=True);
  rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=hq.tolist(),ik=e))
endq=np.array(old['rows'][540]['arm_q']);endhq=np.array(old['rows'][540]['hand_q'])
for t in np.arange(13,19,1/30):
 u=(t-13)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*endq).tolist(),hand_q=((1-u)*hq+u*endhq).tolist()))
for row in old['rows'][540:]:
 rr=dict(row);rr['time_s']+=1;rows.append(rr)
print('maxerror',max(e['position_m'] for e in errors),flush=True)
assert max(e['position_m'] for e in errors)<.005
out=dict(duration_s=25,physical_initial_xy=[.37,-.5695],physical_initial_yaw_deg=45,table_y_m=-.23,pose_source='sim_oracle initial geometry, one postpush update',rows=rows,scope=__doc__,source=s,downmotor_preload_m=.004,max_ik_position_error_m=max(e['position_m'] for e in errors));(p/'prefix.json').write_text(json.dumps(out,indent=2));print(out['max_ik_position_error_m'])
