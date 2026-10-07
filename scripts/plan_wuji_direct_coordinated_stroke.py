"""Joint wrist/hand stroke from this route's genuine pad and support contacts."""
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
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--material',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--arm-coordination',action='store_true');p.add_argument('--slide-index-material',action='store_true');p.add_argument('--support-links');p.add_argument('--approach-cap',action='store_true');p.add_argument('--strict-body-clearance',action='store_true');p.add_argument('--thumb1-upper',type=float);p.add_argument('--thumb3-lower',type=float);p.add_argument('--support-axial-range-m',type=float,default=0.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=np.load(a.source/'takeover.npz');cfg=json.load(a.material.open());g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);q=s['robot_q'][7:].astype(float);F0=g.w.forward(q);ids=np.r_[0:8,12:20];trial=Path(json.load(open(a.source/'manifest.json'))['source']).parent;native=[json.loads(l) for l in (trial/'wrap-contact-physical-steps.jsonl').open()];end=max(r['time_s'] for r in native);materials={};points={};normals={}
trial,native,end=source_contacts(a.source)
acquired_nonthumb={c['hand_link'] for r in native if r['time_s']>end-.3 for c in r['contacts'] if c['knife_link']=='link_0' and '_thumb_' not in c['hand_link']}
preserve_acquired=cfg.get('preserve_acquired_body_gaps',False)
initial_gaps={f:g.gaps(q,L,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']} if preserve_acquired else {}
for n in a.support_links.split(',') if a.support_links else ['hand_r_index_link2','hand_r_middle_pad_link','hand_r_ring_pad_link']:
 C=[c for r in native if r['time_s']>end-.3 for c in r['contacts'] if c['hand_link']==n];m=np.mean([c['position_hand_link_m'] for c in C],0);T=L@F0[n];materials[n]=m;points[n]=T[:3,:3]@m+T[:3,3];N=np.mean([c['force_normal_contribution_knife_N'] for c in C],0);N/=np.linalg.norm(N);normals[n]=(T[:3,:3].T@N,N)
name='hand_r_thumb_pad_link';m=np.array(cfg['material_point']);T=L@F0[name];P0=T[:3,:3]@m+T[:3,3];C=[c for r in native if r['time_s']>end-.3 for c in r['contacts'] if c['hand_link']==name and c['knife_link']=='link_1']
if 'local_normal' in cfg:thumbNormal=np.array(cfg['local_normal'])
else:
 N=np.mean([c['force_normal_contribution_knife_N'] for c in C],0);N/=np.linalg.norm(N);thumbNormal=T[:3,:3].T@N
stroke=cfg['stroke_m'];thumbTarget=np.array([0,cfg.get('cap_target_y_m',.007),cfg.get('cap_target_z_offset_m',-.026)+float(s['slider_q'])]) if a.approach_cap else P0+[0,0,stroke];x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q[ids]];lo=np.r_[x0[:3]-.06,x0[3:6]-.8,g.w.lower[ids]+.04];hi=np.r_[x0[:3]+.06,x0[3:6]+.8,g.w.upper[ids]-.04];base=6
fixedparts=g.knife_geometry.collision_parts(float(s['slider_q'])+stroke);g.knife_geometry.collision_parts=lambda ignored:fixedparts
if a.arm_coordination:
 base=7;x0=np.r_[s['robot_q'][:7],q[ids]];lo=np.r_[np.maximum(k.lower+.025,s['robot_q'][:7]-.6),g.w.lower[ids]+.04];hi=np.r_[np.minimum(k.upper-.025,s['robot_q'][:7]+.6),g.w.upper[ids]-.04]
 if cfg.get('arm_search_range_rad') is not None:
  distance=float(cfg['arm_search_range_rad']);lo[:7]=np.maximum(k.lower+.06,s['robot_q'][:7]-distance);hi[:7]=np.minimum(k.upper-.06,s['robot_q'][:7]+distance)
if cfg.get('planning_hand_margin_rad'):
 lo[base:base+len(ids)]=g.w.lower[ids]+cfg['planning_hand_margin_rad']
 hi[base:base+len(ids)]=g.w.upper[ids]-cfg['planning_hand_margin_rad']
if cfg.get('planning_thumb_margin_rad') is not None:
 for index in range(16,20):
  j=base+list(ids).index(index)
  lo[j]=g.w.lower[index]+cfg['planning_thumb_margin_rad']
  hi[j]=g.w.upper[index]-cfg['planning_thumb_margin_rad']
if a.thumb1_upper is not None:hi[base+list(ids).index(16)]=a.thumb1_upper
if a.thumb3_lower is not None:lo[base+list(ids).index(18)]=a.thumb3_lower
for index in cfg.get('preserve_acquired_spread_joint_indices',[]):
 j=base+list(ids).index(index)
 lo[j]=max(lo[j],q[index]-.005);hi[j]=min(hi[j],q[index]+.005)
for index in cfg.get('fixed_hand_joint_indices',[]):
 if index in ids:
  j=base+list(ids).index(index);lo[j]=q[index]-1e-6;hi[j]=q[index]+1e-6
support_material_bases={}
for n in cfg.get('slide_support_materials',[]):
 from scipy.spatial import ConvexHull
 Vsupport=np.concatenate([v for v,_ in g.meshes[n]])
 Hsupport=ConvexHull(Vsupport).equations
 face=int(np.argmax(Hsupport[:,:3]@normals[n][0]))
 support_material_bases[n]=(len(x0),Hsupport,face)
 foot=materials[n]-Hsupport[face,:3]*(Hsupport[face,:3]@materials[n]+Hsupport[face,3])
 x0=np.r_[x0,foot];lo=np.r_[lo,np.maximum(Vsupport.min(0),materials[n]-.006)];hi=np.r_[hi,np.minimum(Vsupport.max(0),materials[n]+.006)]
thumb_material_base=None
if cfg.get('slide_thumb_material',False):
 from scipy.spatial import ConvexHull
 Vthumb=np.concatenate([v for v,_ in g.meshes[name]])
 Hthumb=ConvexHull(Vthumb).equations
 thumbface=int(np.argmax(Hthumb[:,:3]@thumbNormal))
 thumbNormal=Hthumb[thumbface,:3].copy()
 thumb_material_base=len(x0)
 foot=m-thumbNormal*(thumbNormal@m+Hthumb[thumbface,3])
 x0=np.r_[x0,foot];lo=np.r_[lo,Vthumb.min(0)];hi=np.r_[hi,Vthumb.max(0)]
if a.slide_index_material:
 from scipy.spatial import ConvexHull
 index='hand_r_index_link2';V=np.concatenate([v for v,_ in g.meshes[index]]);H=ConvexHull(V).equations;M0=materials[index];face=int(np.argmax(H[:,:3]@M0+H[:,3]));x0=np.r_[x0,M0];lo=np.r_[lo,np.maximum(V.min(0),M0-.02)];hi=np.r_[hi,np.minimum(V.max(0),M0+.02)]
def decode(x):
 if a.arm_coordination:l=np.linalg.inv(O)@k.forward(x[:7])
 else:l=transform(quaternion=Rotation.from_rotvec(x[3:6]).as_quat());l[:3,3]=x[:3]
 h=q.copy();h[ids]=x[base:base+len(ids)];return l,h,g.w.forward(h)
def res(x):
 l,h,F=decode(x);r=[]
 transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in parts] for n,parts in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])};spheres={}
 for n,parts in transformed.items():
  for j,(v,_) in enumerate(parts):
   centre=v.mean(0);spheres[n,j]=(centre,np.linalg.norm(v-centre,axis=1).max())
 for n,mat in materials.items():
  if a.slide_index_material and n==index:mat=x[-3:]
  if n in support_material_bases:
   j,Hs,face=support_material_bases[n];mat=x[j:j+3]
   values=Hs[:,:3]@mat+Hs[:,3];r.extend(np.maximum(values,0)*1500);r.append(values[face]*1500)
  T=l@F[n];delta=T[:3,:3]@mat+T[:3,3]-points[n]
  if a.support_axial_range_m:
   # Retain the acquired side surface, allowing bounded longitudinal rolling
   # instead of treating a frictional contact as a welded material point.
   r.extend(delta[:2]*300);r.append(delta[2]*20)
   r.append(max(0.,abs(delta[2])-a.support_axial_range_m)*1500)
  else:r.extend(delta*300)
  local,initial=normals[n];r.extend((T[:3,:3]@local-initial)*.15)
 if a.slide_index_material:
  value=H[:,:3]@x[-3:]+H[:,3];r.extend(np.maximum(value-.00004,0)*400);r.append(value[face]*200)
 T=l@F[name];thumbmat=m if thumb_material_base is None else x[thumb_material_base:thumb_material_base+3]
 r.extend((T[:3,:3]@thumbmat+T[:3,3]-thumbTarget)*270)
 if cfg.get('thumb_normal_cone_cosine') is None:r.extend((T[:3,:3]@thumbNormal-[0,-1,0])*.8)
 else:r.append(max(0.,cfg['thumb_normal_cone_cosine']+(T[:3,:3]@thumbNormal)[1])*.8)
 if thumb_material_base is not None:
  facevalues=Hthumb[:,:3]@thumbmat+Hthumb[:,3]
  r.extend(np.maximum(facevalues,0)*1500);r.append(facevalues[thumbface]*1500)
 for finger in ['thumb','index','middle','ring']:
  for gap_index,gap in enumerate(g.gaps(h,l,float(s['slider_q'])+stroke,finger,frames=F)):
   threshold=-.0004 if gap['hand_link']==name and gap['knife_link']=='link_1' else .0003 if finger=='thumb' else -.0005
   if gap['knife_link']=='link_0' and gap['hand_link'] in cfg.get('thumb_body_clearance_links',[]):threshold=cfg['thumb_selected_body_clearance_m']
   if a.strict_body_clearance and finger!='thumb':threshold=-.00015 if gap['hand_link'] in materials else .0001
   if preserve_acquired and gap['hand_link'] in materials and gap['knife_link']=='link_0':threshold=min(threshold,initial_gaps[finger][gap_index]['gap_lower_bound_m'])
   if preserve_acquired and cfg.get('preserve_all_acquired_nonthumb_gaps') and gap['hand_link'] in acquired_nonthumb and gap['knife_link']=='link_0':threshold=min(threshold,initial_gaps[finger][gap_index]['gap_lower_bound_m'])
   r.append(min(0,gap['gap_lower_bound_m']-threshold)*(1500 if a.strict_body_clearance and finger!='thumb' else 250))
  selected = cfg.get('selected_self_clearance', [])
  clearance = max([.0001]+[v['clearance_m'] for v in selected])
  for v in g.self_gaps(h,finger,certify_clearance_m=.0001,frames=F,transformed=transformed,enclosing_spheres=spheres,pair_clearances={tuple(sorted(v['links'])):v['clearance_m'] for v in selected}):
   threshold=.0001; weight=100
   for spec in selected:
    if {v['moving_link'],v['other_link']} == set(spec['links']):
     threshold=spec['clearance_m']; weight=1500
   r.append(min(0,v['gap_lower_bound_m']-threshold)*weight)
 r.extend((x-x0)*.02);return np.array(r)
