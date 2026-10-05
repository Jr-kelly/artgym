"""Build a continuous35mm motor reference from joint wrist/contact IK.
Pure initial-estimate geometry; acquisition and limits still need certification.
"""
import argparse,json,copy
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_once_estimated_collision_geometry import build,rematch_open_preform
from scripts.wuji_traction_axial_geometry import attach_axial_jacobians

def main():
 p=argparse.ArgumentParser();p.add_argument('--preserve-authored-normal',action='store_true',help='Refine interpolated smooth pose without replacing its authored pad orientation');p.add_argument('--thumb-preload-normal-m',type=float);p.add_argument('--continuous',action='store_true');p.add_argument('--lifted-operation',action='store_true');p.add_argument('--pose',type=Path,required=True);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 plan=json.loads((a.pose/'motor-plan.json').read_text());pose=json.loads((a.pose/'contact-pose.json').read_text());estimate=plan['initial_geometry_estimate'];spec=build(estimate,a.output/'estimated-collision');g=DigitGeometry();h=g.w;w=np.array(plan['wrist_in_knife']);touch=np.array(plan['touch_q']);vertices=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);size=estimate['handle_size_WTL_m'];cap=estimate['slider_size_WTL_m'];target0=np.array([0,size[1]/2+cap[1]+.00015,-.02205+estimate['slider_contact_shift_m'][2]])
 def point(x):
  q=touch.copy();q[16:]=x;m=w@h.forward(q)['hand_r_thumb_pad_link'];v=vertices@m[:3,:3].T+m[:3,3];z=v[:,1];weight=np.exp(-(z-z.min())/.0002);return weight@v/weight.sum(),m[:3,0]
 ref=json.loads((a.base/'reference.json').read_text());ref['rows']=[];start=touch[16:].copy()
 for shift in np.linspace(0,.035,36):
  target=target0+[0,0,shift];prior=np.array([np.interp(shift,[r['shift_m'] for r in pose['rows']],[r['thumb_q'][i] for r in pose['rows']]) for i in range(4)]);start=prior.copy() if not a.continuous or shift==0 else start
  normal_target=point(prior)[1] if a.preserve_authored_normal else np.array([0,-1,0])
  if a.preserve_authored_normal:start=prior.copy()
  def residual(x):
   pos,n=point(x);return np.r_[(pos-target)*1000,(n-normal_target)*.15,(x-prior)*(.1 if a.preserve_authored_normal else .02 if a.continuous else .002)]
  fit=least_squares(residual,np.clip(start,h.lower[16:]+.006,h.upper[16:]-.006),bounds=(h.lower[16:]+.005,h.upper[16:]-.005),max_nfev=250)
  start=fit.x;pos,n=point(start);error=float(np.linalg.norm(pos-target))
  if error>=.00025:
   for seedrow in pose['rows']:
    if seedrow['shift_m']<shift:continue
    retry=least_squares(residual,np.clip(seedrow['thumb_q'],h.lower[16:]+.006,h.upper[16:]-.006),bounds=(h.lower[16:]+.005,h.upper[16:]-.005),max_nfev=250)
    rp,rn=point(retry.x);re=float(np.linalg.norm(rp-target))
    if re<error:start=retry.x;pos,n=rp,rn;error=re
    if error<.00025:break
  ref['rows'].append(dict(shift_m=float(shift),q_thumb=start.tolist(),point_error_m=error,point_initial_estimate_m=pos.tolist(),authored_front_cosine=float(-n[1]),feasible=error<.00025))
 ref.update(command_travel_m=.035,all_feasible=all(r['feasible'] for r in ref['rows']),all_feasible_scope='Dense initial-estimate IK only; original-limit and geometry certificates pending',posture_preload=False,known_motor_anchor=True)
 # Starting pose is refined by the same solve; retain previous finite preload.
 preload=np.array(plan['close_q'])-touch;opening=np.array(plan['open_q'])-touch;touch[16:]=ref['rows'][0]['q_thumb'];plan['touch_q']=touch.tolist()
 if a.thumb_preload_normal_m is not None:
  assert 0<=a.thumb_preload_normal_m<=.001
  pos0,normal0=point(touch[16:]);target=pos0+np.array([0,-a.thumb_preload_normal_m,0]);prior=touch[16:].copy()
  def preload_residual(x):
   pos,n=point(x);return np.r_[(pos-target)*1000,(n-normal0)*.1,(x-prior)*.01]
  fit=least_squares(preload_residual,np.clip(prior,h.lower[16:]+.006,h.upper[16:]-.006),bounds=(h.lower[16:]+.005,h.upper[16:]-.005),max_nfev=250);pos,_=point(fit.x);assert np.linalg.norm(pos-target)<.00005
  preload[16:]=fit.x-touch[16:];plan['thumb_geometric_preload']=dict(normal_displacement_m=a.thumb_preload_normal_m,point_error_m=float(np.linalg.norm(pos-target)),scope='Initial-estimate geometric preloaddemand only, not actual indentation/force; replaces unrelated oldgrip jointdelta')
 plan['close_q']=np.clip(touch+preload,h.lower+.005,h.upper-.005).tolist();plan['open_q']=np.clip(touch+opening,h.lower+.005,h.upper-.005).tolist();plan['close_waypoints']=[dict(fraction=0.,q=plan['open_q']),dict(fraction=2/3,q=plan['touch_q']),dict(fraction=1.,q=plan['close_q'])];plan=rematch_open_preform(plan,spec)
 loc=json.loads((a.base/'localization.json').read_text());world=np.array(loc['object_world_matrix']);kin=G2Kinematics();armworld=world.copy()
 if a.lifted_operation:armworld[2,3]+=.1
 arm,error=kin.solve(armworld@w,np.array(loc['grasp_q']));loc['grasp_q']=arm.tolist();plan.update(arm_grasp_q=arm.tolist(),arm_ik=error,object_world_matrix=world.tolist());relative=np.linalg.inv(w);cap0=np.eye(4);cap0[:3,3]=[0,.0075,-.02205];cal=dict(object_in_wrist=relative.tolist(),slider_in_wrist=(relative@cap0).tolist(),initial_geometry_estimate=estimate,scope='Once-estimated prior, actor applies dimension delta once; no running physical truth')
 ref=attach_axial_jacobians(plan,ref);audit=dict(source=str(a.pose),arm_ik=error,all_reference_ik_passed=ref['all_feasible'],maximum_reference_error_m=max(r['point_error_m'] for r in ref['rows']),minimum_front_cosine=min(r['authored_front_cosine'] for r in ref['rows']),scope=__doc__)
 for name,value in [('motor-plan.json',plan),('reference.json',ref),('localization.json',loc),('calibration.json',cal),('adaptation-audit.json',audit)]:
  (a.output/name).write_text(json.dumps(value,indent=2))
 print(json.dumps(audit));assert ref['all_feasible'] and error['position_m']<.001 and error['rotation_rad']<.02
if __name__=='__main__':main()
