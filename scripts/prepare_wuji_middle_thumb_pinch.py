"""Refine new middle/thumb opening for full path clearance, then finite motor prefix."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=json.load(open(a.source));W=np.array(s['wrist_in_knife']);closed=np.array(s['close_q']);opened=np.array(s['open_q']);g=DigitGeometry(max_face_axes=24,knife_spec=a.source.parent/'asset-spec.json');ids=np.r_[np.arange(4,8),np.arange(16,20)];verts={n:np.concatenate([v for v,_ in mesh]) for n,mesh in g.meshes.items()};names=['hand_r_middle_link4','hand_r_thumb_pad_link']
def residual(x):
 qo=closed.copy();qo[ids]=x;r=[]
 for u in [0,.25,.5,.75,1.]:
  q=qo*(1-u)+closed*u;f=g.w.forward(q)
  r.extend(min(0,v['gap_lower_bound_m']-.0002)*500 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0002))
  for n,vs in verts.items():
   mat=W@f[n];r.append(max(0,-.002-(vs@mat[:3,:3].T+mat[:3,3])[:,1].min())*350)
  if u==0:
   for n,sgn in zip(names,[1,-1]):
    mat=W@f[n];vs=verts[n]@mat[:3,:3].T+mat[:3,3];weights=np.exp(-(sgn*vs[:,0]-(sgn*vs[:,0]).min())/.0004);pt=weights@vs/weights.sum();r.extend((pt-[sgn*.014,.001,-.05])*120)
 r.extend((x-opened[ids])*.005);return np.array(r)
fit=least_squares(residual,opened[ids],bounds=(g.w.lower[ids]+.04,g.w.upper[ids]-.04),max_nfev=120,diff_step=1e-5);opened[ids]=fit.x;g=DigitGeometry(knife_spec=a.source.parent/'asset-spec.json');receipt=[]
for u in np.linspace(0,1,21):
 q=opened*(1-u)+closed*u;gap=g.self_gaps(q,'thumb',certify_clearance_m=.0001);receipt.append(dict(alpha=float(u),min_self_gap_m=min(r['gap_lower_bound_m'] for r in gap)))
s.update(open_q=opened.tolist(),opening_path_receipt=receipt);(a.output/'candidate.json').write_text(json.dumps(s,indent=2));print('min self',min(r['min_self_gap_m'] for r in receipt),flush=True)
# Keep uncertified geometry as planning evidence, never assume literal penetration.
if min(r['min_self_gap_m'] for r in receipt)<-.0001:raise SystemExit('opening path rejected')
O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());goal=O@W;above=goal.copy();above[2,3]+=.12;lift=goal.copy();lift[2,3]+=.18;k=G2Kinematics();q,e=k.solve(above);print('above',e,flush=True);rows=[];errors=[]
keys=[(0,above,opened),(2,above,opened),(6,goal,opened),(9,goal,closed),(15,lift,closed),(24,lift,closed)]
for (ta,pa,ha),(tb,pb,hb) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);p=pa.copy();p[:3,3]=(1-u)*pa[:3,3]+u*pb[:3,3];q,e=k.solve_near(p,q);errors.append(e);rows.append(dict(time_s=float(t),arm_q=q.tolist(),hand_q=((1-u)*ha+u*hb).tolist()))
rows.append(dict(time_s=24.,arm_q=q.tolist(),hand_q=closed.tolist()));assert max(e['position_m'] for e in errors)<.005
out=dict(duration_s=24.,physical_initial_xy=[.37,-.5695],physical_initial_yaw_deg=45.,table_y_m=-.23,pose_source='sim_oracle',rows=rows,scope=__doc__,geometry=s);(a.output/'prefix.json').write_text(json.dumps(out,indent=2));print('prepared',len(rows),flush=True)
