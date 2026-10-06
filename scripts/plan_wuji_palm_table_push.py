"""New palm face pusher: broad body side contact, all fingers above fixed table."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);sp=a.output/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=16,knife_spec=sp);verts={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};print(list(verts),flush=True)
# Knife frame+y vertical. Orient hand finger axis toward world above table.
R=np.array([[1,0,0],[0,0,1],[0,-1,0]]);q0=np.clip(np.array([1.3,0,1.3,1.3]*5),g.w.lower+.04,g.w.upper-.04);x0=np.r_[[.025,.04,0],Rotation.from_matrix(R).as_rotvec(),q0]
lo=np.r_[[-.15,-.02,-.15],[-np.pi]*3,g.w.lower+.04];hi=np.r_[[.15,.25,.15],[np.pi]*3,g.w.upper-.04]
name='hand_r_base_link'
def decode(x):
 W=np.eye(4);W[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();W[:3,3]=x[:3];return W,x[6:]
def residual(x):
 W,q=decode(x);f=g.w.forward(q);r=[];vs=verts[name]@W[:3,:3].T+W[:3,3];weight=np.exp(-(vs[:,0]-vs[:,0].min())/.001);pt=weight@vs/weight.sum();r.extend((pt-[.010,.003,0])*150)
 # Broad horizontal support extent avoids single-cap torque.
 r.append(max(0,.050-(vs[:,2].max()-vs[:,2].min()))*100)
 for n,v in verts.items():
  M=W@f[n];vv=v@M[:3,:3].T+M[:3,3];r.append(max(0,-.002-vv[:,1].min())*400)
 for finger in ['index','middle','ring','pinky','thumb']:r.extend(min(0,v['gap_lower_bound_m']-.005)*150 for v in g.gaps(q,W,0.,finger))
 r.extend(min(0,v['gap_lower_bound_m']-.0002)*100 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0002));r.extend((x[6:]-q0)*.002);r.extend((x[:6]-x0[:6])*.001);return np.asarray(r)
fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=160,diff_step=1e-5);W,q=decode(fit.x);f=g.w.forward(q);vs=verts[name]@W[:3,:3].T+W[:3,3];out=dict(wrist_in_knife=W.tolist(),hand_q=q.tolist(),palm_min_x_m=float(vs[:,0].min()),palm_z_extent_m=[float(vs[:,2].min()),float(vs[:,2].max())],minimum_height_m=float(min((v@(W@f[n])[:3,:3].T+(W@f[n])[:3,3])[:,1].min()+.0041 for n,v in verts.items())),minimum_finger_knife_gap_m=min(v['gap_lower_bound_m'] for finger in ['index','middle','ring','pinky','thumb'] for v in g.gaps(q,W,0.,finger)),cost=fit.cost,scope=__doc__);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q']}),flush=True)
