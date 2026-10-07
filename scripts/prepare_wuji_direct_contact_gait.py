"""Motor contact gait to a feasible thumb-clear endpoint, no physical setters."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--front-normal',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=np.load(a.source/'takeover.npz');c=json.load(a.candidate.open());g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);initialQ=s['robot_q'][7:].astype(float);initialL=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);endL=np.array(c['wrist_in_knife']);endQ=np.array(c['hand_q']);offset=s['issued_target'][7:]-initialQ;armoffset=s['issued_target'][:7]-s['robot_q'][:7];h=initialQ.copy();arm=s['robot_q'][:7].astype(float);name='hand_r_thumb_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);T=endL@g.w.forward(endQ)[name];Nend=T[:3,0];v=V@T[:3,:3].T+T[:3,3];w=np.exp((V[:,0]-V[:,0].max())/.0004) if a.front_normal else np.exp(-(v[:,1]-v[:,1].min())/.0002);m=w@V/w.sum();T=initialL@g.w.forward(initialQ)[name];Nstart=T[:3,0];P0=T[:3,:3]@m+T[:3,3];Pend=np.array(c['thumb_point']);Rdelta=Rotation.from_matrix(initialL[:3,:3].T@endL[:3,:3]).as_rotvec();rows=[];diagnostics=[];checker=HandIntersection();b=time.time()
if 'thumb_material_point' in c:
 m=np.array(c['thumb_material_point']);T=initialL@g.w.forward(initialQ)[name];P0=T[:3,:3]@m+T[:3,3]
if c.get('strict_body_clearance'):
 # Use the same conservative separating axes as this endpoint planner.
 # Different nonnested samples can lose a valid separating certificate.
 g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
initial_gaps={f:g.gaps(initialQ,initialL,float(s['slider_q']),f) for f in ['index','middle','ring','pinky']} if c.get('strict_body_clearance') else {}
for t in np.linspace(0,8,25):
 u=smooth((t-.5)/6);L=initialL.copy();L[:3,3]=(1-u)*initialL[:3,3]+u*endL[:3,3];L[:3,:3]=initialL[:3,:3]@Rotation.from_rotvec(Rdelta*u).as_matrix();errs={}
 active={n.split('_')[2] for n in c['support_materials']}
 for f in ['index','middle','ring','pinky']:
  if f not in active:
   ii=[g.w.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)];h[ii]=(1-u)*initialQ[ii]+u*endQ[ii]
 for n,material in c['support_materials'].items():
  f=n.split('_')[2];ids=[g.w.names.index('hand_r_'+f+'_joint'+str(j)) for j in range(1,5)];material=np.array(material);target=np.array(c.get('support_points_achieved',c['support_points'])[n]);T0=initialL@g.w.forward(initialQ)[n];target=(1-u)*(T0[:3,:3]@material+T0[:3,3])+u*target;seed=h[ids].copy();prior=(1-u)*initialQ[ids]+u*endQ[ids]
  def res(x):
   q=h.copy();q[ids]=x;T=L@g.w.forward(q)[n];r=list((T[:3,:3]@material+T[:3,3]-target)*300);r.extend((x-prior)*.02)
   if c.get('strict_body_clearance'):
    gaps=g.gaps(q,L,float(s['slider_q']),f)
    for gap,initial_gap in zip(gaps,initial_gaps[f]):
     endthreshold=-.00004 if gap['hand_link'] in c['support_materials'] else .0001
     threshold=(1-u)*min(endthreshold,initial_gap['gap_lower_bound_m'])+u*endthreshold
     r.append(min(0,gap['gap_lower_bound_m']-threshold)*1500)
   return np.array(r)
  fit=least_squares(res,np.clip(seed,g.w.lower[ids]+.025,g.w.upper[ids]-.025),bounds=(g.w.lower[ids]+.025,g.w.upper[ids]-.025),max_nfev=70);h[ids]=fit.x;errs[n]=float(np.linalg.norm(res(fit.x)[:3])/300)
 target=(1-u)*P0+u*Pend;target[1]+=.014*np.sin(np.pi*u);prior=(1-u)*initialQ[16:]+u*endQ[16:];seed=h[16:].copy()
 def res(x):
  q=h.copy();q[16:]=x;T=L@g.w.forward(q)[name];r=list((T[:3,:3]@m+T[:3,3]-target)*200);r.extend((x-prior)*.03)
  if a.front_normal:
   N=(1-u)*Nstart+u*Nend;N/=np.linalg.norm(N);r.extend((T[:3,0]-N)*1.5)
  r.extend(min(0,v['gap_lower_bound_m']+(.0007*(1-u)-.0001*u))*350 for v in g.gaps(q,L,float(s['slider_q']),'thumb'))
  r.extend(min(0,v['gap_lower_bound_m']-.0001)*130 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0001));return np.array(r)
 fit=least_squares(res,np.clip(seed,g.w.lower[16:]+.025,g.w.upper[16:]-.025),bounds=(g.w.lower[16:]+.025,g.w.upper[16:]-.025),max_nfev=90,diff_step=1e-5);h[16:]=fit.x
 expectedO=O@transform(quaternion=Rotation.from_euler('z',c.get('object_axial_leveling_degrees',0.)*u,degrees=True).as_quat())
 arm,e=k.solve_near(expectedO@L,arm,max_step=.15);cmd=h+offset;cmd[16:]=h[16:]+offset[16:]*(1-u);cmd=np.clip(cmd,g.w.lower,g.w.upper);rows.append(dict(time_s=float(t),arm_q=(arm+armoffset).tolist(),hand_q=cmd.tolist()));diagnostics.append(dict(time_s=float(t),fraction=float(u),support_errors_m=errs,arm_ik=e,thumb_target_error_m=float(np.linalg.norm(res(fit.x)[:3])/200),thumb_gap_m=g.minimum_gap(h,L,float(s['slider_q']),'thumb'),self_intersections=checker.inspect(h)));print(t,diagnostics[-1]['thumb_gap_m'],errs,flush=True)
out=dict(rows=rows,diagnostics=diagnostics,source=str(a.source),candidate=str(a.candidate),thumb_material=m.tolist(),elapsed_s=time.time()-b,scope='Retain loaded motoroffsets on nonthumb; thumb offset decays only while clearing actualknife;25knots not fullphysical acceptance');(a.output/'gait.json').write_text(json.dumps(out,indent=2));record('direct_contact_gait_prepared',[str(a.output/'gait.json')],config={'max_support_error_m':max(max(d['support_errors_m'].values()) for d in diagnostics),'min_thumb_gap_m':min(d['thumb_gap_m'] for d in diagnostics),'intersection_frames':sum(bool(d['self_intersections']) for d in diagnostics)},next_step='Only feasiblecontactpath executes shortnative8s; measure exactfirstlostsupport iffails')
