"""Continuous actual-pad stroke, original index surface sliding and G2 leveling."""
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
from scripts.wuji_direct_contact_prior import source_contacts
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--strict-body-clearance',action='store_true');p.add_argument('--world-axial-leveling-degrees',type=float,default=-15.);p.add_argument('--thumb1-upper',type=float);p.add_argument('--thumb3-lower',type=float);p.add_argument('--arm7-reserve',type=float);p.add_argument('--planning-hand-margin',type=float);p.add_argument('--reverse-continuation',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=np.load(a.source/'takeover.npz');c=json.load(a.candidate.open());g=DigitGeometry(max_face_axes=10 if a.strict_body_clearance else 8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O0=transform(s['object_state'][:3],s['object_state'][3:7]);arm0=s['robot_q'][:7].astype(float);q0=s['robot_q'][7:].astype(float);L0=np.linalg.inv(O0)@k.forward(arm0);ids=np.r_[0:8,12:20];name='hand_r_thumb_pad_link';m=np.array(c['thumb_material']);T=L0@g.w.forward(q0)[name];P0=T[:3,:3]@m+T[:3,3];priorTrial=Path(json.load((a.source/'manifest.json').open())['source']).parent;native=[json.loads(l) for l in (priorTrial/'wrap-contact-physical-steps.jsonl').open()];end=max(r['time_s'] for r in native);materials={}
priorTrial,native,end=source_contacts(a.source)
preserve_acquired=c.get('preserve_acquired_body_gaps',False)
acquired_nonthumb={v['hand_link'] for r in native for v in r['contacts'] if v['knife_link']=='link_0' and '_thumb_' not in v['hand_link']}
for n in c['support_materials']:
 C=[v for r in native if r['time_s']>end-.3 for v in r['contacts'] if v['hand_link']==n];materials[n]=np.mean([v['position_hand_link_m'] for v in C],0)
