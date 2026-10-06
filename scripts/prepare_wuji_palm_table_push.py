"""Broad palm pushes knife sideways to original functional corner; finite motor path."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=json.load(open(a.source));W=np.array(s['wrist_in_knife']);O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());goal=O@W;axis=O[:3,0];above=goal.copy();above[:3,3]+=axis*.04;above[2,3]+=.12;side=above.copy();side[2,3]-=.12;pushed=goal.copy();pushed[:3,3]-=axis*.08485;release=pushed.copy();release[:3,3]+=axis*.045;retreat=release.copy();retreat[2,3]+=.18;outside=retreat.copy();outside[:2,3]=[.17,-.70]
ac=json.load(open('runs/newknife-20261005/preparation/capfront-v2/acquisition/acquisition-path.json'));end=np.array(ac['start_wrist_world']);turned=end.copy();turned[2,3]=outside[2,3];k=G2Kinematics();q,e=k.solve(above);print('above',e,flush=True);hq=np.array(s['hand_q']);rows=[];errors=[]
key=[(0,above),(1,above),(3,side),(4,goal),(8,pushed),(9,release),(11,retreat),(13,outside)]
for (ta,pa),(tb,pb) in zip(key[:-1],key[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);M=pa.copy();M[:3,3]=pa[:3,3]*(1-u)+pb[:3,3]*u;q,e=k.solve_near(M,q);errors.append(e);rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=hq.tolist()))
endq=np.array(ac['approach_q'][0]);highq,e=k.solve(turned,endq);opened=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'))['open_q'])
for t in np.arange(13,19,1/30):
 u=(t-13)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*highq).tolist(),hand_q=((1-u)*hq+u*opened).tolist()))
q=highq
for t in np.arange(19,23,1/30):
 u=(t-19)/4;u=u**3*(10-15*u+6*u*u);M=turned.copy();M[:3,3]=(1-u)*turned[:3,3]+u*end[:3,3];q,e=k.solve_near(M,q);errors.append(e);rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=opened.tolist()))
for t in np.arange(23,24+1/60,1/30):
 u=np.clip(t-23,0,1);u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*endq).tolist(),hand_q=opened.tolist()))
assert max(e['position_m'] for e in errors)<.005
out=dict(duration_s=24,pose_source='sim_oracle',physical_initial_xy=[.37,-.5695],physical_initial_yaw_deg=45,table_y_m=-.23,rows=rows,scope=__doc__,palm_geometry=s);(a.output/'prefix.json').write_text(json.dumps(out,indent=2));print('prepared',len(rows),flush=True)
