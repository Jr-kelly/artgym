"""Move inactive middle/ring/pinky away from active pinch and table."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
D=Path('runs/flat-table-20261006/preparation/side-pinch-v32');D.mkdir(parents=True,exist_ok=False);s=json.load(open('runs/flat-table-20261006/preparation/side-pinch-v31/candidate.json'));g=DigitGeometry(max_face_axes=16);q=np.array(s['close_q']);W=np.array(s['wrist_in_knife']);O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());ids=np.arange(4,16);prior=q[ids].copy()
def residual(x):
 a=q.copy();a[ids]=x;frames=g.w.forward(a);r=[]
 for finger in ['middle','ring','pinky']:
  gaps=g.self_gaps(a,finger,certify_clearance_m=.001);r.extend(min(0,v['gap_lower_bound_m']-.001)*100 for v in gaps)
 for n,meshes in g.meshes.items():
  if not any(f in n for f in ['middle','ring','pinky']):continue
  mat=O@W@frames[n]
  for v,nn in meshes:
   vv=v@mat[:3,:3].T+mat[:3,3];r.append(max(0,.752-vv[:,2].min())*200)
 r.extend((x-prior)*.002);return np.array(r)
r=least_squares(residual,prior,bounds=(g.w.lower[ids]+.005,g.w.upper[ids]-.005),diff_step=1e-5,max_nfev=150);q[ids]=r.x;s['close_q']=q.tolist();s['inactive_clearance_cost']=float(r.cost);s['inactive_scope']=__doc__; (D/'candidate.json').write_text(json.dumps(s,indent=2));print('cost',r.cost,'q',q[ids])
