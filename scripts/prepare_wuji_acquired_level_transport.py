"""Rotate actual acquired clamp toward level functional operation; no release or physical reset."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import transform,G2Kinematics
out=Path('runs/flat-table-20261006/preparation/acquired-level-v113');out.mkdir();z=np.load('runs/flat-table-20261006/development/clamped-extraction-v104/simulation/trace.npz');i=np.argmin(abs(z['time']+1));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L=np.linalg.inv(O)@W;end=O.copy();end[:3,:3]=(Rotation.from_euler('z',58.47,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_matrix();end[:3,3]=[.36,-.49,1.0];slerp=Slerp([0,1],Rotation.from_matrix([O[:3,:3],end[:3,:3]]));k=G2Kinematics();aq=z['arm_q'][i].astype(float);old=json.load(open('runs/flat-table-20261006/preparation/clamped-extraction-v104/prefix.json'));rows=old['rows'].copy();motor=rows[-1]['hand_q'];errors=[]
for t in np.arange(47,53,1/30):
 u=(t-47)/6;u=u**3*(10-15*u+6*u*u);T=O.copy();T[:3,:3]=slerp(u).as_matrix();T[:3,3]=O[:3,3]*(1-u)+end[:3,3]*u;aq,e=k.solve_near(T@L,aq);errors.append(e);rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=motor))
for t in np.arange(53,56,1/30):rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=motor))
old.update(duration_s=56,rows=rows,scope=__doc__,expected_level_object=end.tolist(),actual_acquired_relative=L.tolist(),max_ik_error_m=max(e['position_m'] for e in errors),max_rotation_error_rad=max(e['rotation_rad'] for e in errors));(out/'prefix.json').write_text(json.dumps(old,indent=2));print(old['max_ik_error_m'],old['max_rotation_error_rad'],flush=True);assert old['max_ik_error_m']<.003 and old['max_rotation_error_rad']<.015