record('direct_coordinated_actual_pad_stroke_planning_start',[str(a.output)],config={'uncertainty':'Thumb26mmfixedwrist unavailable; wrist/finger compensation retains3loadedactualmaterials andgenuinepadnormal across actualmovingcap geometry?','stroke_m':stroke,'decision':'Feasible endpoint+path permits one actualstroke; failure changes supportsliding/materialgait or initialfunctionalgrip'},next_step='Jointkinematic contactcapacity first; no pressureincrease or idealobject state')
b=time.time();seed=x0.copy()
if cfg.get('relative_grip_endpoint_prior'):
 prior=json.load(open(cfg['relative_grip_endpoint_prior']))
 priorarm,priorik=k.solve_near(O@np.array(prior['wrist_in_knife']),s['robot_q'][:7].astype(float),max_step=1.)
 if not a.arm_coordination:raise ValueError('Relativegrip prior requires actual G2 endpoint variables')
 endpoint_range=cfg.get('certified_arm_search_range_rad',.6)
 lo[:7]=np.maximum(k.lower+.025,s['robot_q'][:7]-endpoint_range)
 hi[:7]=np.minimum(k.upper-.025,s['robot_q'][:7]+endpoint_range)
 seed[:7]=priorarm;seed[base:base+len(ids)]=np.array(prior['hand_q'])[ids]
