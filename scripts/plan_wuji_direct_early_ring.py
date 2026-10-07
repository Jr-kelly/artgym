"""Early ring side support from actual newly lifted grasp, motor target only."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
s=np.load(a.source/'takeover.npz');g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();q=s['robot_q'][7:].astype(float);W=k.forward(s['robot_q'][:7]);O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@W;name='hand_r_ring_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]])
def decode(x):
 h=q.copy();h[12:16]=x[:4];F=g.w.forward(h);T=L@F[name];v=V@T[:3,:3].T+T[:3,3];weights=np.exp(-(v[:,0]-v[:,0].min())/.00025);P=weights@v/weights.sum();return h,F,T,P
def residual(x):
 h,F,T,P=decode(x);r=list((P-[.0085,x[4],x[5]])*250);r.extend((T[:3,0]-[-1,0,0])*.5)
 r.extend(min(0,z['gap_lower_bound_m']+(.0011 if z['hand_link'] in [name,'hand_r_ring_link4'] and z['knife_link']=='link_0' else -.0001))*300 for z in g.gaps(h,L,s['slider_q'],'ring'))
 r.extend(min(0,z['gap_lower_bound_m']-.0002)*150 for z in g.self_gaps(h,'ring',certify_clearance_m=.0002))
 for n,parts in g.meshes.items():
  if '_ring_' not in n:continue
  T=W@F[n]
  for v,_ in parts:r.append(min(0,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7502))*400)
 r.extend((x[:4]-q[12:16])*.02);return np.array(r)
lo=np.r_[g.w.lower[12:16]+.04,-.003,.0-.07];hi=np.r_[g.w.upper[12:16]-.04,.002,-.035];seed=np.r_[[.65,0,.8,.2],-.001,-.055]
record('direct_early_ring_geometry_started',[str(a.output)],config={'uncertainty':'Ring rightside truepad support atknife-tail beforemiddleloss, wholemesh clearoftable/otherdigits?','change':'Unused ring only, currentrealwrist andcarrier handfixed, trueenvelope contact1mmfinitepreload','decision':'Submmendpoint/tableclear/handself0 permits loaded6s acquisition; fixedwristunreachable changesgeometrynotangle scan'})
fit=least_squares(residual,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=120,diff_step=1e-5);h,F,T,P=decode(fit.x);selfbad=HandIntersection().inspect(h);table=[]
for n,parts in g.meshes.items():
 if '_ring_' not in n:continue
 for v,_ in parts:
  A=W@F[n];table.append(float((v@A[:3,:3].T+A[:3,3])[:,2].min()-.75))
diag=dict(contact_error_m=float(np.linalg.norm(P-[.0085,fit.x[4],fit.x[5]])),point=P.tolist(),ring_q=h[12:16].tolist(),normal=T[:3,0].tolist(),ring_table_min_clearance_m=min(table),self_intersections=selfbad)
rows=[];pathbad=[]
for t in np.linspace(0,6,25):
 u=smooth((t-.3)/3);cmd=s['issued_target'].copy();cmd[19:23]=(1-u)*cmd[19:23]+u*h[12:16];rows.append(dict(time_s=float(t),arm_q=cmd[:7].tolist(),hand_q=cmd[7:].tolist()));pathbad.extend(HandIntersection().inspect(cmd[7:]))
out=dict(rows=rows,source=str(a.source),diagnostics=diag,path_self_intersections=pathbad,scope='Actualearlylift wrist held andringonlymoves; original finite torques/contacts/gravity retained; notphysicalpass')
(a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps(diag));record('direct_early_ring_geometry_finished',[str(a.output/'motor.json')],config=diag,next_step='Inspectfullpathgeometry before nativeearlyring acquisition, otherwise change contacttopology')
