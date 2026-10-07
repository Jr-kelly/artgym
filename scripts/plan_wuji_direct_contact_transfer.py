"""Coordinate the acquired wrist and loaded nonthumb material contacts."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_direct_contact_prior import source_contacts
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--contact-geometry',action='store_true');p.add_argument('--thumb-height-m',type=float,default=.007);p.add_argument('--seed-candidate',type=Path);p.add_argument('--front-normal',action='store_true');p.add_argument('--support-links');p.add_argument('--pad-takeover',action='store_true');p.add_argument('--front-envelope',action='store_true');p.add_argument('--thumb-material',type=Path);p.add_argument('--strict-body-clearance',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();s=np.load(a.source/'takeover.npz');O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);q=s['robot_q'][7:].astype(float);F=g.w.forward(q);initialF=F;ids=np.r_[0:8,12:20];trial=Path(json.load(open(a.source/'manifest.json'))['source']).parent;native=[json.loads(l) for l in (trial/'wrap-contact-physical-steps.jsonl').open()];end=max(r['time_s'] for r in native);contacts={};normals={};points={}
trial,native,end=source_contacts(a.source)
thumb_prior=json.loads(a.thumb_material.read_text()) if a.thumb_material else None
fixed_parts=g.knife_geometry.collision_parts(float(s['slider_q']));g.knife_geometry.collision_parts=lambda ignored:fixed_parts
for n in (a.support_links.split(',') if a.support_links else ['hand_r_index_link2','hand_r_middle_pad_link','hand_r_ring_link4'] if a.front_normal else ['hand_r_index_link4','hand_r_middle_pad_link','hand_r_ring_pad_link']):
 C=[c for r in native if r['time_s']>end-.3 for c in r['contacts'] if c['hand_link']==n];m=np.mean([c['position_hand_link_m'] for c in C],0);contacts[n]=m;T=L@F[n];points[n]=T[:3,:3]@m+T[:3,3];normal=np.mean([c['force_normal_contribution_knife_N'] for c in C],0);normal/=np.linalg.norm(normal);normals[n]=T[:3,:3].T@normal
name='hand_r_thumb_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);weights=np.exp((V[:,0]-V[:,0].max())/.0004);frontM=weights@V/weights.sum();zcenter=-.026+float(s['slider_q']);margin=.08 if a.front_normal else .035;x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q[ids],zcenter];lo=np.r_[x0[:3]-(.055 if a.front_normal else .035),x0[3:6]-(1. if a.front_normal else .7),g.w.lower[ids]+margin,zcenter-.010];hi=np.r_[x0[:3]+(.055 if a.front_normal else .035),x0[3:6]+(1. if a.front_normal else .7),g.w.upper[ids]-margin,zcenter+.010]
def decode(x):
 l=transform(quaternion=Rotation.from_rotvec(x[3:6]).as_quat());l[:3,3]=x[:3];h=q.copy();h[ids]=x[6:-1];F=g.w.forward(h);T=l@F[name];vertices=V[V[:,0]>.005] if a.front_envelope else V;v=vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(v[:,1]-v[:,1].min())/.0002);P=T[:3,:3]@np.array(thumb_prior['material_point'])+T[:3,3] if thumb_prior else T[:3,:3]@frontM+T[:3,3] if a.front_normal and not a.front_envelope else w@v/w.sum();return l,h,F,P
def res(x):
 l,h,F,P=decode(x);r=[]
 for n,m in contacts.items():
  T=l@F[n];r.extend((T[:3,:3]@m+T[:3,3]-points[n])*300);r.extend((T[:3,:3]@normals[n]-(L@initialF[n])[:3,:3]@normals[n])*.3)
 r.extend((P-[0,a.thumb_height_m,x[-1]])*230);r.extend(((l@F[name])[:3,:3]@np.array(thumb_prior['local_normal'])-[0,-1,0])*1.6 if thumb_prior else ((l@F[name])[:3,0]-[0,-1,0])*(1.6 if a.front_normal else .3))
 if a.contact_geometry:
  for f in ['thumb','index','middle','ring']:
   for v in g.gaps(h,l,float(s['slider_q']),f):
    threshold=(.0015 if v['hand_link']!=name else -.0003 if v['knife_link']=='link_1' else .0003) if f=='thumb' and a.pad_takeover else .0002 if f=='thumb' else -.0005
    if a.strict_body_clearance and f!='thumb':threshold=-.00004 if v['hand_link'] in contacts else .0001
    r.append(min(0,v['gap_lower_bound_m']-threshold)*(1500 if a.strict_body_clearance and f!='thumb' else 500 if f=='thumb' else 200))
   r.extend(min(0,v['gap_lower_bound_m']-.0001)*150 for v in g.self_gaps(h,f,certify_clearance_m=.0001))
 r.extend((x-x0)*.015);return np.array(r)
seed=x0.copy()
if a.seed_candidate:
 old=json.load(a.seed_candidate.open());oldL=np.array(old['wrist_in_knife']);seed=np.r_[oldL[:3,3],Rotation.from_matrix(oldL[:3,:3]).as_rotvec(),np.array(old['hand_q'])[ids],old.get('thumb_target',[0,0,zcenter])[-1]]
b=time.time();fit=least_squares(res,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=130,diff_step=1e-5);l,h,F,P=decode(fit.x);arm,e=k.solve_near(O@l,s['robot_q'][:7].astype(float),max_step=1.);errors={n:float(np.linalg.norm((l@F[n])[:3,:3]@m+(l@F[n])[:3,3]-points[n])) for n,m in contacts.items()};out=dict(wrist_in_knife=l.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),arm_ik=e,thumb_point=P.tolist(),thumb_target=[0,a.thumb_height_m,float(fit.x[-1])],thumb_error_m=float(np.linalg.norm(P-[0,a.thumb_height_m,fit.x[-1]])),support_errors_m=errors,support_materials={n:m.tolist() for n,m in contacts.items()},support_points={n:m.tolist() for n,m in points.items()},self_intersections=HandIntersection().inspect(h),finger_gaps_m={f:g.minimum_gap(h,l,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']},elapsed_s=time.time()-b,scope='Trueactual supportmaterials; planonly, no accepted execution')
if a.front_envelope:out['thumb_material_point']=((l@F[name])[:3,:3].T@(P-(l@F[name])[:3,3])).tolist()
if thumb_prior:out['thumb_material_point']=thumb_prior['material_point'];out['thumb_surface_normal']=((l@F[name])[:3,:3]@np.array(thumb_prior['local_normal'])).tolist()
if a.strict_body_clearance:
 out['strict_body_clearance']=True
 out['support_points_achieved']={n:((l@F[n])[:3,:3]@m+(l@F[n])[:3,3]).tolist() for n,m in contacts.items()}
(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['hand_q','wrist_in_knife','support_materials','support_points']},flush=True);record('direct_contact_transfer_geometry',[str(a.output/'candidate.json')],config={k:out[k] for k in ['thumb_error_m','support_errors_m','arm_ik','self_intersections','finger_gaps_m']},next_step='Wholecontactfeasibility guides continuousgait; if unreachable revise actualgrip not pressure')
