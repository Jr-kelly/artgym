"""Actual table-supported partialpickup feeds paired slider grip before final extraction; no state reset."""
import json,numpy as np
from pathlib import Path
from scripts.g2_kinematics import G2Kinematics,transform
out=Path('runs/flat-table-20261006/preparation/table-paired-v150');out.mkdir();z=np.load('runs/flat-table-20261006/development/selected-pickup-v123/simulation/trace.npz');i=np.argmin(abs(z['time']+7));O=transform(z['object'][i,:3],z['object'][i,3:7]);path=json.load(open('runs/flat-table-20261006/preparation/paired-contact-gait-v140/path.json'));held=np.array(path['object_world']);delta=O@np.linalg.inv(held);old=json.load(open('runs/flat-table-20261006/preparation/clamped-extraction-v104/prefix.json'));rows=[r for r in old['rows'] if r['time_s']<40];k=G2Kinematics();aq=np.array(rows[-1]['arm_q']);errors=[];rr=[]
for p in path['rows']:
 T=delta@k.forward(p['arm_q']);aq,e=k.solve_near(T,aq);errors.append(e);rr.append(dict(time_s=float(p['time_s']-7),arm_q=aq.tolist(),hand_q=p['hand_q']))
first=rr[0];start=rows[-1];rr=[r for i,r in enumerate(rr) if not i or r['time_s']>rr[i-1]['time_s']+.001]
for A,B in zip(rr[:-1],rr[1:]):
 for t in np.arange(A['time_s'],B['time_s']-1e-8,1/30):
  u=(t-A['time_s'])/(B['time_s']-A['time_s']);aq=np.array(A['arm_q'])*(1-u)+np.array(B['arm_q'])*u;hq=np.array(A['hand_q'])*(1-u)+np.array(B['hand_q'])*u;b=min(1,t-40);aq+=(np.array(start['arm_q'])-np.array(first['arm_q']))*(1-b);hq+=(np.array(start['hand_q'])-np.array(first['hand_q']))*(1-b);rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=hq.tolist()))
last=rr[-1];W=k.forward(last['arm_q']);lift=W.copy();lift[2,3]+=.18;aq=np.array(last['arm_q']);hq=last['hand_q']
for t in np.arange(52,58,1/30):
 u=(t-52)/6;u=u*u*u*(10-15*u+6*u*u);T=W.copy();T[:3,3]=W[:3,3]*(1-u)+lift[:3,3]*u;aq,e=k.solve_near(T,aq);errors.append(e);rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=hq))
for t in np.arange(58,61,1/30):rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=hq))
old.update(duration_s=61,rows=rows,scope=__doc__,max_ik_error_m=max(e['position_m'] for e in errors),max_rotation_error_rad=max(e['rotation_rad'] for e in errors));(out/'prefix.json').write_text(json.dumps(old,indent=2));print(old['max_ik_error_m'],old['max_rotation_error_rad']);assert old['max_ik_error_m']<.004