T=L0@g.w.forward(q0)[name];C=[v for r in native if r['time_s']>end-.3 for v in r['contacts'] if v['hand_link']==name and v['knife_link']=='link_1'];normal=np.mean([v['force_normal_contribution_knife_N'] for v in C],0);normal/=np.linalg.norm(normal);localNormal=T[:3,:3].T@normal;bodyOffset=s['issued_target'][7:]-q0;armOffset=s['issued_target'][:7]-arm0;physics=json.load((priorTrial/'physics.json').open());kp=np.array(physics['kp'][-4:]);seed=np.r_[arm0,q0[ids]];rows=[];D=[];checker=HandIntersection();beg=time.time();stroke=c['stroke_m'];loAll=np.r_[k.lower+.04,g.w.lower[ids]+.035];hiAll=np.r_[k.upper-.04,g.w.upper[ids]-.035]
initialGaps={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']};collision_parts=g.knife_geometry.collision_parts
initialSelf={f:{(v['moving_link'],v['other_link']):v['gap_lower_bound_m'] for v in g.self_gaps(q0,f,certify_clearance_m=.0001)} for f in ['thumb','index','middle','ring']}
if a.thumb1_upper is not None:hiAll[7+list(ids).index(16)]=a.thumb1_upper
if a.thumb3_lower is not None:loAll[7+list(ids).index(18)]=a.thumb3_lower
if a.arm7_reserve is not None:hiAll[6]=min(hiAll[6],k.upper[6]-a.arm7_reserve)
record('direct_sliding_pad_stroke_path_start',[str(a.output)],config={'uncertainty':'26mm reachableendpoint can be followed with originalfacet materialsliding, actual3supports and-15deg worldleveling while G2 retainsjointreserve?','decision':'Feasiblecontinuous23variablepath permits shortnative stroke; physicalforce/contacthold thenfullcontinuous'},next_step='17causal boundedknots retainnormalpressure/reference, no objectstatewriter')
times=np.linspace(0,9,19)
if a.reverse_continuation:
 times=times[::-1];seed=np.r_[np.array(c['arm_q']),np.array(c['hand_q'])[ids]]
for t in times:
 u=smooth((t-.5)/6);O=O0@transform(quaternion=Rotation.from_euler('z',a.world_axial_leveling_degrees*u,degrees=True).as_quat());M={n:np.array(v) for n,v in materials.items()}
 if 'hand_r_index_link2' in M:M['hand_r_index_link2']=(1-u)*M['hand_r_index_link2']+u*np.array(c['support_materials']['hand_r_index_link2'])
 for link in c.get('slide_support_materials',[]):
  M[link]=(1-u)*np.array(materials[link])+u*np.array(c['support_materials'][link])
 target=P0+[0,0,stroke*u];slider=float(s['slider_q'])+stroke*u;previous=seed.copy();prior=np.r_[arm0*(1-u)+np.array(c['arm_q'])*u,q0[ids]*(1-u)+np.array(c['hand_q'])[ids]*u]
 fixedparts=collision_parts(slider);g.knife_geometry.collision_parts=lambda ignored:fixedparts
 def decode(x):
  h=q0.copy();h[ids]=x[7:];l=np.linalg.inv(O)@k.forward(x[:7]);return l,h,g.w.forward(h)
 def res(x):
  l,h,F=decode(x);r=[]
  for n,mat in M.items():
   T=l@F[n];delta=T[:3,:3]@mat+T[:3,3]-np.array(c['support_points'][n])
   axial_range=float(c.get('support_axial_range_m',0.))
   if axial_range:
    r.extend(delta[:2]*350);r.append(delta[2]*20)
    r.append(max(0.,abs(delta[2])-axial_range)*1500)
   else:r.extend(delta*350)
  T=l@F[name];r.extend((T[:3,:3]@m+T[:3,3]-target)*300)
  if c.get('thumb_normal_cone_cosine') is None:r.extend((T[:3,:3]@localNormal-((1-u)*normal+u*np.array([0,-1,0])))*.7)
  else:r.append(max(0.,((1-u)*min(c['thumb_normal_cone_cosine'],-normal[1])+u*c['thumb_normal_cone_cosine'])+(T[:3,:3]@localNormal)[1])*.7)
  for finger in ['thumb','index','middle','ring']:
   for gap,g0 in zip(g.gaps(h,l,slider,finger,frames=F),initialGaps[finger]):
    threshold=-.0004 if gap['hand_link']==name and gap['knife_link']=='link_1' else .0002 if finger=='thumb' else -.0006
    if gap['knife_link']=='link_0' and gap['hand_link'] in c.get('thumb_body_clearance_links',[]):threshold=c['thumb_selected_body_clearance_m']
    if a.strict_body_clearance:
     if finger!='thumb':threshold=-.00015 if gap['hand_link'] in M else .0001
     threshold=(1-u)*min(threshold,g0['gap_lower_bound_m'])+u*threshold
    if preserve_acquired and gap['hand_link'] in M and gap['knife_link']=='link_0':threshold=min(threshold,g0['gap_lower_bound_m'])
    if preserve_acquired and c.get('preserve_all_acquired_nonthumb_gaps') and gap['hand_link'] in acquired_nonthumb and gap['knife_link']=='link_0':threshold=min(threshold,g0['gap_lower_bound_m'])
    r.append(min(0,gap['gap_lower_bound_m']-threshold)*(1500 if a.strict_body_clearance and finger!='thumb' else 250 if a.strict_body_clearance else 220))
   selected=c.get('selected_self_clearance',[])
   clearance=max([.0001]+[v['clearance_m'] for v in selected])
   for v in g.self_gaps(h,finger,certify_clearance_m=.0001,frames=F,pair_clearances={tuple(sorted(v['links'])):v['clearance_m'] for v in selected}):
    gap0=initialSelf[finger].get((v['moving_link'],v['other_link']),.0001)
    threshold=(1-u)*min(.0001,gap0)+u*.0001 if preserve_acquired else .0001
    weight=70
    for spec in selected:
     if {v['moving_link'],v['other_link']} == set(spec['links']):
      # Retain the actual entry posture and separate this known pair by
      # motor motion before the main stroke. No collision filter changes.
      posture_blend=u if c.get('synchronize_posture_transition') else smooth(t/1.5)
      threshold=(1-posture_blend)*min(spec['clearance_m'],gap0)+posture_blend*spec['clearance_m']
      weight=1500
    r.append(min(0,v['gap_lower_bound_m']-threshold)*weight)
  if a.arm7_reserve is not None:r.append((x[6]-prior[6])*.3)
  elif not a.strict_body_clearance:r.append((x[6]-((1-u)*arm0[6]+u*1.4))*.3)
  r.extend((x-prior)*.015);return np.array(r)
 lo=np.maximum(loAll,previous-.18);hi=np.minimum(hiAll,previous+.18)
 if a.planning_hand_margin is not None:
  # Enter the desired reserve from the genuine loaded source without a
  # boundary jump. Original physical joint limits are never changed.
  blend=u if c.get('synchronize_posture_transition') else smooth(t/1.5);margin=np.full(len(ids),a.planning_hand_margin)
  if c.get('planning_thumb_margin_rad') is not None:margin[np.isin(ids,np.arange(16,20))]=c['planning_thumb_margin_rad']
  lowmargin=(1-blend)*np.minimum(margin,np.maximum(0,q0[ids]-g.w.lower[ids]))+blend*margin
  highmargin=(1-blend)*np.minimum(margin,np.maximum(0,g.w.upper[ids]-q0[ids]))+blend*margin
  lo[7:]=np.maximum(np.maximum(loAll[7:],g.w.lower[ids]+lowmargin),previous[7:]-.18)
  bounds_hi=hiAll[7:].copy()
  if a.thumb1_upper is not None:
   j=list(ids).index(16);bounds_hi[j]=(1-blend)*max(q0[16],a.thumb1_upper)+blend*a.thumb1_upper
  hi[7:]=np.minimum(np.minimum(bounds_hi,g.w.upper[ids]-highmargin),previous[7:]+.18)
 for index in c.get('preserve_acquired_spread_joint_indices',[]):
  j=7+list(ids).index(index)
  lo[j]=max(lo[j],q0[index]-.005);hi[j]=min(hi[j],q0[index]+.005)
 for index in c.get('fixed_hand_joint_indices',[]):
  if index in ids:
   j=7+list(ids).index(index);lo[j]=q0[index]-1e-6;hi[j]=q0[index]+1e-6
 if a.reverse_continuation and u==0:seed=np.r_[arm0,q0[ids]]
 if (u>0 or not preserve_acquired) and (not D or abs(u-D[-1]['fraction'])>1e-10):
  fit=least_squares(res,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=55,diff_step=1e-5);seed=fit.x
 l,h,F=decode(seed);T=l@F[name];errors={n:float(np.linalg.norm((l@F[n])[:3,:3]@mat+(l@F[n])[:3,3]-np.array(c['support_points'][n]))) for n,mat in M.items()};P=T[:3,:3]@m+T[:3,3];J=np.empty((3,4))
 for j in range(4):
  hh=h.copy();hh[16+j]+=1e-5;TT=l@g.w.forward(hh)[name];J[:,j]=((TT[:3,:3]@m+TT[:3,3])-P)/1e-5
 forceReference=np.array([0,-1.4,c.get('axial_proxy_reference_N',.7355)*smooth((t-.5)/1.5)]);motorOffset=np.clip(J.T@forceReference/kp,-.12,.12);loadBlend=smooth(t/1.);cmd=h+bodyOffset;cmd[16:]=h[16:]+(1-loadBlend)*bodyOffset[16:]+loadBlend*motorOffset;cmd=np.clip(cmd,g.w.lower,g.w.upper);rows.append(dict(time_s=float(t),arm_q=(seed[:7]+armOffset).tolist(),hand_q=cmd.tolist()));entry=dict(time_s=float(t),fraction=float(u),thumb_error_m=float(np.linalg.norm(P-target)),support_errors_m=errors,arm_margin_rad=float(np.minimum(seed[:7]-k.lower,k.upper-seed[:7]).min()),max_joint_step_rad=float(abs(seed-previous).max()),self_intersections=checker.inspect(h),thumb_surface_normal=(T[:3,:3]@localNormal).tolist(),expected_slider_q_m=slider,index_material_point=M['hand_r_index_link2'].tolist() if 'hand_r_index_link2' in M else None,planned_arm_q=seed[:7].tolist(),planned_hand_q=h.tolist(),planned_object_world=O.tolist(),planned_support_materials={n:mat.tolist() for n,mat in M.items()},support_transverse_errors_m={n:float(np.linalg.norm(((l@F[n])[:3,:3]@mat+(l@F[n])[:3,3]-np.array(c['support_points'][n]))[:2])) for n,mat in M.items()},support_axial_errors_m={n:float(abs(((l@F[n])[:3,:3]@mat+(l@F[n])[:3,3]-np.array(c['support_points'][n]))[2])) for n,mat in M.items()});D.append(entry);print(json.dumps(entry),flush=True)
rows.sort(key=lambda v:v['time_s']);D.sort(key=lambda v:v['time_s'])
out=dict(rows=rows,diagnostics=D,source=str(a.source),candidate=str(a.candidate),stroke_m=stroke,object_world_initial=O0.tolist(),world_axial_leveling_degrees=a.world_axial_leveling_degrees,strict_body_clearance=a.strict_body_clearance,reverse_continuation=a.reverse_continuation,scope='Motor references only, explicit retained load; expectedmovingcap geometry is planning target, not actualslidercommand; originalbrake/limits/gravity unchanged',elapsed_s=time.time()-beg);(a.output/'stroke.json').write_text(json.dumps(out,indent=2));record('direct_sliding_pad_stroke_path_finished',[str(a.output/'stroke.json')],config={'max_thumb_error_m':max(d['thumb_error_m'] for d in D),'max_support_error_m':max(max(d['support_errors_m'].values()) for d in D),'min_arm_margin_rad':min(d['arm_margin_rad'] for d in D),'self_intersection_frames':sum(bool(d['self_intersections']) for d in D)},next_step='Only feasiblecontactpath native stroke; actual26mm+1shold is required before fullfresh directroute')
