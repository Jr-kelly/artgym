"""Retained acquired grasp, thumb from real cap material toward slider; reach diagnostic only."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.g2_contact_geometry import DigitGeometry
p=Path('runs/flat-table-20261006/preparation/acquired-thumb-slider-v115');p.mkdir();z=np.load('runs/flat-table-20261006/development/clamped-extraction-v104/simulation/trace.npz');i=np.argmin(abs(z['time']+1));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L=np.linalg.inv(O)@W;g=DigitGeometry(max_face_axes=12,knife_spec='runs/flat-table-20261006/preparation/supported-cap-clamp-v101/asset-spec.json');q=z['q'][i].astype(float);n='hand_r_thumb_pad_link';m=np.array([.00405569,-.00805529,-.00738926]);initial=q[16:].copy();rows=[]
for target in [np.array([-.008,.005,-.060]),np.array([-.008,.005,-.045]),np.array([0,.00615,-.026]),np.array([0,.00615,.009])]:
 def res(x):
  qq=q.copy();qq[16:]=x;T=L@g.w.forward(qq)[n];r=list((T[:3,:3]@m+T[:3,3]-target)*200);r.extend(min(0,s['gap_lower_bound_m']-.0002)*80 for s in g.self_gaps(qq,'thumb',certify_clearance_m=.0002));r.extend((x-initial)*.003);return np.array(r)
 f=least_squares(res,np.clip(initial,g.w.lower[16:]+.001,g.w.upper[16:]-.001),bounds=(g.w.lower[16:]+.001,g.w.upper[16:]-.001),max_nfev=150);initial=f.x;qq=q.copy();qq[16:]=f.x;T=L@g.w.forward(qq)[n];r=dict(target=target.tolist(),point_error_m=float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-target)),thumb_q=f.x.tolist(),min_self_gap_m=min(s['gap_lower_bound_m'] for s in g.self_gaps(qq,'thumb')));rows.append(r);print(json.dumps(r),flush=True)
(p/'reach.json').write_text(json.dumps(dict(rows=rows,scope=__doc__,wrist_in_knife=L.tolist()),indent=2))
