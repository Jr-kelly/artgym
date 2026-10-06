"""Arm and supported whole-table placement constrained broad palm pusher, fixed table."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);sp=a.output/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=16,knife_spec=sp);verts={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};print(list(verts),flush=True)
# Knife frame+y vertical. Orient hand finger axis toward world above table.
k=G2Kinematics();O=transform([.37,-.5695,.7541],(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());prior=json.load(open('runs/flat-table-20261006/preparation/palm-pusher-v43/candidate.json'));arm0,err=k.solve(O@np.array(prior['wrist_in_knife']));R=np.eye(3);q0=np.clip(np.array([1.3,0,1.3,1.3]*5),g.w.lower+.04,g.w.upper-.04);x0=np.r_[arm0,q0,[.37,-.5695]]
lo=np.r_[k.lower+.01,g.w.lower+.04,[.361,-.569]];hi=np.r_[k.upper-.01,g.w.upper-.04,[.75,.10]]
name='hand_r_base_link'
def decode(x):
 OO=O.copy();OO[:2,3]=x[27:29];W=np.linalg.inv(OO)@k.forward(x[:7]);return W,x[7:27]
def residual(x):
 W,q=decode(x);f=g.w.forward(q);r=[];vs=verts[name]@W[:3,:3].T+W[:3,3];weight=np.exp(-(vs[:,0]-vs[:,0].min())/.001);pt=weight@vs/weight.sum();r.extend((pt-[.010,.003,0])*150)
 # Broad horizontal support extent avoids single-cap torque.
 r.append(max(0,.050-(vs[:,2].max()-vs[:,2].min()))*100)
 for n,v in verts.items():
  M=W@f[n];vv=v@M[:3,:3].T+M[:3,3];r.append(max(0,-.002-vv[:,1].min())*400)
 for finger in ['index','middle','ring','pinky','thumb']:r.extend(min(0,v['gap_lower_bound_m']-.005)*150 for v in g.gaps(q,W,0.,finger))
 r.extend(min(0,v['gap_lower_bound_m']-.0002)*100 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0002));r.extend((x[7:27]-q0)*.002);r.extend((x[:7]-x0[:7])*.001);return np.asarray(r)
fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=160,diff_step=1e-5);W,q=decode(fit.x);f=g.w.forward(q);vs=verts[name]@W[:3,:3].T+W[:3,3];out=dict(wrist_in_knife=W.tolist(),arm_q=fit.x[:7].tolist(),hand_q=q.tolist(),physical_initial_xy=fit.x[27:29].tolist(),palm_min_x_m=float(vs[:,0].min()),palm_z_extent_m=[float(vs[:,2].min()),float(vs[:,2].max())],minimum_height_m=float(min((v@(W@f[n])[:3,:3].T+(W@f[n])[:3,3])[:,1].min()+.0041 for n,v in verts.items())),minimum_finger_knife_gap_m=min(v['gap_lower_bound_m'] for finger in ['index','middle','ring','pinky','thumb'] for v in g.gaps(q,W,0.,finger)),cost=fit.cost,scope=__doc__);(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q']}),flush=True)