elif cfg.get('thumb_endpoint_prior'):
 prior=json.load(open(cfg['thumb_endpoint_prior']))
 # An explicit known distal branch is an endpoint initialization only.
 # Actual acquired wrist and all support material constraints remain current.
 seed[base+12:base+16]=np.array(prior['hand_q'])[16:20]
if not a.arm_coordination:seed[:3]+=np.array([0,0,stroke*.5])
fit=least_squares(res,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=140,diff_step=1e-5);l,h,F=decode(fit.x)
if a.arm_coordination:arm=fit.x[:7];e={'position_m':0.,'rotation_rad':0.,'joint_margin_rad':float(np.minimum(arm-k.lower,k.upper-arm).min()),'scope':'Actual7G2variables optimized, no inversepose shortcut'}
else:arm,e=k.solve_near(O@l,s['robot_q'][:7].astype(float),max_step=1.)
if a.slide_index_material:materials[index]=fit.x[-3:].copy()
for n,(j,Hs,face) in support_material_bases.items():materials[n]=fit.x[j:j+3].copy()
if thumb_material_base is not None:m=fit.x[thumb_material_base:thumb_material_base+3].copy()
T=l@F[name];errors={n:float(np.linalg.norm((l@F[n])[:3,:3]@mat+(l@F[n])[:3,3]-points[n])) for n,mat in materials.items()};out=dict(source=str(a.source),stroke_m=stroke,approach_cap=bool(a.approach_cap),thumb_local_normal=thumbNormal.tolist(),wrist_in_knife=l.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),arm_ik=e,thumb_material=m.tolist(),thumb_target=thumbTarget.tolist(),thumb_point=(T[:3,:3]@m+T[:3,3]).tolist(),thumb_error_m=float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-thumbTarget)),thumb_surface_normal=(T[:3,:3]@thumbNormal).tolist(),support_errors_m=errors,support_materials={n:m.tolist() for n,m in materials.items()},support_points={n:p.tolist() for n,p in points.items()},self_intersections=HandIntersection().inspect(h),elapsed_s=time.time()-b,arm_coordination=a.arm_coordination,sliding_index_material=a.slide_index_material);out.update({key:cfg[key] for key in ['thumb_body_clearance_links','thumb_selected_body_clearance_m','preserve_acquired_body_gaps','preserve_all_acquired_nonthumb_gaps','planning_hand_margin_rad','planning_thumb_margin_rad','thumb_normal_cone_cosine','synchronize_posture_transition','axial_proxy_reference_N','support_command_upper_margin_rad','selected_self_clearance','preserve_acquired_spread_joint_indices','slide_support_materials'] if key in cfg});(a.output/'candidate.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q','support_materials','support_points']},flush=True);record('direct_coordinated_actual_pad_stroke_endpoint',[str(a.output/'candidate.json')],config={k:out[k] for k in ['thumb_error_m','support_errors_m','arm_ik','self_intersections','thumb_surface_normal']},next_step='Feasibleendpoint prepares loaded contactpath; failure identifies insufficientsupportspan orcorrespondingwrist DOF')
