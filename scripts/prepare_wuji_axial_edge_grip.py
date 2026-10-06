"""Positive rail-end axial normal push, free wrist twist; original fullflat start."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
p=Path('runs/flat-table-20261006/preparation/axial-end-long-prefix-v99');p.mkdir(parents=True,exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/axial-end-push-v95/candidate.json'));k=G2Kinematics();h=WujiKinematics();q=np.array(s['arm_q']);hq=np.array(s['hand_q']);F=h.forward(hq)[s['material_link']];point=F[:3,:3]@np.array(s['material_point'])+F[:3,3];normal=F[:3,0];desired_normal=k.forward(q)[:3,:3]@normal;start=k.forward(q)[:3,:3]@point+k.forward(q)[:3,3];above=start.copy();above[2]+=.12;press=start.copy();press[:3]-=k.forward(q)[:3,:3]@normal*.004;drag=press.copy();drag[:3]-=(k.forward(q)[:3,:3]@normal)*.120;release=drag.copy();release[2]+=.16;rows=[];errors=[]
def solve(target,seed):
 def res(x):
  W=k.forward(x);P=W[:3,:3]@point+W[:3,3];N=W[:3,:3]@normal;return np.r_[(P-target)*100,(N-desired_normal)*2,(x-seed)*.002]
 fit=least_squares(res,np.clip(seed,k.lower+.0001,k.upper-.0001),bounds=(k.lower+.0001,k.upper-.0001),max_nfev=65);W=k.forward(fit.x);return fit.x,dict(position_m=float(np.linalg.norm(W[:3,:3]@point+W[:3,3]-target)),normal_error=float(np.linalg.norm(W[:3,:3]@normal-desired_normal)))
q,e=solve(above,q);keys=[(0,above),(1,above),(3,start),(4,press),(9,drag),(12,release)]
for (ta,A),(tb,B) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);target=(1-u)*A+u*B;q,e=solve(target,q);errors.append(e);rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=hq.tolist(),contact_ik=e))
old=json.load(open('runs/flat-table-20261006/preparation/push-corner-v10/prefix.json'));endq=np.array(old['rows'][540]['arm_q']);endhq=np.array(old['rows'][540]['hand_q'])
for t in np.arange(12,18,1/30):
 u=(t-12)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*endq).tolist(),hand_q=((1-u)*hq+u*endhq).tolist()))
rows+=old['rows'][540:];out=dict(duration_s=24,physical_initial_xy=[.37,-.5695],physical_initial_yaw_deg=45,table_y_m=-.23,pose_source='sim_oracle initial',rows=rows,scope=__doc__,max_position_error_m=max(x['position_m'] for x in errors),max_normal_error=max(x['normal_error'] for x in errors),source=s);(p/'prefix.json').write_text(json.dumps(out,indent=2));print(out['max_position_error_m'],out['max_normal_error'],flush=True);assert out['max_position_error_m']<.002
