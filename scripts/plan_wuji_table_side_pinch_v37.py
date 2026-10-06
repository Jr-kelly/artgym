"""Development tabletop side pinch: estimated knife-frame contacts, original mesh/limits."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform,G2Kinematics
D=Path('runs/flat-table-20261006/preparation/side-pinch-v37');D.mkdir(parents=True,exist_ok=False)
g=DigitGeometry();m=json.load(open('runs/newknife-20261005/preparation/capfront-v2/motor-plan.json'));initial=np.array(m['close_q']);initial[4:16]=[.6,.3,.6,.6,1.1,-.3,1.3,1.3,1.1,.3,.6,1.3]
O=transform([.37,-.5695,.7541],Rotation.from_euler('z',45,degrees=True).as_quat())
O[:3,:3]=Rotation.from_euler('z',45,degrees=True).as_matrix()@Rotation.from_euler('x',90,degrees=True).as_matrix()
# Contact opposition across width, body tail. World table remains fixed.
ids=np.arange(20);verts={n:np.concatenate([v for v,nn in meshes]) for n,meshes in g.meshes.items()};names=['hand_r_index_link4','hand_r_thumb_pad_link']
initial[:4]=[.8,.2,.8,.5];initial[16:]=[1.2,.3,.5,.2];x0=np.r_[[0,.17,-.05],Rotation.from_matrix(np.array([[1,0,0],[0,0,-1],[0,1,0]])).as_rotvec(),initial[ids]]
lo=np.r_[[-.25,-.02,-.25],[-np.pi]*3,g.w.lower[ids]+.07];hi=np.r_[[.25,.25,.25],[np.pi]*3,g.w.upper[ids]-.07]
def decode(x):
 W=np.eye(4);W[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();W[:3,3]=x[:3];q=initial.copy();q[ids]=x[6:];return W,q
# Thumb on negative width face, index positive. Collision penalties against table plane.
def residual(x):
 W,q=decode(x);f=g.w.forward(q);r=[]
 for n,sgn in zip(names,[1,-1]):
  mat=W@f[n];v=verts[n]@mat[:3,:3].T+mat[:3,3];p=v[:,0]*sgn;weights=np.exp(-(p-p.min())/.0004);point=weights@v/weights.sum();r.extend((point-np.array([sgn*.0083,.001,-.058]))*150)
  hull=ConvexHull(verts[n]);normals=hull.equations[:,:3]@mat[:3,:3].T;centers=v[hull.simplices].mean(1);proj=centers[:,0]*sgn;fw=np.exp(-(proj-proj.min())/.001);face=fw@(normals@np.array([-sgn,0,0]))/fw.sum();r.append(max(0,.85-face)*3)
 for n,v in verts.items():
  mat=O@W@f[n];vv=v@mat[:3,:3].T+mat[:3,3];r.append(max(0,.7515-vv[:,2].min())*300)
 r.extend(min(0,v['gap_lower_bound_m']-.0005)*100 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0005));r.extend(min(0,v['gap_lower_bound_m']-.004)*200 for finger in ['middle','ring','pinky'] for v in g.gaps(q,W,0.,finger));r.extend((x[6:]-initial[ids])*.001);r.extend((x[:3]-x0[:3])*.01)
 return np.array(r)
fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=500,diff_step=1e-5);W,q=decode(fit.x);errors=residual(fit.x);out=dict(wrist_in_knife=W.tolist(),close_q=q.tolist(),max_contact_error_m=float(np.max(abs(errors[:6]))/150),min_plane_penalty_m=float(max(errors[6:6+len(verts)])/300),solver_cost=float(fit.cost),pose_source='estimated geometry only',scope=__doc__)
(D/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['wrist_in_knife','close_q']}))
