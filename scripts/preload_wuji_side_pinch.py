"""Bounded inward virtual contact displacement with original finite PD."""
import json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
D=Path('runs/flat-table-20261006/preparation/side-pinch-v35');D.mkdir(parents=True,exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/side-pinch-v34/prefix.json'));g=DigitGeometry();base=json.load(open('runs/flat-table-20261006/preparation/side-pinch-v33/candidate.json'));W=np.array(base['wrist_in_knife']);q=np.array(base['close_q']);extra=np.zeros(20)
for finger,ids,sgn,name in [('index',np.arange(4),1,'hand_r_index_link4'),('thumb',np.arange(16,20),-1,'hand_r_thumb_pad_link')]:
 def value(a):
  mat=W@g.w.forward(a)[name];v=np.concatenate([v for v,n in g.meshes[name]])@mat[:3,:3].T+mat[:3,3];proj=v[:,0]*sgn;w=np.exp(-(proj-proj.min())/.0004);return w@v[:,0]/w.sum()
 j=[]
 for i in ids:
  plus=q.copy();minus=q.copy();plus[i]+=.0001;minus[i]-=.0001;j.append((value(plus)-value(minus))/.0002)
 j=np.array(j);dq=(-sgn*.004)*j/(j@j+1e-8);extra[ids]=np.clip(dq,-.15,.15)
print('offset',extra)
for row in s['rows']:
 t=row['time_s'];u=np.clip((t-7)/2,0,1);u=u**3*(10-15*u+6*u*u);row['hand_q']=np.clip(np.array(row['hand_q'])+u*extra,g.w.lower+.005,g.w.upper-.005).tolist()
s['scope']='Direct full-table side pinch, same clear opening then bounded4mm virtual inward preload (max.15rad), finite originalPD/torque; not calibrated force';s['preload_rad']=extra.tolist();(D/'prefix.json').write_text(json.dumps(s,indent=2))
