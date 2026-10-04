"""Common initial-estimate adaptation of actual pickup and postlift motor path.

No physical asset ID, current object state, contacts or force is read. This
retains known arm poses up to estimated table-height change and adapts each
hand waypoint to the same noisy dimensional/slider observation. Passing the
motor checks does not establish contact retention or successful operation.
"""
import argparse,copy,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_table_collision import ArmTableCollision
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--coarse-slider-placement',action='store_true',help='Move known wrist path toward initially estimated cap before residual IK; support points remain tied to body, not live slider');p.add_argument('--table-edge-inset',type=float,help='Known permitted tabletop knife COM inset, positive metres, applied before episode only');p.add_argument('--estimate',type=Path,required=True);p.add_argument('--pickup-plan',type=Path,required=True);p.add_argument('--operation-plan',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--transfer',type=Path,required=True);p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 estimate=json.loads(a.estimate.read_text());pickup=json.loads(a.pickup_plan.read_text());operation=json.loads(a.operation_plan.read_text());reference=json.loads(a.reference.read_text());transfer=json.loads(a.transfer.read_text());acquisition=json.loads(a.acquisition.read_text());localization=json.loads(a.localization.read_text());g=DigitGeometry();h=g.w;k=G2Kinematics();root=Path(__file__).resolve().parents[1]
 initial_rotation=np.asarray(localization['object_world_matrix'])[:3,:3];coarse_local=np.asarray(estimate['slider_contact_shift_m'])+np.array([0,(estimate['handle_size_WTL_m'][1]-.012)/2,0]) if a.coarse_slider_placement else np.zeros(3);coarse_world=initial_rotation@coarse_local
 pickup_estimate=copy.deepcopy(estimate);pickup_estimate['initial_object_center_shift_knife_m']=(-coarse_local).tolist();pickup['wrist_in_knife']=np.asarray(pickup['wrist_in_knife']).copy();pickup['wrist_in_knife'][:3,3]+=coarse_local;pickup['wrist_in_knife']=pickup['wrist_in_knife'].tolist()
 op_coarse=np.asarray(transfer['expected_knife_world'])[:3,:3].T@coarse_world;operation['wrist_in_knife']=np.asarray(operation['wrist_in_knife']).copy();operation['wrist_in_knife'][:3,3]+=op_coarse;operation['wrist_in_knife']=operation['wrist_in_knife'].tolist();operation_estimate=copy.deepcopy(estimate);operation_estimate['initial_object_center_shift_knife_m']=(-op_coarse).tolist()
 adapted_pickup,_,_,pickup_audit=adapt(pickup_estimate,copy.deepcopy(pickup),{'post_lift_target_q':pickup['close_q']},copy.deepcopy(reference),support_surface_scaling=True,geometry=g)
 adapted_operation,_,adapted_reference,operation_audit=adapt(operation_estimate,copy.deepcopy(operation),{'post_lift_target_q':operation['close_q']},copy.deepcopy(reference),support_surface_scaling=True,geometry=g)
 dz=(estimate['handle_size_WTL_m'][1]-.012)/2
 outward=0. if a.table_edge_inset is None else .3+a.table_edge_inset-localization['object_world_matrix'][0][3]
 if a.table_edge_inset is not None:assert 0<a.table_edge_inset<=.01
 body_shift=np.array([outward,0,dz]);localization['object_world_matrix'][2][3]+=dz;localization['object'][2]+=dz;localization['object_world_matrix'][0][3]+=outward;localization['object'][0]+=outward
 expected=np.asarray(transfer['expected_knife_world']).copy();expected[:3,3]+=body_shift;transfer['expected_knife_world']=expected.tolist()
 arm_checks=[]
 def shifted_arm(q):
  q=np.asarray(q);pose=k.forward(q);pose[:3,3]+=body_shift+coarse_world;new,error=k.solve(pose,q);arm_checks.append(error);return new
 for field in ['approach_q','lift_q']:acquisition[field]=[shifted_arm(q).tolist() for q in acquisition[field]]
 for field in ['start_wrist_world','grasp_wrist_world','lift_wrist_world']:
  if field in acquisition:
   mat=np.asarray(acquisition[field]);mat[:3,3]+=body_shift+coarse_world;acquisition[field]=mat.tolist()
 new_arm=np.asarray([shifted_arm(q) for q in transfer['arm_q']]);new_hand=[];waypoint_errors=[]
 nominal_expected=np.asarray(json.loads(a.transfer.read_text())['expected_knife_world']);inverse=np.linalg.inv(nominal_expected)
 one_reference=dict(reference,rows=[reference['rows'][0]])
 for aq,q in zip(transfer['arm_q'],transfer['hand_q']):
  plan=copy.deepcopy(operation);nominal_wrist=inverse@k.forward(np.asarray(aq));nominal_wrist[:3,3]+=op_coarse;plan.update(wrist_in_knife=nominal_wrist.tolist(),touch_q=q,close_q=q,open_q=q)
  adapted,_,_,audit=adapt(operation_estimate,plan,{'post_lift_target_q':q},copy.deepcopy(one_reference),support_surface_scaling=True,geometry=g)
  new_hand.append(np.clip(adapted['close_q'],h.lower+.005,h.upper-.005).tolist());waypoint_errors.append(audit['contact_errors_m'])
 for plan in [adapted_pickup,adapted_operation]:
  plan['initial_geometry_estimate']=estimate;plan['close_q']=np.clip(plan['close_q'],h.lower+.005,h.upper-.005).tolist();plan['close_waypoints'][-1]['q']=plan['close_q']
 mapping=np.linalg.inv(k.forward(new_arm[-1]));old_arm=k.forward(np.asarray(transfer['arm_q'][-1]));body_transform=np.eye(4);body_transform[:3,3]=body_shift
 for key in ['object_in_wrist','slider_in_wrist']:transfer[key]=(mapping@body_transform@old_arm@np.asarray(transfer[key])).tolist()
 adapted_reference['initial_geometry_estimate']=estimate
 new_hand=np.asarray(new_hand);new_hand[0]=adapted_pickup['close_q'];transfer.update(arm_q=new_arm.tolist(),hand_q=new_hand.tolist(),initial_geometry_estimate=estimate,contact_continuity_verified=False)
 xml=ET.parse(root/h.config['asset']);velocities={j.get('name'):float(j.find('limit').get('velocity')) for j in xml.findall('joint') if j.get('type')=='revolute'};limits=np.array([velocities[n] for n in h.names]);rates=abs(np.diff(new_hand,axis=0))/np.diff(transfer['times_s'])[:,None]
 collision=ArmTableCollision(.75);geometry_rows=[];arm_table_rows=[]
 arm_sequences=[]
 for field,seconds in [('approach_q',3.),('lift_q',4.)]:
  path=np.asarray(acquisition[field]);u=np.linspace(0,1,round(seconds*30)+1);fraction=u*u*u*(10-15*u+6*u*u);samples=np.array([[np.interp(f*(len(path)-1),np.arange(len(path)),path[:,j]) for j in range(7)] for f in fraction]);arm_sequences.append(samples)
 arm_sequences.append(new_arm)
 for segment,samples in enumerate(arm_sequences):
  for i,q in enumerate(samples):
   hits=collision.collisions(q)
   if hits:arm_table_rows.append(dict(segment=segment,frame=i,collisions=hits))
 arm_rate_ok=all(np.all(abs(np.diff(samples,axis=0))*30<k.velocity[None]) for samples in arm_sequences)
 # Screen the adapted actual closure and transfer using the same original
 # authored meshes. We do not inherit nominal self/table certificates.
 poses=[]
 grasp_arm=np.asarray(acquisition['approach_q'][-1]);way=adapted_pickup['close_waypoints']
 for first,last in zip(way[:-1],way[1:]):
  for u in np.linspace(0,1,7):poses.append(('closure',grasp_arm,(1-u)*np.asarray(first['q'])+u*np.asarray(last['q'])))
 for i in np.unique(np.linspace(0,len(new_hand)-1,17).astype(int)):poses.append(('transfer',new_arm[i],new_hand[i]))
 for phase,aq,q in poses:
  wrist=k.forward(aq);frames=h.forward(q);gaps=[]
  for name,meshes in g.meshes.items():
   frame=wrist@frames[name]
   for v,n in meshes:
    vv=v@frame[:3,:3].T+frame[:3,3];axes=np.r_[np.eye(3),n@frame[:3,:3].T];proj=(vv-np.array([.6,-.25,.725]))@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);gaps.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max()))
  bad=[r for f in FINGERS for r in g.self_gaps(q,f,certify_clearance_m=.000015) if r['gap_lower_bound_m']<.000015-1e-7]
  geometry_rows.append(dict(phase=phase,minimum_table_gap_m=min(gaps),uncertified_self_pairs=bad))
 rate_ok=bool(np.all(rates<limits[None]));geometry_ok=all(r['minimum_table_gap_m']>.0003 and not r['uncertified_self_pairs'] for r in geometry_rows);ik_ok=all(r['position_m']<.003 and r['rotation_rad']<.02 for r in arm_checks)
 passed=bool(rate_ok and geometry_ok and ik_ok and arm_rate_ok and not arm_table_rows and adapted_reference['all_feasible']);transfer.update(preflight_passed=passed,hand_original_velocity_limits_passed=rate_ok,maximum_hand_command_rates_rad_s=rates.max(0).tolist(),sampled_geometry=geometry_rows,initial_geometry_adaptation_scope=__doc__)
 audit=dict(scope=__doc__,coarse_slider_placement=a.coarse_slider_placement,coarse_wrist_shift_world_m=coarse_world.tolist(),known_initial_body_shift_world_m=body_shift.tolist(),table_edge_inset_m=a.table_edge_inset,no_physical_asset_read=True,estimate=estimate,preflight_passed=passed,hand_rate_ok=rate_ok,hand_geometry_ok=geometry_ok,arm_ik_ok=ik_ok,arm_rate_ok=bool(arm_rate_ok),arm_swept_table_recertified=not arm_table_rows,arm_table_collisions=arm_table_rows,pickup=pickup_audit,operation=operation_audit,waypoint_errors=waypoint_errors,geometry=geometry_rows)
 for name,value in [('pickup-plan.json',adapted_pickup),('operation-plan.json',adapted_operation),('reference.json',adapted_reference),('transfer.json',transfer),('acquisition.json',acquisition),('localization.json',localization),('audit.json',audit)]:
  (a.output/name).write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(preflight_passed=passed,hand_geometry_ok=geometry_ok,rate_ok=rate_ok,arm_ik_ok=ik_ok,reference_ok=adapted_reference['all_feasible'])))
 assert passed,'Adapted pickup/transfer rejected; do not execute'

if __name__=='__main__':main()
