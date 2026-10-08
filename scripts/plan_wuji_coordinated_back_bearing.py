"""Coordinated new back bearing with retained old opposition and free wrist pose.

No prescribed roll angle, fixed material locations or additional pressure.
Old contacts can roll and slide axially; the ring pad must reach the actual back
face before the old clamp can retire. Geometry alone is not physical load proof.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform,minimal_alignment
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--version');p.add_argument('--bearing-goal-z-m',type=float);p.add_argument('--bearing-abduction-q2-max',type=float);p.add_argument('--gravity-wrench-calibration',type=Path);p.add_argument('--adaptive-resume-path',action='store_true');p.add_argument('--bearing-digit',choices=['ring','pinky'],default='ring');p.add_argument('--hold-middle-posture',action='store_true');p.add_argument('--arm-coordinates',action='store_true');p.add_argument('--cleared-side-source',action='store_true');p.add_argument('--bearing-self-clearance-m',type=float,default=.0002);p.add_argument('--whole-patch-clearance',action='store_true');p.add_argument('--resume-geometry',type=Path);p.add_argument('--max-wall-seconds',type=float,default=240.);p.add_argument('--around-corner',action='store_true');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;normal_counts_before=sum(len(n)for meshes in g.meshes.values()for _,n in meshes)
 for name,meshes in g.meshes.items():g.meshes[name]=[(v,np.unique(n,axis=0))for v,n in meshes]
 normal_counts_after=sum(len(n)for meshes in g.meshes.values()for _,n in meshes);h0=z['robot_q'][7:].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);L0=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);manifest=json.loads((a.source/'manifest.json').read_text());contact_rows=[json.loads(t)for t in (Path(manifest['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];contact_row=min(contact_rows,key=lambda row:abs(row['time_s']-manifest['takeover_elapsed_s']));cc=contact_row['contacts'];names=[]
 for digit in ['index','middle','thumb']:
  available={c['hand_link']for c in cc if '_'+digit+'_'in c['hand_link']};assert available,digit;names.append(max(available,key=lambda name:sum(c['normal_magnitude_N']for c in cc if c['hand_link']==name)))
 materials=[];P0=[];hulls=[]
 for name in names:
  selected=[c for c in cc if c['hand_link']==name];w=np.array([c['normal_magnitude_N']for c in selected]);w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in selected]);materials.append(m);T=L0@g.w.forward(h0)[name];P0.append(T[:3,:3]@m+T[:3,3]);hulls.append(ConvexHull(np.concatenate([v for v,_ in g.meshes[name]])))
 ring='hand_r_'+a.bearing_digit+'_pad_link';V=np.concatenate([v for v,_ in g.meshes[ring]])
 def ring_vertices(L,h):
  T=L@g.w.forward(h)[ring];return V@T[:3,:3].T+T[:3,3]
 def ring_foot(L,h):
  P=ring_vertices(L,h);w=np.exp((P[:,1]-P[:,1].max())/.0002);return w@P/w.sum()
 first=ring_foot(L0,h0);first_vertices=ring_vertices(L0,h0);goal=np.clip(first,[-.006,-.004,-.065],[.006,-.004,-.025]);
 if a.bearing_goal_z_m is not None:assert -.07<=a.bearing_goal_z_m<=.065;goal[2]=a.bearing_goal_z_m
 if a.around_corner:goal[1]=-.0042
 if a.whole_patch_clearance:goal[1]=-.0044
 if a.cleared_side_source:assert a.whole_patch_clearance and first_vertices[:,0].min()>.0125
 retreat=first.copy();retreat[0]+=.0145-first_vertices[:,0].min();back_corner=retreat.copy();back_corner[1]=-.0094;back_corner[2]=goal[2];back_inside=goal.copy();back_inside[1]=-.0094
 corner=np.array([max(first[0]+.0005,.0102),-.0044,first[2]]);ids=np.array(sorted(set(list(range(4))+([]if a.hold_middle_posture else list(range(4,8)))+list(range(16,20))+list(range(12,16)if a.bearing_digit=='ring'else range(8,12)))));hand_end=6+len(ids);x0=np.r_[np.zeros(6),h0[ids],np.array(materials).ravel()];low=np.r_[[-.035]*3,[-.60]*3,g.w.lower[ids]+.025,np.concatenate([H.points.min(0)-.0002 for H in hulls])];high=np.r_[[.035]*3,[.60]*3,g.w.upper[ids]-.025,np.concatenate([H.points.max(0)+.0002 for H in hulls])];depth={};P0=np.array(P0)
 for digit in sorted(set(['index','middle','thumb','ring',a.bearing_digit])):
  for c in g.gaps(h0,L0,float(z['slider_q']),digit):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 if a.arm_coordinates:
  x0=np.r_[z['robot_q'][:7].astype(float),h0[ids],np.array(materials).ravel()];low=np.r_[f.kin.lower+.06,low[6:]];high=np.r_[f.kin.upper-.06,high[6:]]
 material_start=hand_end+(1 if a.arm_coordinates else 0);force_start=material_start+9;cal=None;normal_corrections=[];force_initial=np.zeros((4,3))
 if a.gravity_wrench_calibration:
  cal=json.loads(a.gravity_wrench_calibration.read_text());assert cal['feasible']and cal['source']==str(a.source);force_initial[:3]=cal['allocated_F_proxy_knife_N'];budget=cal['original_normal_budget_N'];wrench=np.array(cal['desired_gravity_wrench']);com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])])
  for j,(name,m,H)in enumerate(zip(names,materials,hulls)):
   T=L0@g.w.forward(h0)[name];eq=H.equations[:,:3]@m+H.equations[:,3];normal_corrections.append(minimal_alignment(H.equations[eq.argmax(),:3],T[:3,:3].T@np.array(cal['normals_knife'][j])))
  x0=np.r_[x0,force_initial.ravel()];low=np.r_[low,[-budget]*12];high=np.r_[high,[budget]*12]
 def decode(x):
  h=h0.copy()
  if a.arm_coordinates:L=np.linalg.inv(O)@f.kin.forward(x[:7]);h[ids]=x[7:hand_end+1];M=x[hand_end+1:hand_end+10].reshape(3,3)
  else:L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];h[ids]=x[6:hand_end];M=x[hand_end:hand_end+9].reshape(3,3)
  return L,h,M
 prior=x0.copy();rows=[];arm=z['robot_q'][:7].astype(float)
 if a.resume_geometry:
  old=json.loads(a.resume_geometry.read_text());assert old['source']==str(a.source);rows=old['rows'];last=rows[-1];L=np.array(last['wrist_in_knife']);h=np.array(last['hand_q']);M=np.array([last['contact_material_points'][n]for n in names]);prior=np.r_[L[:3,3]-L0[:3,3],Rotation.from_matrix(L[:3,:3]@L0[:3,:3].T).as_rotvec(),h[ids],M.ravel()];arm=np.array(last['arm_q'])
  if a.arm_coordinates:prior=np.r_[arm,h[ids],M.ravel()]
  if cal is not None:prior=np.r_[prior,np.array(last.get('gravity_wrench_proxy',{}).get('forces_knife_N',force_initial)).ravel()]
 start=time.monotonic();failure=None;force_valid=bool(rows[-1].get('gravity_wrench_proxy',{}).get('valid',True))if rows else True;version=a.version or 'v912' if cal is not None else 'v909' if a.bearing_digit=='pinky' else 'v905' if a.arm_coordinates else 'v903' if a.cleared_side_source else 'v899' if a.whole_patch_clearance else 'v896' if a.around_corner else 'v895';record('coordinated_new_back_bearing_geometry_started_'+version,[str(a.source)],dict(scope=__doc__,initial_ring_foot=first.tolist(),resume_geometry=str(a.resume_geometry)if a.resume_geometry else None,reused_poses=len(rows),contact_source_time_s=contact_row['time_s'],actual_primary_links=names,arm_coordinates=a.arm_coordinates,new_bearing_digit=a.bearing_digit,bearing_goal_z_m=a.bearing_goal_z_m,bearing_abduction_q2_max=a.bearing_abduction_q2_max,hold_middle_posture=a.hold_middle_posture,gravity_wrench_calibration=str(a.gravity_wrench_calibration)if cal is not None else None,bearing_self_clearance_m=a.bearing_self_clearance_m,already_cleared_side=a.cleared_side_source,exact_normal_deduplication=dict(before=normal_counts_before,after=normal_counts_after),goal_ring_region=[[-.006,-.004,-.065],[.006,-.004,-.025]],wrist_freedom='3translation/3rotation, originalarmreachability',old_bearing='oppositionX retained, Ywithinbody andaxialmigration±12mm, contactpoint rolls onsameoriginalhull'),next_step='Truebackbearing first withwholegripmotion; nativechecksload beforeanyoldThumbrelease, no fixedturnangle')
 count=13 if a.cleared_side_source else 17 if a.around_corner or a.whole_patch_clearance else 13;adaptive_targets=[];acquisition_start=8 if a.cleared_side_source else 12
 if a.adaptive_resume_path:
  assert a.resume_geometry and rows[-1]['phase']=='enter-back-face';last_target=np.array(rows[-1].get('bearing_target_knife_m',rows[-1].get('ring_target_knife_m')));n=max(1,int(np.ceil(np.linalg.norm(back_inside-last_target)/.005)));adaptive_targets=[('enter-back-face',v)for v in np.linspace(last_target,back_inside,n+1)[1:]]+[('acquire-back-face',v)for v in np.linspace(back_inside,goal,5)[1:]];acquisition_start=len(rows)+n-1;count=len(rows)+len(adaptive_targets);reused=len(rows)
  for j,r in enumerate(rows):r['fraction']=j/(count-1)
 for index,u in enumerate(np.linspace(0,1,count)):
  if index<len(rows):continue
  if a.adaptive_resume_path:phase,wanted=adaptive_targets[index-reused]
  elif a.whole_patch_clearance:
   anchors=[first,retreat,back_corner,back_inside,goal];stage=min(3,index//4);local=(index-stage*4)/4
   if a.cleared_side_source:
    already_back_corner=first.copy();already_back_corner[1]=-.0094;already_back_corner[2]=goal[2];anchors=[first,already_back_corner,back_inside,goal];stage=min(2,index//4);local=(index-stage*4)/4;phase=['clear-whole-back-corner','enter-back-face','acquire-back-face'][stage]
   else:phase=['withdraw-whole-pad','clear-whole-back-corner','enter-back-face','acquire-back-face'][stage]
   wanted=anchors[stage]*(1-local)+anchors[stage+1]*local
  elif a.around_corner:
   local=index/8 if index<=8 else (index-8)/8;wanted=first*(1-local)+corner*local if index<=8 else corner*(1-local)+goal*local
   assert wanted[0]>=.0095 or wanted[1]<=-.004,'Ringapproach crossesknifevolume'
  else:wanted=first*(1-u)+goal*u
  geometry_cache={}
  def wrench_constraints(x,L,h,M,F):
   P=[];N=[]
   for j,(name,m,H)in enumerate(zip(names,M,hulls)):
    T=L@F[name];P.append(T[:3,:3]@m+T[:3,3]);eq=H.equations[:,:3]@m+H.equations[:,3];N.append(T[:3,:3]@normal_corrections[j]@H.equations[eq.argmax(),:3])
   P.append(ring_foot(L,h));N.append(np.array([0.,1.,0.]));P=np.array(P);N=np.array(N);forces=x[force_start:].reshape(4,3);fn=np.sum(forces*N,1);ft=forces-fn[:,None]*N;active=phase=='acquire-back-face'and wanted[0]<.0092 and wanted[1]+.00019>-.0055;sel=4 if active else 3;error=np.r_[forces.sum(0)-wrench[:3],np.cross(P-com,forces).sum(0)-wrench[3:]];slack=np.r_[.8**2*fn[:sel]**2-np.sum(ft[:sel]**2,1),fn[:3]-.10,fn[3]-.15 if active else 0.,budget-fn.sum()];return error,slack,active,forces
  def residual(x):
   if time.monotonic()-start>a.max_wall_seconds:raise TimeoutError('Boundedwholegripbearingpath walltime reached')
   L,h,M=decode(x);key=x[:material_start].tobytes();F=geometry_cache.get('frames')if geometry_cache.get('key')==key else g.w.forward(h);r=[]
   for j,(name,m,H)in enumerate(zip(names,M,hulls)):
    T=L@F[name];P=T[:3,:3]@m+T[:3,3];lo=np.array([(.0095 if j<2 else-.0095),-.004,P0[j,2]-.012]);hi=np.array([lo[0],.004,P0[j,2]+.012]);r.extend((P-np.clip(P,lo,hi))*800);eq=H.equations[:,:3]@m+H.equations[:,3];r.append(float(eq.max())*1000);r.extend(np.maximum(eq,0)*1000)
   P=ring_foot(L,h);r.extend((P-wanted)*800)
   if a.bearing_abduction_q2_max is not None:
    q2=13 if a.bearing_digit=='ring'else 9;limit=h0[q2]+min(index/4.,1.)*(a.bearing_abduction_q2_max-h0[q2]);r.append(max(0.,h[q2]-limit)*500)
   if a.whole_patch_clearance:
    vertices=ring_vertices(L,h)
    if phase=='withdraw-whole-pad':r.append(min(0.,vertices[:,0].min()-(first_vertices[:,0].min()+min(index/4,1)*(.0145-first_vertices[:,0].min())))*1400)
    elif phase=='clear-whole-back-corner':r.append(min(0.,vertices[:,0].min()-(min(.0145,first_vertices[:,0].min()) if a.cleared_side_source else .0145))*1400)
    elif phase=='enter-back-face':r.append(max(0.,vertices[:,1].max()+.009)*1400)
    else:r.append(max(0.,vertices[:,1].max()+.0042)*1400)
   if geometry_cache.get('key')!=key:
    gr=[]
    for digit in sorted(set(['index','middle','thumb','ring',a.bearing_digit])):
     for c in g.gaps(h,L,float(z['slider_q']),digit,frames=F,certify_clearance_m=.0002):gr.append(min(0.,c['gap_lower_bound_m']-depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))])*1400)
    gr.extend(min(0.,c['gap_lower_bound_m']-(.0002+min(index/4,1)*(a.bearing_self_clearance_m-.0002)if a.bearing_digit in c['link_a']or a.bearing_digit in c['link_b']else .0002))*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=a.bearing_self_clearance_m));geometry_cache.update(key=key,frames=F,r=gr)
   r.extend(geometry_cache['r'])
   if cal is not None:
    force_error,slack,active,forces=wrench_constraints(x,L,h,M,F);r.extend(force_error*np.array([500,500,500,25000,25000,25000]));r.extend(np.minimum(slack,0)*1000);r.extend(forces[3]*500 if not active else np.zeros(3))
   if a.arm_coordinates:
    translation=L[:3,3]-L0[:3,3];rotation=Rotation.from_matrix(L[:3,:3]@L0[:3,:3].T).as_rotvec();r.extend(translation*3);r.extend(rotation*.1);r.extend(np.maximum(abs(translation)-.035,0)*1000);r.append(max(0.,np.linalg.norm(rotation)-.60)*1000)
   else:r.extend(x[:3]*3);r.extend(x[3:6]*.1)
   r.extend((x-prior)*.02);return np.array(r)
  try:
   x=prior.copy() if index==0 else least_squares(residual,np.clip(prior,low+1e-7,high-1e-7),bounds=(low,high),max_nfev=40,diff_step=1e-5).x
  except TimeoutError as exc:failure=str(exc);break
  L,h,M=decode(x);actual=ring_foot(L,h);error=float(np.linalg.norm(actual-wanted));
  if a.arm_coordinates:
   previous_arm=arm.copy();arm=x[:7].copy();ik=dict(position_m=0.,rotation_rad=0.,max_joint_step_rad=float(abs(arm-previous_arm).max()),joint_margin_rad=float(np.minimum(arm-f.kin.lower,f.kin.upper-arm).min()))
  else:arm,ik=f.kin.solve_near(O@L,arm,max_step=.15,minimum_margin=.06)
  bad=f.H.inspect(h);row=dict(phase=phase if a.whole_patch_clearance else 'clear-side-to-back-corner' if a.around_corner and index<=8 else 'enter-back-face' if a.around_corner else 'straight-approach',index=index,fraction=float(u),wrist_in_knife=L.tolist(),arm_q=arm.tolist(),hand_q=h.tolist(),bearing_foot_knife_m=actual.tolist(),bearing_target_knife_m=wanted.tolist(),ring_error_m=error,bearing_pad_bounds_knife_m=[ring_vertices(L,h).min(0).tolist(),ring_vertices(L,h).max(0).tolist()],contact_material_points=dict(zip(names,[m.tolist()for m in M])),arm_IK=ik,self=bad);
  if a.bearing_digit=='ring':row.update(ring_foot_knife_m=row['bearing_foot_knife_m'],ring_target_knife_m=row['bearing_target_knife_m'],ring_pad_bounds_knife_m=row['bearing_pad_bounds_knife_m'])
  force_valid=True
  if cal is not None:
   fe,slack,active,forces=wrench_constraints(x,L,h,M,g.w.forward(h));inactive_error=float(np.linalg.norm(forces[3]))if not active else 0.;force_error=float(np.linalg.norm(fe*np.array([1,1,1,100,100,100])));force_valid=force_error<.0001 and slack.min()>-.0001 and inactive_error<.0001;row['gravity_wrench_proxy']=dict(error_scaled=force_error,min_cone_slack=float(slack.min()),active_new_bearing=bool(active),inactive_force_error=inactive_error,forces_knife_N=forces.tolist(),valid=bool(force_valid))
  rows.append(row);prior=x;(a.output/'partial.json').write_text(json.dumps(dict(rows=rows,geometry_pass=False),indent=2));print(json.dumps(row),flush=True)
  if not force_valid or error>.0007 or bad or ik['position_m']>.0003 or ik['rotation_rad']>.003:break
 passed=force_valid and len(rows)==count and rows[-1]['fraction']==1 and rows[-1]['ring_error_m']<.0007 and not rows[-1]['self']and rows[-1]['arm_IK']['position_m']<.0003 and rows[-1]['arm_IK']['rotation_rad']<.003;out=dict(rows=rows,geometry_pass=bool(passed),source=str(a.source),initial_issued=z['issued_target'].tolist(),failure=failure,elapsed_s=time.monotonic()-start,scope=__doc__,new_bearing_digit=a.bearing_digit,new_bearing_initially_clear=a.cleared_side_source,bearing_acquisition_start_index=acquisition_start);(a.output/'result.json').write_text(json.dumps(out,indent=2));record('coordinated_new_back_bearing_geometry_terminal_'+version,[str(a.output/'result.json')],dict(passed=bool(passed),poses=len(rows),failure=failure,last=rows[-1]if rows else None),next_step='Sourceconsistenttrueback-bearing guide ->nativewholegripshort load proof; blockedchangecontactmode, no pressure/timinggrid')
if __name__=='__main__':main()
