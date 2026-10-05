"""Central side push with pad above table and motor-only high branch transfer."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
D=Path('runs/flat-table-20261006/preparation/push-v4');D.mkdir(parents=True,exist_ok=False)
k=G2Kinematics();g=DigitGeometry();a=json.load(open('runs/newknife-20261005/preparation/capfront-v2/acquisition/acquisition-path.json'))
qhand=np.clip(np.zeros(20),g.w.lower,g.w.upper);qhand[[0,8,12]]=1.1
direction=np.array([1.,1.,0.])/np.sqrt(2);axis=np.array([1.,-1.,0.])/np.sqrt(2);rot=np.column_stack([direction,axis,[0,0,-1]])
center=np.array([.37,-.5695,.7541]);goal=np.eye(4);goal[:3,:3]=rot;goal[:3,3]=center+direction*.047+axis*(-.00746);goal[2,3]=.9465
above=goal.copy();above[2,3]+=.075
pushed=goal.copy();pushed[:3,3]-=direction*(.06*np.sqrt(2)+.044)
release=pushed.copy();release[:3,3]+=direction*.05
retreat=release.copy();retreat[2,3]+=.18
outside=retreat.copy();outside[:2,3]=[.17,-.70]
end=np.array(a['start_wrist_world']);turned=end.copy();turned[2,3]=outside[2,3]
q,e=k.solve(above,np.array(a['approach_q'][0]));rows=[]
key=[(0,above),(1,above),(3,goal),(7,pushed),(8,release),(10,retreat),(12,outside)]
for (ta,pa),(tb,pb) in zip(key[:-1],key[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);p=pa.copy();p[:3,3]=(1-u)*pa[:3,3]+u*pb[:3,3];q,e=k.solve_near(p,q);assert e['position_m']<.002
  rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=qhand.tolist(),ik=e))
# Change redundant branch outside the table, then use old certified branch.
endq=np.array(a['approach_q'][0]);highq,e=k.solve(turned,endq);openq=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'))['open_q'])
for t in np.arange(12,18,1/30):
 u=(t-12)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*highq).tolist(),hand_q=((1-u)*qhand+u*openq).tolist()))
q=highq
for t in np.arange(18,22,1/30):
 u=(t-18)/4;u=u**3*(10-15*u+6*u*u);p=turned.copy();p[:3,3]=(1-u)*turned[:3,3]+u*end[:3,3];q,e=k.solve_near(p,q);rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=openq.tolist(),ik=e))
# Preserve branch; no cached joint state write.
for t in np.arange(22,24+1/60,1/30):
 u=np.clip((t-22)/2,0,1);u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*q+u*endq).tolist(),hand_q=openq.tolist()))
out=dict(duration_s=24,pose_source='sim_oracle',physical_initial_xy=center[:2].tolist(),physical_initial_yaw_deg=45,table_y_m=-.23,rows=rows,scope='Motor targets only; centered side pad raised 4mm to avoid roll; high outside branch transition. Actual displacement unverified.')
(D/'prefix.json').write_text(json.dumps(out,indent=2));print(D)
