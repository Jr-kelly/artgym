"""Actual flatpickup then robot deposits at original functional table corner, without physical-state reset."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import transform,G2Kinematics
from scripts.g2_knife_geometry import KnifeGeometry
out=Path('runs/flat-table-20261006/preparation/table-assisted-vertical-v119');out.mkdir();z=np.load('runs/flat-table-20261006/development/clamped-extraction-v104/simulation/trace.npz');i=np.argmin(abs(z['time']+1));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L=np.linalg.inv(O)@W;end=O.copy();end[:3,:3]=(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_matrix();end[:3,3]=[.31,-.6295,.7545];slerp=Slerp([0,1],Rotation.from_matrix([O[:3,:3],end[:3,:3]]));k=G2Kinematics();aq=z['arm_q'][i].astype(float);old=json.load(open('runs/flat-table-20261006/preparation/clamped-extraction-v104/prefix.json'));rows=old['rows'].copy();motor=np.array(rows[-1]['hand_q']);errors=[];G=KnifeGeometry('runs/flat-table-20261006/preparation/supported-cap-clamp-v101/asset-spec.json');V=np.concatenate([c['vertices'] for c in G.collision_parts(float(z['slider'][i]))]);dest=O.copy();dest[:2,3]=end[:2,3]
def add(t,T,hq):
 global aq
 aq,e=k.solve_near(T,aq);errors.append(e);rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=hq.tolist()))
for t in np.arange(47,51,1/30):
 u=(t-47)/4;u=u**3*(10-15*u+6*u*u);T=O.copy();T[:3,3]=O[:3,3]*(1-u)+dest[:3,3]*u;add(t,T@L,motor)
low=dest.copy();low[2,3]=.7505-float((V@low[:3,:3].T)[:,2].min())
for t in np.arange(51,54,1/30):
 u=(t-51)/3;u=u**3*(10-15*u+6*u*u);T=dest.copy();T[:3,3]=dest[:3,3]*(1-u)+low[:3,3]*u;add(t,T@L,motor)
for t in np.arange(54,60,1/30):add(t,low@L,motor)
lastW=k.forward(aq);up=lastW.copy();up[2,3]+=.16;opened=np.array(json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'))['open_q'])
for t in np.arange(60,64,1/30):
 u=(t-60)/4;u=u**3*(10-15*u+6*u*u);T=lastW.copy();T[:3,3]=lastW[:3,3]*(1-u)+up[:3,3]*u;add(t,T,motor*(1-u)+opened*u)
for t in np.arange(64,67,1/30):rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=opened.tolist()))
old.update(duration_s=67,rows=rows,scope=__doc__,stage_events=[dict(time_s=47,event='held_transport'),dict(time_s=54,event='table_supported_deposit'),dict(time_s=60,event='withdraw'),dict(time_s=67,event='actual_pose_regrasp')],max_ik_error_m=max(e['position_m'] for e in errors),max_rotation_error_rad=max(e['rotation_rad'] for e in errors));(out/'prefix.json').write_text(json.dumps(old,indent=2));print(old['max_ik_error_m'],old['max_rotation_error_rad']);assert old['max_ik_error_m']<.004
