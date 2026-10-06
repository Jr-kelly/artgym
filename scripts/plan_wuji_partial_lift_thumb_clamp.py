"""Body-side opposition during robot-created v19 partial lift, offline motor IK."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
z=np.load('runs/flat-table-20261006/development/middle-curl-v19/simulation/trace.npz');sp=a.output/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})));g=DigitGeometry(max_face_axes=16,knife_spec=sp);v=np.concatenate([v for v,n in g.meshes['hand_r_thumb_pad_link']]);rows=[]
for t in [8.,9.,9.5,10.,10.5,11.,12.]:
 i=np.argmin(abs(z['time']-t));state=z['object'][i];O=transform(state[:3],state[3:7]);wr=z['wrist'][i];W=transform(wr[:3],wr[3:7]) if wr.shape in [(7,),(13,)] else wr;L=np.linalg.inv(O)@W;q=np.asarray(z['q'][i],dtype=float);prior=q[16:].copy()
 def point(x):
  qq=q.copy();qq[16:]=x;M=L@g.w.forward(qq)['hand_r_thumb_pad_link'];vv=v@M[:3,:3].T+M[:3,3];weights=np.exp(-(vv[:,0]-vv[:,0].min())/.0004);return weights@vv/weights.sum()
 def residual(x):
  qq=q.copy();qq[16:]=x
  return np.r_[(point(x)-[.0085,.001,-.051])*200,[min(0,r['gap_lower_bound_m']-.0001)*80 for r in g.self_gaps(qq,'thumb',certify_clearance_m=.0001)],(x-prior)*.005]
 fit=least_squares(residual,np.clip(prior,g.w.lower[16:]+.005,g.w.upper[16:]-.005),bounds=(g.w.lower[16:]+.005,g.w.upper[16:]-.005),max_nfev=100)
 rows.append(dict(time_s=t,thumb_q=fit.x.tolist(),contact_error_m=float(np.linalg.norm(point(fit.x)-[.0085,.001,-.051])),minimum_self_gap_m=min(r['gap_lower_bound_m'] for r in g.self_gaps(np.r_[q[:16],fit.x],'thumb',certify_clearance_m=.0001)),wrist_in_knife=L.tolist()))
 print(t,rows[-1]['contact_error_m'],rows[-1]['minimum_self_gap_m'],flush=True)
out=dict(rows=rows,scope=__doc__,source_trace_sha256=hashlib.sha256(Path('runs/flat-table-20261006/development/middle-curl-v19/simulation/trace.npz').read_bytes()).hexdigest());(a.output/'candidate.json').write_text(json.dumps(out,indent=2))
