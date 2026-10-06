"""Real flat prefix followed by opposing cap clamp and lift; finite motor targets only."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import WujiKinematics
out=Path('runs/flat-table-20261006/preparation/supported-cap-prefix-v102');out.mkdir(exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/supported-cap-clamp-v101/candidate.json'));old=json.load(open('runs/flat-table-20261006/preparation/axial-end-prefix-v96/prefix.json'));k=G2Kinematics();h=WujiKinematics();arm=np.array(s['arm_q']);q=np.array(s['hand_q']);W=k.forward(arm);O=np.array(s['object_world']);materials=[np.array(p) for p in s['material_points']];names=s['active_links'];targets=np.array(s['targets']);L=np.linalg.inv(O)@W
# Open thumb by20mm above actual solidcap; then inward motor compression2mm on both actual material faces.
def fingers(targets,seed):
 def r(x):
  F=h.forward(x);v=[]
  for n,m,t in zip(names,materials,targets):
   T=L@F[n];v.extend((T[:3,:3]@m+T[:3,3]-t)*150)
  v.extend((x-seed)*.005);return np.array(v)
 fit=least_squares(r,np.clip(seed,h.lower+.001,h.upper-.001),bounds=(h.lower+.001,h.upper-.001),max_nfev=100);return fit.x
openedtargets=targets.copy();openedtargets[1,1]+=.020;opened=fingers(openedtargets,q);pressed=targets.copy();pressed[0,1]+=.002;pressed[1,1]-=.002;closed=fingers(pressed,q);rows=old['rows'].copy();prev=np.array(rows[-1]['arm_q']);prevhand=np.array(rows[-1]['hand_q']);outside=W.copy();outside[0,3]-=.08;above=outside.copy();above[2,3]+=.15;aq,e=k.solve(above,prev);errors=[e]
for t in np.arange(24,27,1/30):
 u=(t-24)/3;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*prev+u*aq).tolist(),hand_q=((1-u)*prevhand+u*opened).tolist()))
keys=[(27,above),(30,outside),(33,W),(36,W)];qarm=aq
for (ta,A),(tb,B) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);T=A.copy();T[:3,3]=A[:3,3]*(1-u)+B[:3,3]*u;qarm,e=k.solve_near(T,qarm);errors.append(e);hq=opened.copy() if ta<33 else opened*(1-u)+closed*u;rows.append(dict(time_s=float(t),arm_q=qarm.tolist(),hand_q=hq.tolist()))
lift=W.copy();lift[2,3]+=.12
for t in np.arange(36,40,1/30):
 u=(t-36)/4;u=u**3*(10-15*u+6*u*u);T=W.copy();T[:3,3]=W[:3,3]*(1-u)+lift[:3,3]*u;qarm,e=k.solve_near(T,qarm);errors.append(e);rows.append(dict(time_s=float(t),arm_q=qarm.tolist(),hand_q=closed.tolist()))
for t in np.arange(40,43,1/30):rows.append(dict(time_s=float(t),arm_q=qarm.tolist(),hand_q=closed.tolist()))
old.update(rows=rows,duration_s=43,scope=__doc__,actual_v97_pose_prior=True,no_stage_state_reset=True,operation_connected=False,contact_plan=s,max_ik_error_m=max(e['position_m'] for e in errors));(out/'prefix.json').write_text(json.dumps(old,indent=2));print(old['max_ik_error_m']);assert old['max_ik_error_m']<.003
