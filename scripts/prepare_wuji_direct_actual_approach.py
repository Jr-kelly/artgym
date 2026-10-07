"""Joint contact path from the actual three-carrier state to the slider pad."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_direct_contact_prior import source_contacts

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--material-prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--keep-thumb-pressure',action='store_true');p.add_argument('--preserve-acquired-body-gaps',action='store_true');p.add_argument('--wrist-guide-weight',type=float,default=0.);p.add_argument('--reverse-continuation',action='store_true');p.add_argument('--knots',type=int,default=21);p.add_argument('--free-thumb-joint-path',action='store_true');p.add_argument('--free-thumb-distal-path',action='store_true');p.add_argument('--hand-margin',type=float,default=.02);p.add_argument('--thumb-force-reference',type=float,nargs=3);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 s=np.load(a.source/'takeover.npz');c=json.loads(a.candidate.read_text());prior=json.loads(a.material_prior.read_text());k=G2Kinematics();g=DigitGeometry(max_face_axes=c.get('planner_face_axes',10),knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
 O=transform(s['object_state'][:3],s['object_state'][3:7]);arm0=s['robot_q'][:7].astype(float);q0=s['robot_q'][7:].astype(float);L0=np.linalg.inv(O)@k.forward(arm0);F0=g.w.forward(q0);ids=np.r_[0:8,12:16] if a.free_thumb_joint_path else np.r_[0:8,12:19] if a.free_thumb_distal_path else np.r_[0:8,12:20];m=np.array(c.get('thumb_material',c.get('thumb_material_point')));localN=np.array(prior['local_normal']);T=L0@F0['hand_r_thumb_pad_link'];P0=T[:3,:3]@m+T[:3,3];N0=T[:3,:3]@localN
 endL=np.array(c['wrist_in_knife']);wrist_delta=Rotation.from_matrix(L0[:3,:3].T@endL[:3,:3]).as_rotvec()
 M0={};Pstart={};Pend={}
 native_trial,native,end=source_contacts(a.source)
 acquired_nonthumb={v['hand_link'] for r in native if r['time_s']>end-.3 for v in r['contacts'] if v['knife_link']=='link_0' and '_thumb_' not in v['hand_link']}
 for n in c['support_materials']:
  contacts=[v for r in native if r['time_s']>end-.3 for v in r['contacts'] if v['hand_link']==n];M0[n]=np.mean([v['position_hand_link_m'] for v in contacts],0);T=L0@F0[n];Pstart[n]=T[:3,:3]@M0[n]+T[:3,3];T=np.array(c['wrist_in_knife'])@g.w.forward(np.array(c['hand_q']))[n];Pend[n]=T[:3,:3]@c['support_materials'][n]+T[:3,3]
 fixedparts=g.knife_geometry.collision_parts(float(s['slider_q']));g.knife_geometry.collision_parts=lambda ignored:fixedparts
 gaps0={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']};loAll=np.r_[k.lower+.04,g.w.lower[ids]+a.hand_margin];hiAll=np.r_[k.upper-.04,g.w.upper[ids]-a.hand_margin];seed=np.r_[arm0,q0[ids]];armload=s['issued_target'][:7]-arm0;load=s['issued_target'][7:]-q0;rows=[];D=[];checker=HandIntersection();beg=time.time()
 record('direct_actual_joint_approach_path_start',[str(a.output)],config={'uncertainty':'Can actual3carrier geometry avoidfixedwrist intermediate losses while acquiredindex2 materialslides and genuinepad approaches cap?','source':str(a.source),'candidate':str(a.candidate),'decision':'Everypathknot geometry/contact reserve must pass before shortnativeapproach; no forcevariants or idealstatewriters'},next_step='Joint7G2+16hand path withactualmaterials, consistent10axiswholebodyconstraints')
 selfgaps0={f:g.self_gaps(q0,f,certify_clearance_m=.0001) for f in ['thumb','index','middle','ring']}
 if a.reverse_continuation:seed=np.r_[np.array(c['arm_q']),np.array(c['hand_q'])[ids]]
 duration=float(c.get('path_duration_s',6.));move_duration=float(c.get('path_move_duration_s',4.))
 times=np.linspace(0,duration,a.knots)
 if a.reverse_continuation:times=times[::-1]
 for t in times:
  u=smooth((t-.5)/move_duration);previous=seed.copy();qprior=np.r_[arm0*(1-u)+np.array(c['arm_q'])*u,q0[ids]*(1-u)+np.array(c['hand_q'])[ids]*u];M={n:np.array(v) for n,v in M0.items()};
  for n in M:M[n]=(1-u)*M0[n]+u*np.array(c['support_materials'][n])
  targets={n:(1-u)*Pstart[n]+u*Pend[n] for n in M};thumbtarget=(1-u)*P0+u*np.array(c['thumb_point'])
  # An acquired pad must remain on the cap. The approach arch is only for
  # a free thumb entering contact, not for a pressure-preserving adjustment.
  normal_fraction=u
  if c.get('thumb_waypoint_schedule') is not None:
   waypoints=c['thumb_waypoint_schedule'];fractions=[v['fraction'] for v in waypoints]
   assert fractions[0]==0 and fractions[-1]==1 and all(y>x for x,y in zip(fractions,fractions[1:]))
   points=[P0 if v.get('source') else P0+np.array(v['source_offset_m']) if 'source_offset_m' in v else np.array(v['position_knife_m']) for v in waypoints]
   segment=min(len(waypoints)-2,max(0,int(np.searchsorted(fractions,u,side='right'))-1));a0,b0=fractions[segment:segment+2];blend=smooth((u-a0)/(b0-a0));thumbtarget=(1-blend)*points[segment]+blend*points[segment+1]
   normal_fraction=smooth((u-c.get('normal_align_start_fraction',.3))/(c.get('normal_align_end_fraction',.7)-c.get('normal_align_start_fraction',.3)))
  elif c.get('free_thumb_outward_knife_m') is not None:
   # Release the observed side load before translating along the knife.
   # This is a motor-space target path, never an object state assignment.
   clear=P0+np.array(c['free_thumb_outward_knife_m']);wrap=clear.copy()
   wrap[1]=c.get('free_thumb_wrap_y_m',.018);wrap[2]=c['thumb_point'][2]
   if u<.25:thumbtarget=(1-smooth(u/.25))*P0+smooth(u/.25)*clear
   elif u<.7:thumbtarget=(1-smooth((u-.25)/.45))*clear+smooth((u-.25)/.45)*wrap
   else:thumbtarget=(1-smooth((u-.7)/.3))*wrap+smooth((u-.7)/.3)*np.array(c['thumb_point'])
   normal_fraction=smooth((u-.25)/.75)
  elif not a.keep_thumb_pressure:thumbtarget[1]+=.004*np.sin(np.pi*u)
  N=(1-normal_fraction)*N0+normal_fraction*np.array(c['thumb_surface_normal']);N/=np.linalg.norm(N)
  expectedO=O@transform(quaternion=Rotation.from_euler('z',c.get('object_axial_leveling_degrees',0.)*u,degrees=True).as_quat())
  guideL=L0.copy();guideL[:3,3]=(1-u)*L0[:3,3]+u*endL[:3,3];guideL[:3,:3]=L0[:3,:3]@Rotation.from_rotvec(wrist_delta*u).as_matrix()
  def decode(x):
   q=q0.copy();q[ids]=x[7:]
   if a.free_thumb_joint_path:q[16:]=(1-u)*q0[16:]+u*np.array(c['hand_q'])[16:]
   elif a.free_thumb_distal_path:q[19]=(1-u)*q0[19]+u*c['hand_q'][19]
   L=np.linalg.inv(expectedO)@k.forward(x[:7]);return L,q,g.w.forward(q)
  def res(x):
   L,q,F=decode(x);r=[]
   for n,mat in M.items():
    T=L@F[n];r.extend((T[:3,:3]@mat+T[:3,3]-targets[n])*350)
   T=L@F['hand_r_thumb_pad_link'];point_weight=30+270*smooth((u-.8)/.2) if a.free_thumb_joint_path else 300;normal_weight=.8*smooth((u-.8)/.2) if a.free_thumb_joint_path or a.free_thumb_distal_path else .8
   if 'thumb_waypoint_schedule' in c:normal_weight=.8*smooth((u-c.get('normal_align_start_fraction',.3))/(c.get('normal_align_end_fraction',.7)-c.get('normal_align_start_fraction',.3)))
   r.extend((T[:3,:3]@m+T[:3,3]-thumbtarget)*point_weight);r.extend((T[:3,:3]@localN-N)*normal_weight)
   if a.wrist_guide_weight:
    r.extend((L[:3,3]-guideL[:3,3])*50*a.wrist_guide_weight)
    r.extend(Rotation.from_matrix(guideL[:3,:3].T@L[:3,:3]).as_rotvec()*1.5*a.wrist_guide_weight)
   for finger in ['thumb','index','middle','ring']:
    gaps=g.gaps(q,L,float(s['slider_q']),finger)
    for gap,g0 in zip(gaps,gaps0[finger]):
     endpoint=(-.00015 if gap['hand_link'] in M else .0001) if finger!='thumb' else .0003 if gap['hand_link']!='hand_r_thumb_pad_link' else -.0003 if gap['knife_link']=='link_1' else .0003
     if a.free_thumb_joint_path and finger=='thumb' and gap['knife_link']=='link_0':
      envelope=c.get('free_joint_body_clearance_m',.0003)
      endpoint+=(envelope-.0003)*smooth((u-.12)/.13)*(1-smooth((u-.8)/.15))
     threshold=(1-u)*min(endpoint,g0['gap_lower_bound_m'])+u*endpoint
     if a.free_thumb_joint_path and finger=='thumb' and gap['knife_link']=='link_0':
      release=smooth((u-.12)/.13)
      # Once withdrawn, the whole free thumb needs the full requested
      # envelope, rather than u times the envelope plus old loaded contact.
      threshold=max(threshold,(1-release)*min(.0003,g0['gap_lower_bound_m'])+release*endpoint)
     if a.preserve_acquired_body_gaps and gap['hand_link'] in M and gap['knife_link']=='link_0':threshold=min(endpoint,g0['gap_lower_bound_m'])
     if a.preserve_acquired_body_gaps and c.get('preserve_all_acquired_nonthumb_gaps') and gap['hand_link'] in acquired_nonthumb and gap['knife_link']=='link_0':threshold=min(endpoint,g0['gap_lower_bound_m'])
     r.append(min(0,gap['gap_lower_bound_m']-threshold)*1500)
    current_self=g.self_gaps(q,finger,certify_clearance_m=.0001)
    initial_self={(v['moving_link'],v['other_link']):v['gap_lower_bound_m'] for v in selfgaps0[finger]}
    for v in current_self:
     initial_gap=initial_self.get((v['moving_link'],v['other_link']),.0001)
     threshold=(1-u)*min(.0001,initial_gap)+u*.0001 if a.preserve_acquired_body_gaps else .0001
     r.append(min(0,v['gap_lower_bound_m']-threshold)*150)
   r.extend((x-qprior)*.02);return np.array(r)
  if a.reverse_continuation and u==0:seed=np.r_[arm0,q0[ids]]
  if (a.reverse_continuation or t<=move_duration+.8) and (u>0 or not a.preserve_acquired_body_gaps):
   lo=np.maximum(loAll,previous-.16);hi=np.minimum(hiAll,previous+.16)
   if a.preserve_acquired_body_gaps:
    margin=(1-u)*min(.04,float(np.minimum(arm0-k.lower,k.upper-arm0).min()))+u*.04
    lo[:7]=np.maximum(k.lower+margin,previous[:7]-.16);hi[:7]=np.minimum(k.upper-margin,previous[:7]+.16)
   if a.keep_thumb_pressure:
    ti=7+list(ids).index(16);hi[ti]=min(hi[ti],(1-u)*max(q0[16],hiAll[ti])+u*float(c['hand_q'][16]+.002))
   if 'planned_thumb1_upper_rad' in c and 16 in ids:
    ti=7+list(ids).index(16);upper=float(c['planned_thumb1_upper_rad'])
    hi[ti]=min(hi[ti],(1-u)*max(q0[16],upper)+u*upper)
   fit=least_squares(res,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=45,diff_step=1e-5);seed=fit.x
  L,q,F=decode(seed);T=L@F['hand_r_thumb_pad_link'];P=T[:3,:3]@m+T[:3,3];errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@mat+(L@F[n])[:3,3]-targets[n])) for n,mat in M.items()};cmd=q+load;cmd[16:]=q[16:]+load[16:]*(1-u)
  if a.keep_thumb_pressure or a.thumb_force_reference is not None:
   kp=np.array(json.loads((native_trial/'physics.json').read_text())['kp'][-4:]);J=np.empty((3,4))
   for j in range(4):
    hh=q.copy();hh[16+j]+=1e-5;TT=L@g.w.forward(hh)['hand_r_thumb_pad_link'];J[:,j]=(TT[:3,:3]@m+TT[:3,3]-P)/1e-5
   pressure_start=c.get('thumb_force_start_fraction',.7)
   blend=u if a.keep_thumb_pressure else smooth((u-pressure_start)/(1-pressure_start))
   force=np.array([0,-1.4,0]) if a.thumb_force_reference is None else np.array(a.thumb_force_reference)
   cmd[16:]+=blend*np.clip(J.T@force/kp,-.12,.12)
  cmd=np.clip(cmd,g.w.lower,g.w.upper);rows.append(dict(time_s=float(t),arm_q=(seed[:7]+armload).tolist(),hand_q=cmd.tolist()));d=dict(time_s=float(t),fraction=float(u),thumb_target_m=thumbtarget.tolist(),thumb_error_m=float(np.linalg.norm(P-thumbtarget)),support_errors_m=errors,arm_margin_rad=float(np.minimum(seed[:7]-k.lower,k.upper-seed[:7]).min()),joint_step_rad=float(abs(seed-previous).max()),self_intersections=checker.inspect(q),thumb_normal=(T[:3,:3]@localN).tolist(),planned_thumb1_rad=float(q[16]),issued_thumb1_rad=float(cmd[16]),planned_hand_q=q.tolist(),planned_arm_q=seed[:7].tolist(),expected_object_world=expectedO.tolist());D.append(d);print(json.dumps(d),flush=True)
 rows.sort(key=lambda v:v['time_s']);D.sort(key=lambda v:v['time_s'])
 out=dict(rows=rows,diagnostics=D,source=str(a.source),candidate=str(a.candidate),reverse_continuation=a.reverse_continuation,free_thumb_joint_path=a.free_thumb_joint_path,free_thumb_distal_path=a.free_thumb_distal_path,thumb_force_reference_N=a.thumb_force_reference,hand_margin_rad=a.hand_margin,knots=a.knots,world_axial_leveling_degrees=c.get('object_axial_leveling_degrees',0.),elapsed_s=time.time()-beg,scope='Actualstates only used as development motorprior; jointworldpath/retainedload, no physicalstatewriter or contactforcecontrollerinput')
 (a.output/'approach.json').write_text(json.dumps(out,indent=2));record('direct_actual_joint_approach_path_terminal',[str(a.output/'approach.json')],config={'max_thumb_error_m':max(d['thumb_error_m'] for d in D),'max_support_error_m':max(max(d['support_errors_m'].values()) for d in D),'hand_intersection_knots':sum(bool(d['self_intersections']) for d in D)},next_step='Explicitlyinspect completedpath beforelaunch; feasiblechangedactualapproach native thenpress/stroke, otherwisefirstblockedgeometry determinesnext')

if __name__=='__main__':main()
