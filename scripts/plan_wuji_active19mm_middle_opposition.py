"""New actual index-pad/slider grip, middle opposition to floor before more push/lift."""
import json,time,argparse,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_flat_table_event import record
ap=argparse.ArgumentParser();ap.add_argument('--side',action='store_true');ap.add_argument('--index-under',action='store_true');a=ap.parse_args()
p=Path('runs/flat-table-20261006/preparation/'+('active19mm-index-under-20261006' if a.index_under else 'active19mm-middle-side-opposition-20261006' if a.side else 'active19mm-middle-opposition-20261006'));p.mkdir();sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
s=np.load('runs/flat-table-20261006/recorded-active19mm-11p9s/takeover.npz');g=DigitGeometry(max_face_axes=6,knife_spec=sp);k=G2Kinematics();q0=s['robot_q'].astype(float);O=transform(s['object_state'][:3],s['object_state'][3:7]);inv=np.linalg.inv(O);contacts=json.load(open('runs/flat-table-20261006/recorded-active19mm-11p9s/native-contacts.json'))['contacts'];names=['hand_r_index_pad_link','hand_r_thumb_pad_link','hand_r_middle_pad_link'];materials=[];targets=[]
for n in names[:2]:
 c=next(c for c in contacts if c['hand_link']==n);materials.append(np.array(c['position_hand_link_m']));targets.append(np.array(c['position_knife_m']))
F=g.w.forward(q0[7:]);L0=inv@k.forward(q0[:7]);verts=np.concatenate([v for v,_ in g.meshes[names[2]]]);T=L0@F[names[2]];P=verts@T[:3,:3].T+T[:3,3];weights=np.exp(-(P[:,1].max()-P[:,1])/.0002);materials.append(weights@verts/weights.sum());targets.append(np.array([-.002,-.0042,.025]));indexrot=(L0@F[names[0]])[:3,:3];ids=np.r_[np.arange(7),np.arange(7,19),np.arange(23,27)];x0=q0[ids];lo=np.r_[k.lower,g.w.lower][ids]+.001;hi=np.r_[k.upper,g.w.upper][ids]-.001;V={n:np.concatenate([v for v,_ in ms]) for n,ms in g.meshes.items()}
if a.side:
 weights=np.exp(-(P[:,0]-P[:,0].min())/.0002);materials[-1]=weights@verts/weights.sum();targets[-1]=np.array([.0097,0.,.035])
if a.index_under:
 names=names[:2];materials=materials[:2];targets=targets[:2];under_target=np.array([-.002,-.0042,.015]);index_start=targets[0].copy();thumbrot=(L0@F[names[1]])[:3,:3]
def state(x):
 q=q0.copy();q[ids]=x;W=k.forward(q[:7]);F=g.w.forward(q[7:]);L=inv@W;pts=[(L@F[n])[:3,:3]@m+(L@F[n])[:3,3] for n,m in zip(names,materials)];return q,W,F,L,pts
start=state(x0)[-1][-1];x=np.clip(x0,lo+1e-7,hi-1e-7);rows=[dict(time_s=0.,arm_q=s['issued_target'][:7].tolist(),hand_q=s['issued_target'][7:].tolist())];ds=[];b=time.time()
for u in np.linspace(0,1,7 if a.index_under else 5 if a.side else 9):
 t=(1-u)*start+u*targets[-1]
 if a.index_under:
  ku=[0,.25,.5,.7,1.];kp=[index_start,np.array([-.016,.003,.068]),np.array([-.016,-.006,.065]),np.array([-.012,-.005,.015]),under_target];t=np.array([np.interp(u,ku,[p[j] for p in kp]) for j in range(3)])
 def r(z):
  q,W,F,L,pts=state(z);r=[]
  goals=[t,targets[1]] if a.index_under else targets[:2]+[t]
  for pt,goal in zip(pts,goals):r.extend((pt-goal)*350)
  if a.index_under:r.extend(Rotation.from_matrix(thumbrot.T@(L@F[names[1]])[:3,:3]).as_rotvec()*8)
  else:r.extend(Rotation.from_matrix(indexrot.T@(L@F[names[0]])[:3,:3]).as_rotvec()*10)
  for n,v in V.items():
   T=W@F[n];P=v@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17);r.append(max(0,.7501-P[inside,2].min())*200 if inside.any() else 0.)
  r.extend(min(0,c['gap_lower_bound_m']-.0002)*120 for c in g.self_gaps(q[7:],'index' if a.index_under else 'middle',.0002))
  for f in ['index','middle','thumb']:r.extend(min(0,c['gap_lower_bound_m']+.0003)*100 for c in g.gaps(q[7:],L,float(s['slider_q']),f) if c['hand_link'] not in names)
  r.extend((z-x0)*.01);return r
 fit=least_squares(r,x,bounds=(lo,hi),max_nfev=45,diff_step=1e-5);x=fit.x;q,W,F,L,pts=state(x);goals=[t,targets[1]] if a.index_under else targets[:2]+[t];errors=[float(np.linalg.norm(pt-goal)) for pt,goal in zip(pts,goals)];gap=min(c['gap_lower_bound_m'] for c in g.self_gaps(q[7:],'index' if a.index_under else 'middle',.0002));d=dict(fraction=float(u),errors_m=errors,middle_selfgap_m=gap);ds.append(d);print(json.dumps(d),flush=True);cmd=q+s['issued_target']-q0;rows.append(dict(time_s=float(1+u*6),arm_q=cmd[:7].tolist(),hand_q=cmd[7:].tolist()))
rows.append(dict(rows[-1],time_s=10.));result=dict(rows=rows,diagnostics=ds,materials=[m.tolist() for m in materials],targets=[t.tolist() for t in targets],elapsed_s=time.time()-b);(p/'path.json').write_text(json.dumps(result,indent=2));record('active19mm_middle_opposition_path_finished',[str(p/'path.json')],dict(final=ds[-1]),updates=dict(active_jobs=[]),next_step='Native middle if feasible; actualnewtopology beforetableunload.')
