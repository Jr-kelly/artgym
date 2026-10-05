"""Known-pose two-fingertip lateral table translation; motor targets only."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
D=Path('runs/flat-table-20261006/preparation/push-v2');D.mkdir(parents=True,exist_ok=False)
k=G2Kinematics();g=DigitGeometry();a=json.load(open('runs/newknife-20261005/preparation/capfront-v2/acquisition/acquisition-path.json'))
qhand=np.clip(np.zeros(20),g.w.lower,g.w.upper);qhand[4]=.09;direction=np.array([1.,1.,0.])/np.sqrt(2);axis=np.array([1.,-1.,0.])/np.sqrt(2)
rot=np.column_stack([direction,axis,[0,0,-1]])
# Entire 144x19mm body rests inside fixed original table bounds.
center=np.array([.37,-.5695,.7541]);goal=np.eye(4);goal[:3,:3]=rot;goal[:3,3]=center+direction*.047+axis*(-.022);goal[2,3]=.7515+.1932
above=goal.copy();above[2,3]+=.075
pushed=goal.copy();pushed[:3,3]-=direction*(.06*np.sqrt(2)+.037)
release=pushed.copy();release[:3,3]+=direction*.045
retreat=release.copy();retreat[2,3]+=.10
end=np.array(a['start_wrist_world']);q0,e=k.solve(above,np.array(a['approach_q'][0]));assert e['position_m']<.001,e
key=[(0,above),(1,above),(3,goal),(7,pushed),(8,release),(9,retreat),(12,end)]
rows=[];q=q0
for (ta,pa),(tb,pb) in zip(key[:-1],key[1:]):
 slerp=Slerp([0,1],Rotation.from_matrix([pa[:3,:3],pb[:3,:3]]))
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u*u*u*(10-15*u+6*u*u);p=pa.copy();p[:3,3]=(1-u)*pa[:3,3]+u*pb[:3,3];p[:3,:3]=slerp(u).as_matrix();q,e=k.solve_near(p,q)
  assert e['position_m']<.002,(t,e)
  h=qhand if t<9 else qhand+u*(np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'))['open_q'])-qhand)
  rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=h.tolist(),ik=e))
rows.append(dict(time_s=12.,arm_q=a['approach_q'][0],hand_q=json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'))['open_q']))
out=dict(duration_s=12,pose_source='sim_oracle',physical_initial_xy=center[:2].tolist(),physical_initial_yaw_deg=45,table_y_m=-.23,rows=rows,scope='Open finger side push then withdraw; expected end placement is unverified, no object state setter')
(D/'prefix.json').write_text(json.dumps(out,indent=2));print(D)
