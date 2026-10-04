"""Continuous table pickup and manipulation; one initial state write only.
G2 scripted joint-space approach/closure/lift, then legal-input R800. Reuses G2 URDF/name mapping/kinematics and current student interface.
No object constraint, slider drive, interstage state reset or truth-triggered switch.
"""
import argparse,json,time,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from isaacgym import gymapi,gymtorch
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from omegaconf import OmegaConf
from scripts.wuji_goal_common import configuration
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_r800_policy import G2R800Policy
R=Path(__file__).resolve().parents[1]
def smooth(x):x=np.clip(x,0,1);return x*x*x*(10-15*x+6*x*x)
def gt(t):
 p=gymapi.Transform();p.p=gymapi.Vec3(*t[:3,3]);p.r=gymapi.Quat(*Rotation.from_matrix(t[:3,:3]).as_quat());return p

def main():
 p=argparse.ArgumentParser();p.add_argument('--proximal-friction',type=float,help='Explicit assumed link/palm friction distinctfromdistalpad; unknownmaterial sensitivity, no increasedgeometry/actuatorforce');p.add_argument('--opposing-test-load-mode',choices=['constant-countercommand','slip-gated'],default='constant-countercommand',help='Diagnostic dynamometer load always opposes requested direction; positive work during reverse slip goes away from goal. Native guide remains passive. slip-gated retained only for preliminary test comparison.');p.add_argument('--opposing-axial-test-load',type=float,default=0.,help='Known balanced body/slider axial test force opposing requested direction; evaluation-only task load, not measured thumb force. Mode determines activation.');p.add_argument('--serial-load-cell-diagnostic',action='store_true',help='Modified series-elastic slider diagnostic only; requires calibrated960Hz asset, never original-task direct force measurement');p.add_argument('--wrap-contact-measurement',action='store_true',help='Evaluation-only complete240Hz actual contact locations by link; normals only, not axial total force');p.add_argument('--support-acquisition-config',type=Path,help='Finite postlift measured-joint/previous-issued-target tracking search, original certified corridor; frozen before50 actualhistoryframes, not forcefeedback');p.add_argument('--postlift-regrasp',type=Path,help='Once-loaded known-clock arm/hand motor path after actual pickup, ending before50 constant historyframes; no object-truth trigger/state reset');p.add_argument('--measured-resistance-profile',type=Path,help='Explicit once-loaded fitted bidirectional passive brake-capacity file, physics only; no actor/profile-ID input, reject positions outside measured support');p.add_argument('--held-diagnostic',action='store_true',help='Explicit submodule only: initialize a free-floating knife and closed hand at lifted nominal pose before first simulation; original gravity/contact/limits, no later state writes; never a continuous pickup success');p.add_argument('--wrist-roll-reference-degrees',type=float,default=0.,help='Development motor-only wrist reference: bounded +/-4deg about estimatedknife longaxis, ramps16--18s afteractualpickup; no liveobject/contactinput');p.add_argument('--output',type=Path,required=True);p.add_argument('--support-residual-scale-override',type=float,help='Explicit bounded-offset checkpoint support amplitude inradians, atmost original.04span; originalmotor/effortlimits unchanged');p.add_argument('--truth-body-roll-diagnostic',action='store_true',help='ONE explicitly non-deployable body-orientation truth diagnostic, bounded originalsupportcommands; never counted as deployable demo');p.add_argument('--video',action='store_true');p.add_argument('--middle-load-lag-regulation',action='store_true',help='Scriptoperationonly: boundedmiddlemotor adaptation frommeasuredjoint-minusactualissuedtarget, notforcefeedback');p.add_argument('--middle-deflection-support',type=Path,help='Certifiedpostliftproprioceptive supportsearch; measuredq/knownmotortargetonly; endsbefore50realholdframes');p.add_argument('--contact-import-audit',action='store_true',help='Evaluation-only nativecollision shapeproperties andall contactcandidates, includingzero-normal-force records');p.add_argument('--collision-geometry-video',action='store_true',help='Render importedcollision geometry for actualcontact diagnostics; physics unchanged');p.add_argument('--seconds',type=float,default=36);p.add_argument('--table-height',type=float,default=.75);p.add_argument('--dx',type=float,default=0);p.add_argument('--dy',type=float,default=0);p.add_argument('--yaw',type=float,default=0);p.add_argument('--close-height',type=float,default=0);p.add_argument('--load',type=float,default=0);p.add_argument('--grasp-plan',type=Path);p.add_argument('--slider-face',choices=['up','down'],default='up');p.add_argument('--arm-seed',type=Path);p.add_argument('--grasp-only',action='store_true');p.add_argument('--handover-calibration',type=Path,help='Fixed prior/offline hand-object calibration, loaded once before episode; no live object or slider truth');p.add_argument('--table-calibration',type=Path);p.add_argument('--cartesian-path',type=Path);p.add_argument('--acquisition-path',type=Path);p.add_argument('--thumb-action-gain',type=float,default=1.);p.add_argument('--support-action-gain',type=float,default=1.);p.add_argument('--residual-checkpoint',type=Path);p.add_argument('--detent',type=float,default=0.);p.add_argument('--variable-load',action='store_true');p.add_argument('--thumb-script',type=Path,help='Offline calibrated thumb joint path with scheduled commands and original legal action memory; no live slider/contact feedback');p.add_argument('--knife-asset',type=Path,default=Path('assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf'),help='Physical asset only; policy keeps nominal calibrated geometry, no asset ID input');p.add_argument('--hand-friction',type=float,default=1.);p.add_argument('--knife-friction',type=float,default=3.);p.add_argument('--load-profile',choices=['constant','sinusoidal','triangular','pulse']);p.add_argument('--load-frequency',type=float,default=1.7);p.add_argument('--observation-noise',type=float,default=0.);p.add_argument('--observation-bias',type=float,default=0.);p.add_argument('--seed',type=int,default=2026100301);p.add_argument('--physics-hz',type=int,choices=[240,480,960],default=240,help='Passive resistance/contact integration rate; original motor PD remains240Hz and legal policy/history30Hz');p.add_argument('--takeover-seconds',type=float,default=16.,help='Learned residual begins at8–16s during lift or hold; operation remains16–36s, no history/physical reset');p.add_argument('--pair-force-measurement',action='store_true',help='Evaluation only: calibrated pair forces every physical step, 30Hz averages');p.add_argument('--support-pressure-config',type=Path,help='Nominal motor support/preload transition; measured/known inputs only');p.add_argument('--resistance-integration',choices=['legacy-explicit','solver-brake'],default='legacy-explicit',help='Calibrated passive zero-velocity railbrake; finitecapacity, no commanded slider motion');p.add_argument('--thumb-reference-override',type=Path,help='Fixed nominal scheduled reference/pacing specification; same frozen actor, explicit development modification');p.add_argument('--actuation-delay-frames',type=int,choices=[0,1],default=0,help='Unknown physical target delay in30Hz frames; legal history retains the actually issued command');p.add_argument('--proprioceptive-pressure-config',type=Path,help='Bounded motoradjustment fromestimated normaljointdeflection; noforcesensor/contact input');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 learned_prefix=bool(a.residual_checkpoint and (torch.load(a.residual_checkpoint,map_location='cpu').get('scene_spec') or {}).get('learned_acquisition_prefix',False))
 resistance_profile=json.loads(a.measured_resistance_profile.read_text()) if a.measured_resistance_profile else None
 if resistance_profile:
  assert a.resistance_integration=='solver-brake' and resistance_profile['format']=='wuji-passive-resistance-profile-v1'
  assert set(resistance_profile['directions'])=={'extend','retract'}
 rng=np.random.default_rng(a.seed);sensor_bias=rng.uniform(-a.observation_bias,a.observation_bias,20);knife_path=R/a.knife_asset;knife_parameters=json.loads((knife_path.parent/'parameters.json').read_text());cell_spec=knife_parameters.get('serial_load_cell') if a.serial_load_cell_diagnostic else None
 if a.serial_load_cell_diagnostic:assert cell_spec and a.physics_hz==960 and a.resistance_integration=='solver-brake'
 else:assert 'serial_load_cell' not in knife_parameters,'Diagnostic asset requires explicit label'
 load_profile=a.load_profile or ('sinusoidal' if a.variable_load else 'constant')
 assert a.hand_friction>=0 and a.knife_friction>=0 and a.observation_noise>=0 and a.observation_bias>=0
 initial_estimate=json.loads(a.grasp_plan.read_text()).get('initial_geometry_estimate') if a.grasp_plan else None
 estimated_geometry=list(initial_estimate['handle_size_WTL_m'])+initial_estimate.get('slider_size_WTL_m',[.01,.003,.03]) if initial_estimate else None
 cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
 policy=G2R800Policy(cfg,R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',geometry=estimated_geometry,thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,residual_checkpoint=a.residual_checkpoint,thumb_reference_override=a.thumb_reference_override,support_residual_scale_override=a.support_residual_scale_override);kin=G2Kinematics()
 seed=np.load(R/'research/robust-knife-family-20261003/data/repaired-seeds.npy')[1];relative=transform(seed[40:43],seed[43:47]);closed=seed[20:40].copy();opened=np.clip(closed*.30,policy.fk.lower,policy.fk.upper);opened[16:]=np.clip(closed[16:]-[.35,0,.25,0],policy.fk.lower[16:],policy.fk.upper[16:])
 if a.grasp_plan:
  plan=json.loads(a.grasp_plan.read_text());relative=np.linalg.inv(np.asarray(plan['wrist_in_knife']));closed=np.asarray(plan['close_q']);opened=np.asarray(plan['open_q'])
 operating_closed=np.asarray(plan.get('post_lift_close_q',closed)) if a.grasp_plan else closed.copy()
 regrasp=json.loads(a.postlift_regrasp.read_text()) if a.postlift_regrasp else None
 if regrasp:
  assert regrasp['preflight_passed'] and not a.held_diagnostic and not a.support_pressure_config and not a.middle_deflection_support and a.takeover_seconds==16
  regrasp_times=np.asarray(regrasp['times_s']);regrasp_hand=np.asarray(regrasp['hand_q']);regrasp_arm=np.asarray(regrasp['arm_q'])
  assert 12<=regrasp_times[0]<regrasp_times[-1]<=16-50/30 and regrasp_hand.shape==(len(regrasp_times),20) and regrasp_arm.shape==(len(regrasp_times),7)
  assert np.max(abs(regrasp_hand[0]-closed))<1e-6
  operating_closed=regrasp_hand[-1].copy()
 support_spec=json.loads(a.support_pressure_config.read_text()) if a.support_pressure_config else None
 if support_spec:
  assert a.grasp_plan
  if a.takeover_seconds<16:
   completed=max(support_spec["transition_seconds"][-1],support_spec.get("motor_waypoints",[dict(time_s=0)])[-1]["time_s"])
   assert a.takeover_seconds>=completed+2/30,"Learned preparation must follow the complete planned support transfer"
  first,last=support_spec['transition_seconds'];assert 12<=first<last<=16-50/30
  operating_closed=np.array(support_spec.get('post_lift_target_q',closed),dtype=float)
  assert operating_closed.shape==(20,)
  if support_spec.get('ring_target_q') is not None:operating_closed[12:16]=np.array(support_spec['ring_target_q'])
  operating_closed[16:]+=np.array(support_spec.get('thumb_preload_delta_q',[0,0,0,0]))
  assert np.all(operating_closed>=policy.fk.lower) and np.all(operating_closed<=policy.fk.upper)
 post_lift_interval=plan.get('post_lift_preload_seconds') if a.grasp_plan else None
 lift_preload_height=plan.get('lift_preload_height_m') if a.grasp_plan else None
 assert (5 if learned_prefix else 8)<=a.takeover_seconds<=16 and abs(a.takeover_seconds*30-round(a.takeover_seconds*30))<1e-6
 if a.takeover_seconds<16:
  assert a.residual_checkpoint and not a.thumb_script and not lift_preload_height
  assert learned_prefix or not post_lift_interval or a.takeover_seconds>=post_lift_interval[-1]+2/30,'Learned preparation must not interrupt planned postlift transfer'
 if lift_preload_height:assert a.acquisition_path and not post_lift_interval and 0<=lift_preload_height[0]<lift_preload_height[1]<=.10
 if post_lift_interval:
  assert (a.acquisition_path or a.held_diagnostic) and 12<=post_lift_interval[0]<post_lift_interval[1]<=16-50/30,'Post-lift preload must leave50 real constant-target frames before policy takeover'
 support_acquisition=None
 if a.support_acquisition_config:
  assert a.grasp_plan and a.takeover_seconds==16 and not a.held_diagnostic and not a.middle_deflection_support and not a.support_pressure_config
  from scripts.wuji_joint_deflection_acquisition import JointDeflectionAcquisition
  acquisition_spec=json.loads(a.support_acquisition_config.read_text());assert acquisition_spec['motor_plan_sha256']==hashlib.sha256(a.grasp_plan.read_bytes()).hexdigest()
  assert not post_lift_interval or acquisition_spec['search_interval_seconds'][0]>=post_lift_interval[-1]+.2
  support_acquisition=JointDeflectionAcquisition(acquisition_spec,operating_closed)
 middle_support=None;middle_regulator=None
 if a.middle_load_lag_regulation:assert a.middle_deflection_support and a.thumb_script and not a.residual_checkpoint
 if a.middle_deflection_support:
  from scripts.g2_middle_deflection_support import MiddleDeflectionSupport
  middle_spec=json.loads(a.middle_deflection_support.read_text());assert a.grasp_plan and not post_lift_interval and not lift_preload_height and a.takeover_seconds==16
  assert middle_spec['pickup_plan_sha256']==hashlib.sha256(a.grasp_plan.read_bytes()).hexdigest()
  middle_support=MiddleDeflectionSupport(middle_spec,closed)
 thumb_script=None
 if a.thumb_script:
  assert a.grasp_plan and not a.residual_checkpoint
  thumb_script=json.loads(a.thumb_script.read_text());script_shifts=np.array([r['shift_m'] for r in thumb_script['rows']]);script_q=np.array([r['q_thumb_preloaded'] if thumb_script.get('posture_preload') else r['q_thumb'] for r in thumb_script['rows']]);assert np.isclose(script_shifts[0],0) and np.isclose(script_shifts[-1],.04)
  if thumb_script.get('posture_preload'):assert thumb_script['motor_geometry_passed'],'Rejected nominal motor geometry'
  script_preload=operating_closed[16:]-(script_q[0] if thumb_script.get('posture_preload') or thumb_script.get('known_motor_anchor') else np.asarray(plan['touch_q'])[16:]);script_travel_seconds=float(thumb_script.get('travel_seconds',3.));assert 0<script_travel_seconds<5.
 policy_relative=relative.copy();policy_slider_estimate=None;handover_calibration=None
 if a.handover_calibration:
  handover_calibration=json.loads(a.handover_calibration.read_text());policy_relative=np.asarray(handover_calibration['object_in_wrist']);policy_slider_estimate=np.asarray(handover_calibration['slider_in_wrist']);assert policy_relative.shape==(4,4) and policy_slider_estimate.shape==(4,4)
 if regrasp:
  assert not a.handover_calibration,'Regrasp supplies its own fixed nominal operation estimate'
  policy_relative=np.asarray(regrasp['object_in_wrist']);policy_slider_estimate=np.asarray(regrasp['slider_in_wrist'])
 if initial_estimate:
  center_delta=np.asarray(initial_estimate.get('initial_object_center_shift_knife_m',[0,0,0]))
  policy_relative=policy_relative.copy();policy_relative[:3,3]+=policy_relative[:3,:3]@center_delta
 if initial_estimate and policy_slider_estimate is not None:
  initial_delta=center_delta+np.asarray(initial_estimate['slider_contact_shift_m'])+np.array([0,(initial_estimate['handle_size_WTL_m'][1]-.012)/2,0])
  policy_slider_estimate=policy_slider_estimate.copy();policy_slider_estimate[:3,3]+=policy_relative[:3,:3]@initial_delta
 def initial_takeover_priors():
  if policy.table_initial_prior_from_measured_arm:
   from scripts.wuji_initial_table_prior import measured_arm_relative
   return measured_arm_relative(plan,initial_estimate,kin.forward(dof[arm,0].numpy()))
  return policy_relative,(policy_slider_estimate if policy_slider_estimate is not None else policy_relative@transform([0,.0075,.010624586881962734+lower]))
 if policy.support_load_features is not None:
  policy.support_load_features.reset(torch.tensor([0],device=policy.player.device),policy.tensor(policy_relative[:3,1]))
 pressure_spec=None
 if a.proprioceptive_pressure_config or policy.proprioceptive_pressure_spec:
  assert a.takeover_seconds==16 and (a.handover_calibration or regrasp) and a.residual_checkpoint and not a.thumb_script
  from scripts.wuji_proprioceptive_pressure import ProprioceptivePressure,CoordinatedProprioceptivePressure
  pressure_spec=json.loads(a.proprioceptive_pressure_config.read_text()) if a.proprioceptive_pressure_config else policy.proprioceptive_pressure_spec;assert pressure_spec['prefix_freeze_s']<=16-50/30
  adapter=CoordinatedProprioceptivePressure if pressure_spec.get('coordinate_support') else ProprioceptivePressure
  if pressure_spec.get('model_implementation')=='analytic-torch-v1':
   from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure
   adapter=NativeJointDeflectionPressure
  if pressure_spec.get('control')=='index-support-retention':
   from scripts.wuji_index_support_retention import IndexSupportRetention
   adapter=IndexSupportRetention
  if pressure_spec.get('control')=='support-moment-retention':
   from scripts.wuji_support_moment_retention import SupportMomentRetention
   policy.pressure_adapter=SupportMomentRetention(pressure_spec,policy_relative[:3,1],np.array(cfg.hand.dof_props.stiffness),np.array(cfg.hand.dof_props.damping),policy_relative)
  elif pressure_spec.get('control')=='support-load-share':
   from scripts.wuji_support_load_share import SupportLoadShare
   policy.pressure_adapter=SupportLoadShare(pressure_spec,policy_relative[:3,1],np.array(cfg.hand.dof_props.stiffness),np.array(cfg.hand.dof_props.damping))
  else:policy.pressure_adapter=adapter(pressure_spec,policy_relative[:3,1],np.array(cfg.hand.dof_props.stiffness))
 truth_body_diagnostic=None
 if a.truth_body_roll_diagnostic:
  assert a.takeover_seconds==16 and a.residual_checkpoint and not a.thumb_script and pressure_spec is None
  from scripts.wuji_truth_body_roll_diagnostic import TruthBodyRollDiagnostic
  truth_body_diagnostic=TruthBodyRollDiagnostic(policy_relative)
 def close_motor(u):
  if not a.grasp_plan or 'close_waypoints' not in plan:return opened+smooth(u)*(closed-opened)
  way=plan['close_waypoints']
  for first,last in zip(way[:-1],way[1:]):
   if u<=last['fraction']:
    alpha=smooth((u-first['fraction'])/(last['fraction']-first['fraction']));return np.asarray(first['q'])*(1-alpha)+np.asarray(last['q'])*alpha
  return closed
 def hold_motor(t,aq=None):
  if plan.get('post_lift_thumb_motor_waypoints') and t>=plan['post_lift_thumb_motor_waypoints'][0]['time_s']:
   rows=plan['post_lift_thumb_motor_waypoints'];value=closed.copy();times=[r['time_s'] for r in rows];value[16:]=[np.interp(t,times,[r['q_thumb'][i] for r in rows]) for i in range(4)];return value
  if regrasp and t>=regrasp_times[0]:return np.array([np.interp(t,regrasp_times,regrasp_hand[:,i]) for i in range(20)])
  if support_spec and support_spec.get('motor_waypoints'):
   rows=support_spec['motor_waypoints']
   if t<=rows[0]['time_s']:return np.asarray(rows[0]['q'])
   for first,last in zip(rows[:-1],rows[1:]):
    if t<=last['time_s']:
     alpha=smooth((t-first['time_s'])/(last['time_s']-first['time_s']))
     return np.asarray(first['q'])*(1-alpha)+np.asarray(last['q'])*alpha
   return np.asarray(rows[-1]['q'])
  if lift_preload_height:
   height=kin.forward(aq)[:3,3][2]-grasp[2,3]
   first,last=lift_preload_height;alpha=np.clip((height-first)/(last-first),0.,1.)
   return closed+alpha*(operating_closed-closed)
  if support_spec:
   first,last=support_spec['transition_seconds'];return closed+smooth((t-first)/(last-first))*(operating_closed-closed)
  if not post_lift_interval:return closed
  first,last=post_lift_interval
  alpha=smooth((t-first)/(last-first));bump=np.asarray(plan.get('post_lift_preparation_joint_bump_rad',[0.]*20))
  return closed+alpha*(operating_closed-closed)+np.sin(np.pi*alpha)*bump
 knife0=transform([.50+a.dx,-.30+a.dy,a.table_height+float(knife_parameters['handle_size'][1])/2+.0001],(Rotation.from_euler('z',a.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());
 if a.slider_face=='down':knife0=knife0@transform(quaternion=Rotation.from_euler('z',180,degrees=True).as_quat())
 # Model envelope placement occurs only before the episode starts.
 if a.slider_face=='down':knife0[2,3]=a.table_height+float(knife_parameters['handle_size'][1])/2+.0031
 planned_knife=np.asarray(json.loads(a.table_calibration.read_text())['object_world_matrix']) if a.table_calibration else knife0;grasp=planned_knife@np.linalg.inv(relative);grasp[2,3]+=a.close_height;above=grasp.copy();above[2,3]+=.16;lift=grasp.copy();lift[2,3]+=.16
 qabove,e1=kin.solve(above,np.asarray(json.loads(a.arm_seed.read_text())) if a.arm_seed else np.array([.3,-.3,0,-1.3,0,0,0]));qgrasp,e2=kin.solve(grasp,np.asarray(json.loads(a.arm_seed.read_text())) if a.arm_seed else qabove);qlift,e3=kin.solve(lift,qabove)
 if a.cartesian_path:
  cart=json.loads(a.cartesian_path.read_text());arm_path=np.asarray(cart['path_q']);qgrasp=arm_path[0];qabove=qlift=arm_path[-1]
  above=grasp.copy();above[2,3]+=cart['height_m'];lift=above.copy()
  def error(q,t):return dict(position_m=float(np.linalg.norm(kin.forward(q)[:3,3]-t[:3,3])),rotation_rad=float(Rotation.from_matrix(t[:3,:3].T@kin.forward(q)[:3,:3]).magnitude()))
  e1=error(qabove,above);e2=error(qgrasp,grasp);e3=error(qlift,lift)
  def path_motor(u):
   f=np.clip(u,0,1)*(len(arm_path)-1);i=min(int(f),len(arm_path)-2);return arm_path[i]*(1-(f-i))+arm_path[i+1]*(f-i)
 if a.acquisition_path:
  acquisition=json.loads(a.acquisition_path.read_text());approach_path=np.asarray(acquisition['approach_q']);lift_path=np.asarray(acquisition['lift_q']);qabove=approach_path[0];qgrasp=approach_path[-1];qlift=lift_path[-1]
  above=np.asarray(acquisition['start_wrist_world']);lift=np.asarray(acquisition['lift_wrist_world'])
  def acquisition_error(q,t):return dict(position_m=float(np.linalg.norm(kin.forward(q)[:3,3]-t[:3,3])),rotation_rad=float(Rotation.from_matrix(t[:3,:3].T@kin.forward(q)[:3,:3]).magnitude()))
  e1=acquisition_error(qabove,above);e2=acquisition_error(qgrasp,grasp);e3=acquisition_error(qlift,lift)
  def acquisition_motor(path,u):
   f=np.clip(u,0,1)*(len(path)-1);i=min(int(f),len(path)-2);return path[i]*(1-(f-i))+path[i+1]*(f-i)
 wrist_roll_curve=None
 if a.wrist_roll_reference_degrees:
  assert abs(a.wrist_roll_reference_degrees)<=4
  from scripts.wuji_bounded_wrist_roll import plan_curve,interpolate
  wrist_roll_curve=plan_curve(qlift,policy_relative,maximum_degrees=abs(a.wrist_roll_reference_degrees))
  (a.output/'wrist-roll-curve.json').write_text(json.dumps(wrist_roll_curve,indent=2))
 if a.held_diagnostic:
  assert a.grasp_plan and not a.acquisition_path and not a.cartesian_path and not a.support_pressure_config
  knife0[:3,3]+=lift[:3,3]-grasp[:3,3]
 (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True));(a.output/'plan.json').write_text(json.dumps(dict(args=vars(a),arm_above=qabove.tolist(),arm_grasp=qgrasp.tolist(),arm_lift=qlift.tolist(),ik=[e1,e2,e3],platform='G2+Wuji v1',object_initial=knife0.tolist(),relative_grasp=relative.tolist(),policy_relative_estimate=policy_relative.tolist(),handover_calibration=handover_calibration,open_q=opened.tolist(),close_q=closed.tolist(),schedule='0-2settle,2-5approach,5-8close,8-12lift,12-16hold/history,16-36 selected controller external5sopen/close',handover='Once-loaded offline hand-object geometry estimate; no live object truth fed to policy. Measured q/FK, actual command history; no state reset.'),default=str,indent=2))
 assert max(e['position_m'] for e in [e1,e2,e3])<.005,(e1,e2,e3)
 gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/a.physics_hz;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2;sp.physx.contact_offset=.001;sp.physx.rest_offset=0;sp.physx.max_depenetration_velocity=1.;sp.physx.num_threads=4
 sim=gym.create_sim(0,0 if a.video else -1,gymapi.SIM_PHYSX,sp);assert sim;plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);gym.add_ground(sim,plane);env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,2),1)
 opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=False;opt.collapse_fixed_joints=False;opt.thickness=.001;opt.use_physx_armature=True;asset=gym.load_asset(sim,str(R),'assets/robots/g2_wuji/g2_wuji.urdf',opt);robot=gym.create_actor(env,asset,gymapi.Transform(),'robot',0,0);names=gym.get_actor_dof_names(env,robot);hand=np.array([names.index(n) for n in policy.fk.names]);arm=np.array([names.index(n) for n in kin.names]);rbnames=gym.get_actor_rigid_body_names(env,robot);wrist=gym.get_actor_rigid_body_index(env,robot,rbnames.index('hand_r_base_link'),gymapi.DOMAIN_SIM);assert len(names)==27 and len(hand)==20 and len(arm)==7 and not set(hand)&set(arm);props=gym.get_actor_dof_properties(env,robot);kp=np.zeros(27);kd=np.zeros(27);arm_config=json.loads((R/'assets/robots/g2_wuji/audit.json').read_text())['active_arm'];kp[arm]=[j['stiffness'] for j in arm_config];kd[arm]=[j['damping'] for j in arm_config]
 for key in ['armature','friction']:props[key][hand]=np.asarray(cfg.hand.dof_props[key])
 kp[hand]=np.asarray(cfg.hand.dof_props.stiffness);kd[hand]=np.asarray(cfg.hand.dof_props.damping);props['armature'][arm]=.01;props['driveMode'][:]=gymapi.DOF_MODE_EFFORT;props['stiffness'][:]=0;props['damping'][:]=0;gym.set_actor_dof_properties(env,robot,props)
 shapes=gym.get_actor_rigid_shape_properties(env,robot);indices=gym.get_actor_rigid_body_shape_indices(env,robot);digits=['thumb','index','middle','ring','pinky'];allbits=sum(1<<(8+i) for i in range(5))+sum(1<<(16+i) for i in range(5))
 for name,idx in zip(rbnames,indices):
  if not name.startswith('hand_r_'):mask=(1<<7)|allbits
  elif name=='hand_r_base_link':mask=sum(1<<(16+i) for i in range(5))
  else:
   digit=next(i for i,d in enumerate(digits) if '_'+d+'_' in name);mask=1<<(8+digit)
   if name.endswith(('link1','link2')):mask|=1<<(16+digit)
  for n in range(idx.start,idx.start+idx.count):shapes[n].filter=mask;shapes[n].friction=a.hand_friction if a.proximal_friction is None or name.endswith('pad_link') else a.proximal_friction
 gym.set_actor_rigid_shape_properties(env,robot,shapes)
 opt=gymapi.AssetOptions();opt.fix_base_link=True;tableasset=gym.create_box(sim,.60,.80,.05,opt);table=gym.create_actor(env,tableasset,gt(transform([.60,-.25,a.table_height-.025])),'table',0,0)
 opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;opt.density=1000;knifeasset=gym.load_asset(sim,str(knife_path.resolve().parent),knife_path.name,opt);knife=gym.create_actor(env,knifeasset,gt(knife0),'knife',0,0);bodies=gym.get_actor_rigid_body_properties(env,knife);knife_xml=ET.parse(knife_path)
 for b,name in zip(bodies,gym.get_actor_rigid_body_names(env,knife)):
  node=knife_xml.find(f"./link[@name='{name}']/inertial");b.mass=float(node.find('mass').get('value'));v=node.find('inertia');b.inertia.x.x=float(v.get('ixx'));b.inertia.y.y=float(v.get('iyy'));b.inertia.z.z=float(v.get('izz'))
 gym.set_actor_rigid_body_properties(env,knife,bodies,False);shapes=gym.get_actor_rigid_shape_properties(env,knife)
 for s in shapes:s.friction=a.knife_friction;s.filter=1
 gym.set_actor_rigid_shape_properties(env,knife,shapes)
 if a.contact_import_audit:
  native_shapes=[]
  for label,actor in [('robot',robot),('knife',knife)]:
   body_names=gym.get_actor_rigid_body_names(env,actor);shape_indices=gym.get_actor_rigid_body_shape_indices(env,actor);properties=gym.get_actor_rigid_shape_properties(env,actor)
   for name,span in zip(body_names,shape_indices):
    for j in range(span.start,span.start+span.count):
     prop=properties[j];native_shapes.append(dict(actor=label,body=name,shape_index=j,properties={k:getattr(prop,k) for k in ['filter','friction','rolling_friction','torsion_friction','contact_offset','rest_offset','restitution','compliance','thickness'] if hasattr(prop,k)}))
  (a.output/'native-collision-shapes.json').write_text(json.dumps(native_shapes,indent=2))
 op=gym.get_actor_dof_properties(env,knife);lower=float(op['lower'][0]);op['driveMode'][:]=gymapi.DOF_MODE_EFFORT;op['stiffness'][:]=0;op['damping'][:]=.3;op['friction'][:]=.001;op['armature'][:]=.001;
 if a.resistance_integration=='solver-brake':
  op['driveMode'][:]=gymapi.DOF_MODE_VEL;op['damping'][:]=250.;op['effort'][:]=max(a.load,1e-8);gym.set_actor_dof_properties(env,knife,op);gym.set_actor_dof_velocity_targets(env,knife,np.zeros(len(op),dtype=np.float32))
 else:gym.set_actor_dof_properties(env,knife,op)
 if cell_spec:
  cell_local=gym.get_actor_dof_names(env,knife).index('serial_load_cell');op['driveMode'][cell_local]=gymapi.DOF_MODE_EFFORT;op['damping'][cell_local]=0.;op['friction'][cell_local]=0.;op['armature'][cell_local]=0.;op['effort'][cell_local]=10.;gym.set_actor_dof_properties(env,knife,op)
 ds=np.zeros(27,dtype=gymapi.DofState.dtype);ds['pos'][arm]=qlift if a.held_diagnostic else qabove;ds['pos'][hand]=np.asarray(plan['touch_q']) if a.held_diagnostic else opened;gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);os=np.zeros(len(op),dtype=gymapi.DofState.dtype);os['pos'][0]=lower;gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL)
 cam=None;writer=None
 if a.video:
  import imageio.v2 as imageio
  cp=gymapi.CameraProperties();cp.use_collision_geometry=a.collision_geometry_video;cp.width=960;cp.height=720;cam=gym.create_camera_sensor(env,cp);gym.set_camera_location(cam,env,gymapi.Vec3(1.25,-1.4,1.5),gymapi.Vec3(.4,-.3,.85));cp2=gymapi.CameraProperties();cp2.use_collision_geometry=a.collision_geometry_video;cp2.width=960;cp2.height=720;cp2.horizontal_fov=40;closecam=gym.create_camera_sensor(env,cp2);close_aim=knife0[:3,3]+np.array([0.,0.,.085]);gym.set_camera_location(closecam,env,gymapi.Vec3(*(close_aim+np.array([.34,-.12,.24]))),gymapi.Vec3(*close_aim));closewriter=imageio.get_writer(str(a.output/'hand-closeup.mp4'),fps=30,codec='libx264',quality=7);writer=imageio.get_writer(str(a.output/'continuous.mp4'),fps=30,codec='libx264',quality=7)
 gym.prepare_sim(sim);gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL);dof=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));contact=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));jac=gymtorch.wrap_tensor(gym.acquire_jacobian_tensor(sim,'robot'));oid=gym.get_actor_rigid_body_index(env,knife,0,gymapi.DOMAIN_SIM);sid=gym.get_actor_dof_index(env,knife,0,gymapi.DOMAIN_SIM);robotb=gym.get_actor_rigid_body_properties(env,robot);masses=torch.tensor([b.mass for b in robotb][1:]);force=torch.zeros(len(dof));target=torch.tensor(ds['pos'].copy());K=torch.tensor(kp,dtype=torch.float32);C=torch.tensor(kd,dtype=torch.float32);limits=torch.tensor(props['effort'].copy());limitlow=torch.tensor(props['lower'].copy());limithi=torch.tensor(props['upper'].copy());rows=[];started=time.monotonic();taken=False;operation_reference=None;max_positive_power=0.;groove_work=0.;startup_work=0.;passive_energy_error_max=0.;dissipative_work=0.;total_load_energy_residual_max=0.
 capid=gym.get_actor_rigid_body_index(env,knife,gym.get_actor_rigid_body_names(env,knife).index('link_1'),gymapi.DOMAIN_SIM)
 cell_id=gym.get_actor_dof_index(env,knife,cell_local,gymapi.DOMAIN_SIM) if cell_spec else None
 cell_stream=(a.output/'serial-load-cell-physical-steps.jsonl').open('w') if cell_spec else None
 cell_samples=[]
 test_forces=torch.zeros((len(rb),3));test_torques=torch.zeros((len(rb),3));test_stream=(a.output/'opposing-load-physical-steps.jsonl').open('w') if a.opposing_axial_test_load else None
 assert a.opposing_axial_test_load>=0 and not (cell_spec and a.opposing_axial_test_load)
 physical_target=target.clone()
 def passive_potential(travel):
  q=np.clip(travel,0,.004);start=a.detent*.004/np.pi*(1-np.cos(np.pi*q/.004));x=(travel-.021)/.0015;groove=-a.detent*.0015*.5*(1+np.cos(np.pi*x)) if abs(x)<1 else 0.;return start+groove
 potential_initial=passive_potential(0.)
 (a.output/'physics.json').write_text(json.dumps(dict(physics_hz=a.physics_hz,motor_pd_hz=240,policy_history_hz=30,robot_rigid_body_names=rbnames,robot_dof_names=names,hand_indices=hand.tolist(),arm_indices=arm.tolist(),kp=kp.tolist(),kd=kd.tolist(),effort=limits.tolist(),mass_kg=[b.mass for b in robotb],gravity='All bodies enabled; model-based robot generalized gravity compensation via arm/hand motor efforts; total torque clipped to URDF limits',controller='Explicit finite-torque PD240Hz; original hand gains retained; deployment actuator timing assumption',object=('Free floating, calibrated passive zero-velocity solverbrake capacity; no motion trajectory or grasp constraint' if a.resistance_integration=='solver-brake' else 'Free floating; original passive joint damping/friction plus optional opposing external load'),initial_state_writes_only=True,platform='G2+Wuji v1',policy_inputs='q,FK,50 actual q/action frames, issued targets and known scheduled command, once-loaded relative grip calibration; no live object/slider/contact truth'),indent=2))
 # Reuse the existing G2 contact-pair evaluation API. These values never enter control.
 from scripts.wuji_kinematics import FINGERS
 contact_names={}
 for actor in [robot,table,knife]:
  for n,name in enumerate(gym.get_actor_rigid_body_names(env,actor)):
   contact_names[gym.get_actor_rigid_body_index(env,actor,n,gymapi.DOMAIN_ENV)]=('table' if actor==table else name)
 pair_stream=(a.output/'knife-contact-pairs.jsonl').open('w')
 candidate_stream=(a.output/'native-contact-candidates.jsonl').open('w') if a.contact_import_audit else None
 def native_json(value):
  if isinstance(value,np.void) and value.dtype.names:return {key:native_json(value[key]) for key in value.dtype.names}
  if isinstance(value,np.ndarray):return value.tolist()
  if isinstance(value,np.generic):return value.item()
  return value
 (a.output/'contact-schema.json').write_text(json.dumps(dict(sample_hz=30,scope='Evaluation-only solver contacts; no policy/controller input',magnitude='RigidContact.lambda documented as contact force magnitude by installed IsaacGym Preview4; simulated solver quantity, not a measured hardware force',normal='World normal; calibrated force on body0=+lambda*normal and body1=-lambda*normal',digits=list(FINGERS),force_note='Normal solver contribution only; friction direction/total tangential force not inferred; position-target preload is not constant force'),indent=2))
 def pair_diagnostics(t):
  body_count=np.zeros(5,np.int32);slider_count=np.zeros(5,np.int32);body_magnitude=np.zeros(5);slider_magnitude=np.zeros(5)
  for c in gym.get_env_rigid_contacts(env):
   first=contact_names.get(int(c['body0']),'ground');second=contact_names.get(int(c['body1']),'ground');pair=[first,second]
   if not any(n in ['link_0','link_1'] for n in pair):continue
   if candidate_stream and t>=12:candidate_stream.write(json.dumps(dict(time_s=t,body0_name=first,body1_name=second,native=native_json(c)))+'\n')
   if c['lambda']<=1e-6:continue
   normal=c['normal'];vector=[float(normal[n]) for n in ['x','y','z']]
   pair_stream.write(json.dumps(dict(time_s=t,body0=first,body1=second,normal_world=vector,solver_lambda=float(c['lambda'])))+'\n')
   for index,finger in enumerate(FINGERS):
    if not any('_'+finger+'_' in n for n in pair):continue
    if 'link_1' in pair:slider_count[index]+=1;slider_magnitude[index]+=float(c['lambda'])
    if 'link_0' in pair:body_count[index]+=1;body_magnitude[index]+=float(c['lambda'])
  return dict(finger_body_contacts=body_count,finger_slider_contacts=slider_count,finger_body_solver_magnitude=body_magnitude,finger_slider_solver_magnitude=slider_magnitude)
 force_meter=None
 if a.pair_force_measurement or a.wrap_contact_measurement:
  if a.wrap_contact_measurement:from scripts.wuji_wrap_contact_measurement import WrapContactMeter as PairForceMeter
  else:from scripts.wuji_support_contact_measurement import PairForceMeter
  force_meter=PairForceMeter(gym,env,contact_names,a.output,1/a.physics_hz,float(knife_parameters['handle_size'][1]))
 try:
  for step in range(int(a.seconds*a.physics_hz)):
   gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_jacobian_tensors(sim);t=step/a.physics_hz
   if step%(a.physics_hz//30)==0:
    previously_issued_target=target.clone()
    q=dof[hand,0].numpy().copy()+sensor_bias+rng.normal(0.,a.observation_noise,20);act=np.zeros(20,dtype=np.float32);policy.record(q,policy.last_action if taken else act)
    if regrasp and pressure_spec is not None and pressure_spec.get('transfer_normal_from_known_arm_fk',False):
     assert (isinstance(policy.pressure_adapter,ProprioceptivePressure) or pressure_spec.get('model_implementation')=='analytic-torch-v1') and not pressure_spec.get('coordinate_support')
     fixed_knife_axis=np.asarray(regrasp['expected_knife_world'])[:3,1];measured_wrist=kin.forward(dof[arm,0].numpy());policy.pressure_adapter.normal=measured_wrist[:3,:3].T@fixed_knife_axis
    if policy.support_load_features is not None:
     policy.support_load_features.observe(policy.tensor(q),policy.tensor(previously_issued_target[hand].numpy()),torch.tensor([round(t*30)],device=policy.player.device))
    if a.held_diagnostic and t<16:aq=qlift;hq=hold_motor(t,aq)
    elif t<2:aq=qabove;hq=opened
    elif t<5:aq=acquisition_motor(approach_path,smooth((t-2)/3)) if a.acquisition_path else path_motor(1-smooth((t-2)/3)) if a.cartesian_path else qabove+smooth((t-2)/3)*(qgrasp-qabove);hq=opened
    elif t<8:
     aq=qgrasp;hq=close_motor((t-5)/3)
     if learned_prefix and not a.grasp_only and t>=a.takeover_seconds:
      if not taken:
       object_est,slider_est=initial_takeover_priors();policy.takeover_estimate(q,target[hand].numpy(),object_est,slider_est,clock_s=t);taken=True
      hq,act=policy.command(q,0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,known_prefix_target=hq)
    elif t<12:
     aq=acquisition_motor(lift_path,smooth((t-8)/4)) if a.acquisition_path else path_motor(smooth((t-8)/4)) if a.cartesian_path else qgrasp+smooth((t-8)/4)*(qlift-qgrasp);hq=hold_motor(t,aq) if lift_preload_height else closed
     if not a.grasp_only and t>=a.takeover_seconds:
      if not taken:
       object_est,slider_est=initial_takeover_priors();policy.takeover_estimate(q,target[hand].numpy(),object_est,slider_est,clock_s=t);taken=True
      hq,act=policy.command(q,0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,known_prefix_target=hq if learned_prefix else None)
    elif t<16 or a.grasp_only:
     aq=qlift;hq=hold_motor(t,aq)
     if support_acquisition:
      hq=support_acquisition.command(t,q,previously_issued_target[hand].numpy(),hq);operating_closed[support_acquisition.index]=support_acquisition.target if t>=support_acquisition.start else operating_closed[support_acquisition.index]
     if middle_support:
      hq=middle_support.command(t,q,hq);operating_closed[7]=middle_support.target
     if not a.grasp_only and t>=a.takeover_seconds:
      if not taken:
       object_est,slider_est=initial_takeover_priors();policy.takeover_estimate(q,target[hand].numpy(),object_est,slider_est,clock_s=t);taken=True
      hq,act=policy.command(q,0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,known_prefix_target=hq if learned_prefix else None)
    else:
     aq=qlift
     if not taken:
      object_est,slider_est=initial_takeover_priors();policy.takeover_estimate(q,target[hand].numpy(),object_est,slider_est,clock_s=t);taken=True;operation_reference=rb[oid].numpy().copy()
     if operation_reference is None:operation_reference=rb[oid].numpy().copy()
     if thumb_script is not None:
      phase=int((t-16)/5);fraction=smooth(min(1.,((t-16)%5)/script_travel_seconds));shift=.04*(fraction if phase%2==0 else 1-fraction)
      desired=operating_closed.copy();desired[16:]=np.array([np.interp(shift,script_shifts,script_q[:,n]) for n in range(4)])+script_preload
      if a.middle_load_lag_regulation:
       if middle_regulator is None:
        from scripts.g2_middle_deflection_support import MiddleLoadLagRegulator
        middle_regulator=MiddleLoadLagRegulator(middle_spec,middle_support.target)
       desired=middle_regulator.command(q,target[hand].numpy(),desired)
      hq,act=policy.scripted_target(desired)
     else:
      diagnostic_offset=truth_body_diagnostic.correction(q,dof[arm,0].numpy(),rb[oid,3:7].numpy()) if truth_body_diagnostic is not None else None
      hq,act=policy.command(q,.04 if int((t-16)/5)%2==0 else 0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,diagnostic_motor_offset=diagnostic_offset)
    if policy.pressure_adapter is not None and not taken and t>=8:hq=policy.pressure_adapter.command(q,target[hand].numpy(),hq,t)
    if regrasp and t>=regrasp_times[0]:aq=np.array([np.interp(t,regrasp_times,regrasp_arm[:,i]) for i in range(7)])
    if wrist_roll_curve is not None and t>=16:aq=interpolate(wrist_roll_curve,np.deg2rad(a.wrist_roll_reference_degrees)*smooth((t-16)/2))
    target[arm]=torch.tensor(aq,dtype=torch.float32);target[hand]=torch.tensor(hq,dtype=torch.float32);target=torch.minimum(torch.maximum(target,limitlow),limithi)
    physical_target=previously_issued_target if a.actuation_delay_frames else target.clone()
    # During scripted history settling, actions are the actual equivalent support/target commands (constant targets ->0).
   if step%(a.physics_hz//240)==0:
    gravity_ff=(jac[0,:,2,:]*masses[:,None]*9.81).sum(0);torque=K*(physical_target-dof[:27,0])-C*dof[:27,1]+gravity_ff;force[:27]=torch.maximum(torch.minimum(torque,limits),-limits)
   v=float(dof[sid,1]);travel=float(dof[sid,0])-lower;amplitude=a.load*(.25+.75*np.sin(a.load_frequency*t+.4)**2) if load_profile=='sinusoidal' else a.load*(.25+.75*abs(2*((a.load_frequency*t/(2*np.pi))%1)-1)) if load_profile=='triangular' else a.load*(1. if np.sin(a.load_frequency*t+.4)>.5 else .25) if load_profile=='pulse' else a.load;run_load=-amplitude*np.tanh(v/.002);start_load=-a.detent*np.sin(np.clip(travel/.004,0,1)*np.pi) if 0<=travel<=.004 else 0.;x=(travel-.021)/.0015;groove_load=-a.detent*np.pi*.5*np.sin(np.pi*x) if abs(x)<1 else 0.;load=run_load+start_load+groove_load;brake_capacity=0.
   if a.resistance_integration=='solver-brake':
    brake_capacity=amplitude+abs(start_load)+abs(groove_load)
    if resistance_profile is not None:
     from scripts.fit_wuji_passive_resistance import capacity
     brake_capacity=capacity(resistance_profile,travel,v)
    op['effort'][0]=max(brake_capacity,1e-8);gym.set_actor_dof_properties(env,knife,op);force[sid]=0.;load=0.
   else:force[sid]=load
   test_scalar=0.;test_active=False
   if test_stream and t>=16:
    intended=1 if int((t-16)/5)%2==0 else -1
    if a.opposing_test_load_mode=='constant-countercommand' or v*intended>=-1e-6:
     test_scalar=-intended*a.opposing_axial_test_load;test_active=True
    axis=Rotation.from_quat(rb[oid,3:7].numpy()).apply([0,0,1]);f=axis*test_scalar;r=rb[capid,:3].numpy()-rb[oid,:3].numpy();test_forces[:]=0;test_torques[:]=0;test_forces[capid]=torch.tensor(f,dtype=torch.float32);test_forces[oid]=torch.tensor(-f,dtype=torch.float32);test_torques[oid]=torch.tensor(np.cross(r,-f),dtype=torch.float32);gym.apply_rigid_body_force_tensors(sim,gymtorch.unwrap_tensor(test_forces),gymtorch.unwrap_tensor(test_torques),gymapi.ENV_SPACE)
   if cell_spec:
    cap_velocity_before=rb[capid,7:10].numpy().copy();cell_q_before=float(dof[cell_id,0]);cell_v_before=float(dof[cell_id,1]);spring_force=-cell_spec['spring_N_per_m']*cell_q_before-cell_spec['damper_N_s_per_m']*cell_v_before;force[cell_id]=np.clip(spring_force,-10,10)
   max_positive_power=max(max_positive_power,run_load*v);gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(force));gym.simulate(sim);gym.fetch_results(sim,True)
   gym.refresh_dof_state_tensor(sim);next_travel=float(dof[sid,0])-lower;delta_travel=next_travel-travel;groove_work+=groove_load*delta_travel;startup_work+=start_load*delta_travel;dissipative_work+=run_load*delta_travel;passive_energy_error=groove_work+startup_work+passive_potential(next_travel)-potential_initial;passive_energy_error_max=max(passive_energy_error_max,passive_energy_error);total_load_energy_residual_max=max(total_load_energy_residual_max,passive_energy_error+dissipative_work)
   if test_stream:
    test_stream.write(json.dumps(dict(requested_direction=(1 if int((t-16)/5)%2==0 else -1) if t>=16 else 0,test_load_mode=a.opposing_test_load_mode,time_s=t+1/a.physics_hz,applied_axial_test_force_N=test_scalar,active=test_active,relative_velocity_before_m_s=v,relative_velocity_after_m_s=float(dof[sid,1]),relative_displacement_m=delta_travel,work_J=test_scalar*delta_travel,scope='Known dynamometer force always opposes requested goal; not measuredthumbforce or nativebrakecapacity. Balancedslider/body reaction including moment; no netholder. Positivework may occurduring reverse/wrong-direction motion and cannot aid desiredstroke. Native guide brake unchangedpassive. slip-gated preliminarymode disablesreverse load; report coverage.'))+'\n')
   if cell_spec:
    gym.refresh_rigid_body_state_tensor(sim);axis=Rotation.from_quat(rb[oid,3:7].numpy()).apply([0,0,1]);acc=(rb[capid,7:10].numpy()-cap_velocity_before)*a.physics_hz;inferred=cell_spec['cap_mass_kg']*float(acc@axis)-cell_spec['cap_mass_kg']*float(np.array([0,0,-9.81])@axis)-float(force[cell_id]);cell_value=dict(time_s=t+1/a.physics_hz,spring_applied_N=float(force[cell_id]),inferred_all_external_cap_axial_N=inferred,cell_q_m=float(dof[cell_id,0]),cell_v_m_s=float(dof[cell_id,1]),rail_guide_position_m=float(dof[sid,0])-lower,rail_guide_velocity_m_s=float(dof[sid,1]),cap_world_velocity_m_s=rb[capid,7:10].numpy().tolist(),cap_world_acceleration_axis_m_s2=float(acc@axis),valid_no_cell_endstop=abs(float(dof[cell_id,0]))<.0019,scope='Modified serial diagnostic cap totalexternal axialforce; thumb-only attribution requires actual pair check. Not originaltaskdirect sensor/hardware force.');partners=[]
    for contact_record in gym.get_env_rigid_contacts(env):
     if float(contact_record['lambda'])<=1e-6:continue
     a0,a1=int(contact_record['body0']),int(contact_record['body1'])
     if contact_names.get(a0)=='link_1':partners.append(contact_names.get(a1,'ground'))
     elif contact_names.get(a1)=='link_1':partners.append(contact_names.get(a0,'ground'))
    thumb_only=bool(partners) and all('_thumb_' in n for n in partners);cell_value.update(cap_contact_partners_all=partners,thumb_only_contact=thumb_only,diagnostic_thumb_axial_N=inferred if thumb_only and cell_value['valid_no_cell_endstop'] else None);cell_stream.write(json.dumps(cell_value)+'\n');cell_samples.append(inferred)
   if force_meter:
    gym.refresh_rigid_body_state_tensor(sim);force_meter.sample(t+1/a.physics_hz,rb.numpy())
   if step%(a.physics_hz//30)==a.physics_hz//30-1:
    gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim);row=dict(observed_q=q.copy(),desired_script_shift_m=shift if taken and thumb_script is not None else np.nan,time=t+1/a.physics_hz,q=dof[hand,0].numpy().copy(),arm_q=dof[arm,0].numpy().copy(),target=target.numpy().copy(),applied_target=physical_target.numpy().copy(),action=act.copy(),raw_base_action=policy.last_raw_action.copy() if taken else np.zeros(20,dtype=np.float32),object=rb[oid].numpy().copy(),wrist=rb[wrist].numpy().copy(),slider=float(dof[sid,0]),slider_velocity=float(dof[sid,1]),load=load,dissipative_load=run_load,passive_groove_load=start_load+groove_load,torque=force[:27].numpy().copy(),hand_contact=contact[:len(rbnames)].numpy().copy(),knife_contact=contact[[oid,capid]].numpy().copy(),pad_poses=rb[[rbnames.index('hand_r_'+finger+'_pad_link') for finger in ['thumb','index','middle','ring','pinky']]].numpy().copy(),estimated_thumb_pressure_N=policy.pressure_adapter.last_estimate if policy.pressure_adapter is not None else np.nan,proprioceptive_thumb_offset_rad=policy.pressure_adapter.offset.copy() if policy.pressure_adapter is not None else np.zeros(4),solver_brake_capacity_N=brake_capacity,scheduled_progress_lag_m=float(policy.thumb_reference.last_progress_lag_m[0]) if taken and policy.thumb_reference is not None else np.nan,scheduled_pacing_rate=float(policy.thumb_reference.last_pacing_rate[0]) if taken and policy.thumb_reference is not None else np.nan,middle_support_target_rad=middle_support.target if middle_support else np.nan,middle_support_filtered_lag_rad=middle_support.lag if middle_support else np.nan,middle_support_state=middle_support.state if middle_support else 'disabled',middle_regulated_target_rad=middle_regulator.target if middle_regulator else np.nan,middle_regulated_lag_rad=middle_regulator.lag if middle_regulator else np.nan,phase=0 if t<5 else 1 if t<8 else 2 if t<12 else 3 if t<16 else 4);rows.append(row)
    row.update(pair_diagnostics(t+1/a.physics_hz))
    row['legal_support_load_features']=policy.support_load_features.features()[0].cpu().numpy().copy() if policy.support_load_features is not None else np.zeros(9)
    if support_acquisition:
     row.update(support_acquisition_target_rad=support_acquisition.target,support_acquisition_tracking_lag_rad=support_acquisition.lag,support_acquisition_state=support_acquisition.state)
    row['estimated_contact_normal_moment_proxy_Nm']=getattr(policy.pressure_adapter,'estimated_moment_Nm',np.nan)
    row['estimated_contact_moment_error_proxy_Nm']=getattr(policy.pressure_adapter,'moment_error_Nm',np.nan)
    row['estimated_support_normal_proxy_N']=getattr(policy.pressure_adapter,'last_support_proxy',np.full(3,np.nan)).copy()
    row['support_load_offset_rad']=getattr(policy.pressure_adapter,'motor_offset',np.zeros(20)).copy()
    row['estimated_index_support_proxy_N']=getattr(policy.pressure_adapter,'last_index_estimate',np.nan)
    row['index_support_motor_offset_rad']=getattr(policy.pressure_adapter,'index_offset',np.zeros(4)).copy()
    row['index_support_reference_proxy_N']=getattr(policy.pressure_adapter,'baseline_index_estimate',np.nan)
    row['truth_diagnostic_body_roll_error_rad']=truth_body_diagnostic.last_error_rad if truth_body_diagnostic else np.nan
    row['truth_diagnostic_support_offset_rad']=truth_body_diagnostic.last_offset.copy() if truth_body_diagnostic else np.zeros(20)
    if cell_spec:row.update(serial_diagnostic_axial_mean_N=float(np.mean(cell_samples)),serial_diagnostic_axial_min_N=float(np.min(cell_samples)),serial_diagnostic_axial_max_N=float(np.max(cell_samples)),serial_diagnostic_cell_q_m=float(dof[cell_id,0]));cell_samples=[]
    if force_meter:row.update(force_meter.summary())
    if writer:
     gym.step_graphics(sim);gym.render_all_camera_sensors(sim);im=np.asarray(gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(720,960,4)[...,:3];writer.append_data(im);im2=np.asarray(gym.get_camera_image(sim,env,closecam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(720,960,4)[...,:3];closewriter.append_data(im2)
   if step%1200==0:print(json.dumps(dict(t=t,object_height=float(rb[oid,2]),slider=float(dof[sid,0]),arm_tracking_max=float(abs(target[arm]-dof[arm,0]).max()))),flush=True)
  trace={k:np.asarray([x[k] for x in rows]) for k in rows[0]};np.savez_compressed(a.output/'trace.npz',**trace);h=trace['object'][:,2];held=(trace['time']>=12)&(trace['time']<16);opmask=trace['time']>=16
  endpoints=[]
  for end in [21,26,31,36]:
   mask=(trace['time']>end-.3)&(trace['time']<=end)
   endpoints.append(float((trace['slider'][mask]-lower).mean()) if mask.any() and a.seconds>=end and not a.grasp_only else None)
  opened_ok=all(x is not None and x>.025 for x in [endpoints[0],endpoints[2]])
  closed_ok=all(x is not None and x<.008 for x in [endpoints[1],endpoints[3]])
  report=dict(start='Knife resting on table; hand initially open at planned clearance (11.5cm for registered Cartesian path,16cm otherwise)',methods=('Motor-only scripted continuous-IK approach/close/lift' if a.cartesian_path or a.acquisition_path else 'Motor-only scripted joint-space approach/close/lift')+'; finite-torque gravity-compensated arm/hand; '+('pickup-only diagnostic' if a.grasp_only else ('offline-calibrated scheduled thumb IK with static joint preload' if thumb_script is not None else 'Scheduled calibrated rolling-thumb reference plus learned bounded residual using R800 legal features' if a.residual_checkpoint and policy.action_base_mode=='geometric' else 'R800 legal features plus learned bounded direct action' if a.residual_checkpoint and policy.action_base_mode=='zero' else 'R800+bounded residual' if a.residual_checkpoint else 'R800')+' after16s with once-loaded relative-grip calibration estimate'),lifted_clear=bool((h[held]>a.table_height+.03).all()) if held.any() else False,operation_stays_clear=bool((h[opmask]>a.table_height+.03).all()) if opmask.any() else False,meaningful_extension=opened_ok,retraction_after31s=closed_ok,full_success=False,minimum_hold_height_m=float(h[held].min()) if held.any() else None,max_object_height_m=float(h.max()),wall_seconds=time.monotonic()-started,positive_load_power_max_W=max_positive_power,weight_sha256={(str(x.relative_to(R)) if R in x.parents else str(x)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth']+([R/a.residual_checkpoint] if a.residual_checkpoint else [])},scope='Continuous physics attempt, no stage state writes. Meaningful25mm extension and8mm return are predeclared demo diagnostics; inherited40mm command unchanged. No preciseS5claim.')
  if a.acquisition_path:report['start']='Knife at configured tabletop edge with COM on table; open hand outside edge, lateral acquisition then vertical lift'
  if a.takeover_seconds<16:report['methods']=report['methods'].replace(' after16s with',f' from{a.takeover_seconds:g}s; operation starts16s with')
  if thumb_script and thumb_script.get('motor_target_scope'):
   report['methods']=report['methods'].replace('offline-calibrated scheduled thumb IK with static joint preload','known full tangential motor trajectory with bounded normal relief')
   report['thumb_motor_reference_scope']=thumb_script['motor_target_scope']
  report['known_controller_spec']=dict(support_span_rad=policy.known.support_span,support_step_rad=policy.known.support_step)
  report['integration_diagnostics']=dict(physics_hz=a.physics_hz,motor_pd_hz=240,policy_history_hz=30,passive_groove_work_J=groove_work,passive_startup_work_J=startup_work,total_passive_discrete_work_plus_potential_change_J=passive_energy_error,maximum_positive_passive_discrete_energy_residual_J=passive_energy_error_max,groove_potential_depth_J=a.detent*.0015,dissipative_actual_displacement_work_J=dissipative_work,total_added_load_work_plus_potential_change_J=passive_energy_error+dissipative_work,maximum_positive_total_added_load_energy_residual_J=total_load_energy_residual_max,scope='Evaluation-only sum of held passive force times actual substep displacement plus analytical potential change; zero for exact conservative integration. Positive residual measures held-force quadrature inconsistency; it does not by itself prove net physical energy injection or actuator work. Original passive profiles and motors unchanged.')
  report['resistance_integration']=a.resistance_integration
  report['trace_load_fields_scope']='In solver-brake mode, load=0 is externaljointforce; dissipative_load/passive_groove_load are counterfactual legacy explicit model values, not applied brake force. Only solver_brake_capacity_N is the calibrated native force-cap parameter; actual brakeforce remains unavailable.'
  if a.resistance_integration=='solver-brake':
   report['integration_diagnostics']=dict(physics_hz=a.physics_hz,motor_pd_hz=240,policy_history_hz=30,brake_capacity_max_N=float(trace['solver_brake_capacity_N'].max()),brake_capacity_operation_min_N=float(trace['solver_brake_capacity_N'][opmask].min()),scope='Passive nativezero-velocity jointbrake with250 damping and calibratedNewtonforcecap; physics-only time/position modulatescap. Replaces explicit regularizedfriction and conservativepotential by dissipative startup/groove barriers. No positivevelocity/positiontarget, nohanddrive/rail/criteriachange. Actualbrakeforce incontactdemo unavailable; cap isverifiedfixtureparameter, notmeasuredworldtraction or realresistance.',calibration='runs/support-pressure-20261003/calibration/solver-brake-v3/calibration.json')
  report['opposing_axial_test_load_N']=a.opposing_axial_test_load
  report['serial_load_cell_diagnostic']=cell_spec
  report['original_scene_axial_force_measurement_completed']=False
  report['thumb_reference_override']=str(a.thumb_reference_override) if a.thumb_reference_override else None
  report['learned_action_parameterization']=policy.action_parameterization
  report['support_load_feature_spec']=policy.support_load_feature_spec
  report['support_command_period_frames']=policy.support_command_period
  report['support_decision_scope']='Knownclock supportresidual held between decisions; thumb30Hz; oneactual issuedhistory update each30Hz'
  report['learned_takeover_seconds']=a.takeover_seconds if a.residual_checkpoint else None
  report['support_latch_after_preparation']=policy.support_latch_after_preparation
  report['support_delta_coordinates']={k:v for k,v in policy.support_delta_coordinates.spec.items() if k!='reference_actor_state'} if policy.support_delta_coordinates is not None else None
  report['known_task_schedule_seconds']=[16,21,26,31,36]
  report['learned_hold_scope']='If takeover<16, same legal residual commands closed during8–16 and keeps actual history/motor/RNN state into operation; no phase state reset or force regulation'
  if support_acquisition:report['support_contact_acquisition']=support_acquisition.report()
  report['middle_deflection_support']=middle_support.report() if middle_support else None
  report['middle_load_lag_regulation']=middle_regulator.report() if middle_regulator else None
  report['staged_preload']=dict(seconds=post_lift_interval,issued_arm_lift_height_interval_m=lift_preload_height,scope=('Known closure/lift/transfer motor reference plus bounded learned offsets;50 actualhistoryframes precede5s takeover; no physics/history/RNNreset at16s' if learned_prefix else 'Known motor targets; no live object/slider/contact or physical-state write. Learned preparation follows completed transfer; actual issued-command history continues' if a.takeover_seconds<16 else 'Known motor targets; final full lift leaves≥50 actual constant-target frames before takeover')) if post_lift_interval or lift_preload_height else None
  report.update(operation_evaluated=not a.grasp_only and a.seconds>=36,endpoints_mean_last03s_m=endpoints,diagnostic='Scheduled four5s stages; final0.3s mean >25mm extend and <8mm return on both cycles; no truth-triggered switching')
  if held.any() and opmask.any():
   handover_i=np.flatnonzero(held)[-1];op=trace['object'][opmask];origin=trace['object'][handover_i];drift=np.linalg.norm(op[:,:3]-origin[:3],axis=-1);rot=(Rotation.from_quat(origin[3:7]).inv()*Rotation.from_quat(op[:,3:7])).magnitude()
   report.update(operation_body_max_drift_m=float(drift.max()),operation_body_max_rotation_rad=float(rot.max()),operation_body_stable=bool((drift<.01).all() and (rot<.25).all()),slider_before_handover_m=float(trace['slider'][handover_i]-lower),slider_closed_at_handover=bool(abs(float(trace['slider'][handover_i]-lower))<.008))
  else:report.update(operation_body_stable=False,slider_closed_at_handover=False)
  report.update(physical_asset=str(a.knife_asset),physical_asset_sha256=hashlib.sha256(knife_path.read_bytes()).hexdigest(),physical_dimensions_WTL_m=knife_parameters['handle_size'],physical_slider_size_WTL_m=knife_parameters['slider_size'],initial_geometry_estimate=initial_estimate,policy_geometry_estimate_scope=('Explicit initial noisy geometry estimate, common offline IK adaptation and once-loaded prior; no physicalasset ID or runtime object/contact input' if initial_estimate else 'Unchanged nominal geometry and once-loaded prior calibration; physical asset identity never given to actor'),hand_friction=a.hand_friction,knife_friction=a.knife_friction,load_profile=load_profile,load_frequency_rad_s=a.load_frequency,observation_noise_std_rad=a.observation_noise,observation_bias_bound_rad=a.observation_bias,seed=a.seed,initial_pose_prior_scope=('Once known tabletop+initialgeometry estimate transformedby measuredG2armFK atclosure takeover; no currentobject/slidertruth' if policy.table_initial_prior_from_measured_arm else 'Once loaded nominal heldprior'),loaded_weight_use='Interface initialization only; learned actor never called' if a.grasp_only or thumb_script is not None else 'Frozen R800 and optional residual actor executed after50 actual history frames',residual_checkpoint=str(a.residual_checkpoint),thumb_script=str(a.thumb_script),thumb_script_scope='Known 40mm schedule+offline geometric trajectory and joint preload, not constant force or live state feedback' if thumb_script is not None else None,thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,added_load_N=a.load,passive_startup_detent_amplitude_N=a.detent,variable_load=a.variable_load,load_scope='Calibrated passive zero-velocity solverbrake capacity with dissipative startup/groove; no realtotalresistance or instantaneousfrictionmeasurement claim.' if a.resistance_integration=='solver-brake' else 'Engineering added load plus original passive friction/damping; no measured real total-resistance ceiling. Groove is finite passive potential; positive descent power is stored energy.')
  if opmask.any():
   report.update(operation_thumb_slider_contact_fraction=float((trace['finger_slider_contacts'][opmask,0]>0).mean()),operation_body_contact_fraction=(trace['finger_body_contacts'][opmask]>0).mean(0).tolist(),contact_scope='30Hz solver-contact diagnostics; current truth never fed to actor. Positive motor preload does not establish constant pressure.')
   report['operation_thumb_slider_contact_maintained']=report['operation_thumb_slider_contact_fraction']>=.90
  else:report['operation_thumb_slider_contact_maintained']=False
  if held.any() and opmask.any() and not a.grasp_only:
   operation_times=trace['time'][opmask]
   def onset(mask):
    ids=np.flatnonzero(mask);return float(operation_times[ids[0]]) if len(ids) else None
   lost=trace['finger_slider_contacts'][opmask,0]==0
   continuous_loss=np.convolve(lost.astype(int),np.ones(10,dtype=int),mode='valid')>=10 if len(lost)>=10 else np.zeros(0,dtype=bool)
   first_loss=np.flatnonzero(continuous_loss)
   report['failure_onsets_s']=dict(body_stability=onset((drift>=.01)|(rot>=.25)),height=onset(h[opmask]<=a.table_height+.03),sustained_thumb_slider_contact_loss=float(operation_times[first_loss[0]]) if len(first_loss) else None)
   report['failure_onsets_scope']='Evaluation only: first stability/height breach, and first10 consecutive30Hz samples without thumb-slider contact. Legacy first_failure lists failed conditions by priority, not chronological onset. No control or completion-gate change.'
  report['extension_endpoint_condition_met']=opened_ok
  report['meaningful_extension']=opened_ok and report['operation_body_stable'] and report['operation_thumb_slider_contact_maintained']
  report['full_success']=report['operation_thumb_slider_contact_maintained'] and report['operation_body_stable'] and report['slider_closed_at_handover'] and report['operation_evaluated'] and report['lifted_clear'] and report['operation_stays_clear'] and opened_ok and closed_ok
  if force_meter:
   report['pair_pressure']=dict(calibration='research/support-pressure-20261003/PAIR-FORCE-SEMANTICS.md',physics_hz=a.physics_hz,substeps_per_simulate=1,sample_scope=f'Every actualphysicalstep at{a.physics_hz}Hz, arithmeticmean/min/max over{a.physics_hz//30}steps per30Hz policyframe; Newtonlambda not dividedbydt; onlynormalcontribution. No forcefeedback to control.',finger_order=['thumb','index','middle','ring','pinky'],static_thumb_pressure_mean_N=float(trace['pair_slider_pressure_mean_N'][(trace['time']>=14)&(trace['time']<16),0].mean()),operation_thumb_pressure_mean_N=float(trace['pair_slider_pressure_mean_N'][opmask,0].mean()),operation_thumb_pressure_5th_percentile_N=float(np.quantile(trace['pair_slider_pressure_mean_N'][opmask,0],.05)),operation_thumb_contact_substep_fraction=float(trace['pair_slider_contact_substep_fraction'][opmask,0].mean()),operation_ring_underside_support_mean_N=float(trace['pair_underside_support_mean_N'][opmask,3].mean()),tangential_force_scope='Axial component of measured pairnormalforces only; frictionaltraction is not reconstructed')
  report['fitted_resistance_profile']=resistance_profile
  report['fitted_resistance_profile_sha256']=hashlib.sha256(a.measured_resistance_profile.read_bytes()).hexdigest() if a.measured_resistance_profile else None
  report['postlift_regrasp']=regrasp
  report['postlift_regrasp_scope']='Actual uninterrupted pickup then known-clock arm/hand target transition, all physical velocities/state/history retained; nominal offline estimate only, contact continuity evaluated separately' if regrasp else None
  report['held_diagnostic']=a.held_diagnostic
  if a.held_diagnostic:
   report['start']='Explicit held-only diagnostic reset at lifted nominal pose before first simulation; free-floating knife, original gravity/limits, no later resets'
   report['held_submodule_legacy_criteria_met']=report['full_success']
   report['full_success']=False
  report['actuation_delay_frames']=a.actuation_delay_frames
  report['actuation_delay_scope']='Physical appliedtarget delayed; public knownmemory/history trackissued target without observing private appliedtarget'
  report['support_pressure_spec']=support_spec
  report['proprioceptive_pressure_spec']=pressure_spec
  report['measured_hold_reference_audit']=getattr(policy,'measured_hold_reference_audit',None)
  report['pressure_feedback_scope']='Single-contact quasi-static jointdeflection estimate, notmeasuredpairforce orhardwareforcefeedback; prefix adjustment freezesbefore50 realconstanttarget frames, same motorhistory intoactor' if pressure_spec else None
  report['support_residual_scale_override_rad']=a.support_residual_scale_override
  report['wrist_roll_reference_degrees']=a.wrist_roll_reference_degrees
  report['wrist_roll_scope']=wrist_roll_curve['scope'] if wrist_roll_curve is not None else None
  report['frozen_thumb_actor']=bool(policy.residual is not None and policy.residual.frozen_thumb_actor is not None)
  report['frozen_thumb_scope']='Deterministic thumb mean from frozen legal-input prior; measured joints/history and support motion still affect physical contact. Not constant pressure or an imposed thumb trajectory.' if report['frozen_thumb_actor'] else None
  report['truth_body_roll_diagnostic']=bool(truth_body_diagnostic)
  if truth_body_diagnostic:
   report['diagnostic_physical_task_criteria_met']=report['full_success']
   report['full_success']=False
   report['diagnostic_exclusion_scope']='Actual bodyorientation truth influences supporttargets; not deployable, never counted as full demo success. Original physicalcriteria recorded separately; no forceassist/attachment/reset/limit change.'
  report['first_failure']='Nondeployable truth diagnostic excluded from demo count' if truth_body_diagnostic and report.get('diagnostic_physical_task_criteria_met') else 'none' if report['full_success'] else 'pickup/lift' if not report['lifted_clear'] else 'operation not tested' if a.grasp_only else 'holding after handover' if not report['operation_stays_clear'] else 'body stability after handover' if not report['operation_body_stable'] else 'extension/retraction';(a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
 finally:
  if force_meter:force_meter.close()
  if cell_stream:cell_stream.close()
  if test_stream:test_stream.close()
  pair_stream.close()
  if candidate_stream:candidate_stream.close()
  if writer:writer.close();closewriter.close()
  gym.destroy_sim(sim)
if __name__=='__main__':main()
