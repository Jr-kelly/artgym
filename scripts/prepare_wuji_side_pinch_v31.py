"""Turn side-pinch geometry into finite motor approach/close/lift prefix."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision
D=Path('runs/flat-table-20261006/preparation/side-pinch-v31');s=json.load(open(D/'candidate.json'));g=DigitGeometry();k=G2Kinematics();W=np.array(s['wrist_in_knife']);closed=np.array(s['close_q']);opened=closed.copy()
for finger,ids,sgn in [('index',np.arange(4),1),('thumb',np.arange(16,20),-1)]:
 name='hand_r_index_link4' if finger=='index' else 'hand_r_thumb_pad_link';p0=(W@g.w.forward(closed)[name])[:3,3];target=p0+np.array([sgn*.008,.002,0])
 def res(x):
  q=closed.copy();q[ids]=x;p=(W@g.w.forward(q)[name])[:3,3];return np.r_[(p-target)*100,(x-closed[ids])*.001]
 fit=least_squares(res,closed[ids],bounds=(g.w.lower[ids]+.005,g.w.upper[ids]-.005),max_nfev=200);opened[ids]=fit.x
O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());goal=O@W;above=goal.copy();above[2,3]+=.12;lift=goal.copy();lift[2,3]+=.18
q,e=k.solve(above);print('aboveIK',e);table=ArmTableCollision(.75,margin=0,table_y=-.23);rows=[];errors=[]
key=[(0,above,opened),(2,above,opened),(6,goal,opened),(9,goal,closed),(15,lift,closed),(24,lift,closed)]
for (ta,pa,ha),(tb,pb,hb) in zip(key[:-1],key[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);p=pa.copy();p[:3,3]=(1-u)*pa[:3,3]+u*pb[:3,3];q,e=k.solve_near(p,q);errors.append(e);h=(1-u)*ha+u*hb;rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=h.tolist()))
rows.append(dict(time_s=24.,arm_q=q.tolist(),hand_q=closed.tolist()));assert max(e['position_m'] for e in errors)<.005
r=dict(duration_s=24,pose_source='sim_oracle',physical_initial_xy=[.37,-.5695],physical_initial_yaw_deg=45,table_y_m=-.23,rows=rows,scope='New direct tabletop two-pad side pinch and lift; motor targets only, no object state setter',geometry=s,maximum_ik_position_error_m=max(e['position_m'] for e in errors));(D/'prefix.json').write_text(json.dumps(r,indent=2));print('planned',len(rows),'finalarm',q,'armtable',table.collisions(q))
