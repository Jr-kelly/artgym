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
 # Explicit short development connection to the retained B controller.
 p=argparse.ArgumentParser();p.add_argument("--frame-complete-hand",action="store_true",help="Visual-only camera bounding both complete hand and knife; no changes to physics");p.add_argument("--prefix-pose-adaptation",type=Path,help="Once postpush pose correction of clamp approach, removed toward fixed release pose; motor references only");p.add_argument("--relax-idle-ring",action="store_true",help="Ease unused ring joint3 after functional regrasp; preserve supporting fingers and original limits");p.add_argument("--close-camera-scale",type=float,default=1.,help="Visual-only distance multiplier; physical trajectory unchanged");p.add_argument("--loaded-table-pose-transport",action="store_true");p.add_argument("--recorded-b-start-s",type=float);p.add_argument("--recorded-planar-retain-arm-load",action="store_true");p.add_argument("--recorded-planar-servo",action="store_true");p.add_argument("--recorded-support-command",type=Path);p.add_argument("--recorded-handoff",type=Path,help="Development-only recorded actual state initialization; missing velocities/cache labelled, never full-flow proof");p.add_argument("--paired-vector-load-servo",action="store_true");p.add_argument("--paired-normal-load-servo",action="store_true");p.add_argument("--loaded-thumb-pose-servo",action="store_true");p.add_argument("--flat-pickup-policy",type=Path);p.add_argument("--pose-dual-push",type=Path);p.add_argument("--fixed-support-opposition",type=Path);p.add_argument("--flat-table-prefix",type=Path);p.add_argument("--postpush-pose-update",action="store_true");p.add_argument("--fold-outside-fingers",action="store_true");p.add_argument("--fold-release-start",type=float,default=9.);p.add_argument("--preclose-middle",action="store_true");p.add_argument("--middle-entry-config",type=Path);p.add_argument("--pickup-extra-lift-m",type=float,default=0.);p.add_argument("--slow-lift",action="store_true");p.add_argument("--pickup-thumb-pose-tracking",action="store_true");p.add_argument("--pickup-wrist-pose-follow",action="store_true");p.add_argument("--tail-support-config",type=Path);p.add_argument("--partial-tail-regrasp",type=Path);p.add_argument("--partial-tail-pose-clamp",action="store_true");p.add_argument("--partial-tail-second-pose-update",action="store_true");p.add_argument("--partial-tail-maintain-index",action="store_true");p.add_argument("--contact-preserving-regrasp",action="store_true");p.add_argument("--rail-contact-regrasp",action="store_true");p.add_argument("--retain-loaded-motor-offset",action="store_true");p.add_argument("--native-point-regrasp",action="store_true");p.add_argument("--postpush-pose-input",type=Path);p.add_argument("--pose-estimate-bias-m",type=float,default=0.);p.add_argument("--extension-only",action="store_true",help="Knownclock single forward goal then indefinite positionhold; no return or truth-triggered switching");p.add_argument("--task-stroke-m",type=float,default=.04);p.add_argument("--newknife-resistance",type=Path);p.add_argument('--thumb-residual-scale-override',type=float,help='Explicit thumb motor residual amplitude for matched controller ablation, radians; original physical limits and support actor retained');p.add_argument('--final-issued-target-hold',action='store_true',help='Only35--36s known final-hold position latch; actor/reference/history continue, original finitePD, no truth/forcefeedback');p.add_argument('--table-y',type=float,default=-.25,help='Known table placement, original geometry and gravity; no object fixture');p.add_argument('--scheduled-target-holds',action='store_true',help='Knownclock position holds after full reference stroke; actor/history continue, original finitePD, no constantforce claim');p.add_argument('--proximal-friction',type=float,help='Explicit assumed link/palm friction distinctfromdistalpad; unknownmaterial sensitivity, no increasedgeometry/actuatorforce');p.add_argument('--opposing-test-load-mode',choices=['constant-countercommand','slip-gated'],default='constant-countercommand',help='Diagnostic dynamometer load always opposes requested direction; positive work during reverse slip goes away from goal. Native guide remains passive. slip-gated retained only for preliminary test comparison.');p.add_argument('--opposing-axial-test-load',type=float,default=0.,help='Known balanced body/slider axial test force opposing requested direction; evaluation-only task load, not measured thumb force. Mode determines activation.');p.add_argument('--serial-load-cell-diagnostic',action='store_true',help='Modified series-elastic slider diagnostic only; requires calibrated960Hz asset, never original-task direct force measurement');p.add_argument('--wrap-contact-measurement',action='store_true',help='Evaluation-only complete240Hz actual contact locations by link; normals only, not axial total force');p.add_argument('--support-acquisition-config',type=Path,help='Finite postlift measured-joint/previous-issued-target tracking search, original certified corridor; frozen before50 actualhistoryframes, not forcefeedback');p.add_argument('--postlift-regrasp',type=Path,help='Once-loaded known-clock arm/hand motor path after actual pickup, ending before50 constant historyframes; no object-truth trigger/state reset');p.add_argument('--measured-resistance-profile',type=Path,help='Explicit once-loaded fitted bidirectional passive brake-capacity file, physics only; no actor/profile-ID input, reject positions outside measured support');p.add_argument('--held-diagnostic',action='store_true',help='Explicit submodule only: initialize a free-floating knife and closed hand at lifted nominal pose before first simulation; original gravity/contact/limits, no later state writes; never a continuous pickup success');p.add_argument('--wrist-roll-reference-degrees',type=float,default=0.,help='Development motor-only wrist reference: bounded +/-4deg about estimatedknife longaxis, ramps16--18s afteractualpickup; no liveobject/contactinput');p.add_argument('--output',type=Path,required=True);p.add_argument('--support-residual-scale-override',type=float,help='Explicit bounded-offset checkpoint support amplitude inradians, atmost original.04span; originalmotor/effortlimits unchanged');p.add_argument('--truth-body-roll-diagnostic',action='store_true',help='ONE explicitly non-deployable body-orientation truth diagnostic, bounded originalsupportcommands; never counted as deployable demo');p.add_argument('--video',action='store_true');p.add_argument('--middle-load-lag-regulation',action='store_true',help='Scriptoperationonly: boundedmiddlemotor adaptation frommeasuredjoint-minusactualissuedtarget, notforcefeedback');p.add_argument('--middle-deflection-support',type=Path,help='Certifiedpostliftproprioceptive supportsearch; measuredq/knownmotortargetonly; endsbefore50realholdframes');p.add_argument('--contact-import-audit',action='store_true',help='Evaluation-only nativecollision shapeproperties andall contactcandidates, includingzero-normal-force records');p.add_argument('--collision-geometry-video',action='store_true',help='Render importedcollision geometry for actualcontact diagnostics; physics unchanged');p.add_argument('--seconds',type=float,default=36);p.add_argument('--table-height',type=float,default=.75);p.add_argument('--dx',type=float,default=0);p.add_argument('--dy',type=float,default=0);p.add_argument('--yaw',type=float,default=0);p.add_argument('--close-height',type=float,default=0);p.add_argument('--load',type=float,default=0);p.add_argument('--grasp-plan',type=Path);p.add_argument('--slider-face',choices=['up','down'],default='up');p.add_argument('--arm-seed',type=Path);p.add_argument('--grasp-only',action='store_true');p.add_argument('--handover-calibration',type=Path,help='Fixed prior/offline hand-object calibration, loaded once before episode; no live object or slider truth');p.add_argument('--table-calibration',type=Path);p.add_argument('--cartesian-path',type=Path);p.add_argument('--acquisition-path',type=Path);p.add_argument('--thumb-action-gain',type=float,default=1.);p.add_argument('--support-action-gain',type=float,default=1.);p.add_argument('--residual-checkpoint',type=Path);p.add_argument('--detent',type=float,default=0.);p.add_argument('--variable-load',action='store_true');p.add_argument('--thumb-script',type=Path,help='Offline calibrated thumb joint path with scheduled commands and original legal action memory; no live slider/contact feedback');p.add_argument('--knife-asset',type=Path,default=Path('assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf'),help='Physical asset only; policy keeps nominal calibrated geometry, no asset ID input');p.add_argument('--hand-friction',type=float,default=1.);p.add_argument('--knife-friction',type=float,default=3.);p.add_argument('--load-profile',choices=['constant','sinusoidal','triangular','pulse']);p.add_argument('--load-frequency',type=float,default=1.7);p.add_argument('--observation-noise',type=float,default=0.);p.add_argument('--observation-bias',type=float,default=0.);p.add_argument('--seed',type=int,default=2026100301);p.add_argument('--physics-hz',type=int,choices=[240,480,960],default=240,help='Passive resistance/contact integration rate; original motor PD remains240Hz and legal policy/history30Hz');p.add_argument('--takeover-seconds',type=float,default=16.,help='Learned residual begins at8–16s during lift or hold; operation remains16–36s, no history/physical reset');p.add_argument('--pair-force-measurement',action='store_true',help='Evaluation only: calibrated pair forces every physical step, 30Hz averages');p.add_argument('--support-pressure-config',type=Path,help='Nominal motor support/preload transition; measured/known inputs only');p.add_argument('--resistance-integration',choices=['legacy-explicit','solver-brake'],default='legacy-explicit',help='Calibrated passive zero-velocity railbrake; finitecapacity, no commanded slider motion');p.add_argument('--thumb-reference-override',type=Path,help='Fixed nominal scheduled reference/pacing specification; same frozen actor, explicit development modification');p.add_argument('--actuation-delay-frames',type=int,choices=[0,1],default=0,help='Unknown physical target delay in30Hz frames; legal history retains the actually issued command');p.add_argument('--proprioceptive-pressure-config',type=Path,help='Bounded motoradjustment fromestimated normaljointdeflection; noforcesensor/contact input');p.add_argument("--close-camera-direction",type=float,nargs=3,help="Visual-only world viewing direction; avoids occlusion by forearm without altering physics");p.add_argument('--support-camera-direction',type=float,nargs=3,help='Optional native camera on occluded backing side of the same actual episode, visual only');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 flat_prefix=json.loads(a.flat_table_prefix.read_text()) if a.flat_table_prefix else None
 direct_pickup=None
 if flat_prefix and flat_prefix.get('direct_pickup'):
  from scripts.wuji_direct_pickup import DirectPickup
  if flat_prefix['direct_pickup'].get('continuous_stages'):
   from scripts.wuji_direct_route import DirectRoute
   direct_pickup=DirectRoute(flat_prefix['direct_pickup'],a.output)
  else:direct_pickup=DirectPickup(flat_prefix['direct_pickup'],a.output)
 prefix_pose_adapter=None
 if a.prefix_pose_adaptation:
  from scripts.wuji_prefix_pose_adaptation import PrefixPoseAdaptation
  prefix_pose_adapter=PrefixPoseAdaptation(json.loads(a.prefix_pose_adaptation.read_text()))
 middle_entry=json.loads(a.middle_entry_config.read_text()) if a.middle_entry_config else None
 fixed_support=json.loads(a.fixed_support_opposition.read_text()) if a.fixed_support_opposition else None
 fixed_support_latch=None
 loaded_thumb_servo=None
 if a.loaded_thumb_pose_servo:
  from scripts.wuji_loaded_thumb_pose_servo import LoadedThumbPoseServo
  loaded_thumb_servo=LoadedThumbPoseServo()
 pickup_policy=None
 if a.flat_pickup_policy:
  from scripts.wuji_flat_pickup_policy import FlatPickupPolicy
  pickup_policy=FlatPickupPolicy(a.flat_pickup_policy)
  pickup_motor_path=np.load('runs/flat-table-20261006/learning/real-prefix-v76/learn-path.npz')['targets']
 dual_push=None
 if a.pose_dual_push:
  from scripts.wuji_pose_dual_push import PoseDualPush
  dual_push=PoseDualPush(a.pose_dual_push)
 tail_support=json.loads(a.tail_support_config.read_text()) if a.tail_support_config else None
 partial_tail=json.loads(a.partial_tail_regrasp.read_text()) if a.partial_tail_regrasp else None
 partial_second_updated=False
 partial_clamp=None
 if a.partial_tail_pose_clamp:
  from scripts.wuji_partial_tail_pose_clamp import PartialTailPoseClamp
  partial_clamp=PartialTailPoseClamp(a.partial_tail_regrasp.parent.parent/'three-contact-v51/asset-spec.json')
 prefix_duration=flat_prefix['duration_s'] if flat_prefix else 0.
 recorded_handoff=np.load(a.recorded_handoff/'takeover.npz') if a.recorded_handoff else None
 recorded_support=json.loads(a.recorded_support_command.read_text()) if a.recorded_support_command else None
 recorded_material_carrier=None
 recorded_live_ring=None
 if recorded_support and 'direct_live_ring' in recorded_support:
  from scripts.wuji_direct_live_ring import DirectLiveRing
  recorded_live_ring=DirectLiveRing(recorded_support['direct_live_ring'],a.output)
 recorded_grip_roll_servo=None
 if recorded_support and 'direct_grip_roll_servo' in recorded_support:
  from scripts.wuji_direct_grip_roll_servo import DirectGripRollServo
  recorded_grip_roll_servo=DirectGripRollServo(recorded_support['direct_grip_roll_servo'],a.output)
 recorded_joint_path_tracking=None
 if recorded_support and 'direct_joint_path_tracking' in recorded_support:
  from scripts.wuji_direct_joint_path_tracking import DirectJointPathTracking
  recorded_joint_path_tracking=DirectJointPathTracking(recorded_support['direct_joint_path_tracking'],a.output)
 if recorded_support and 'direct_material_carrier' in recorded_support:
  from scripts.wuji_direct_material_carrier import DirectMaterialCarrier
  recorded_material_carrier=DirectMaterialCarrier(recorded_support['direct_material_carrier'],a.output)
 if recorded_support and 'direct_material_carriers' in recorded_support:
  from scripts.wuji_direct_material_carrier import DirectMaterialCarrierGroup
  recorded_material_carrier=DirectMaterialCarrierGroup(recorded_support['direct_material_carriers'],a.output)
 recorded_idle_middle_clearance=None
 if recorded_support and 'direct_idle_middle_clearance' in recorded_support:
  from scripts.wuji_direct_idle_middle_clearance import DirectIdleMiddleClearance
  recorded_idle_middle_clearance=DirectIdleMiddleClearance(recorded_support['direct_idle_middle_clearance'],a.output)
 direct_thumb_servo=None
 if recorded_support and 'direct_live_ring' in recorded_support:
  from scripts.wuji_direct_live_ring import DirectLiveRing
  direct_thumb_servo=DirectLiveRing(recorded_support['direct_live_ring'],a.output)
 if recorded_support and 'direct_pressure_path_servo' in recorded_support:
  from scripts.wuji_direct_pressure_path_servo import DirectPressurePathServo
  direct_thumb_servo=DirectPressurePathServo(recorded_support,a.output)
 if recorded_support and 'direct_thumb_servo' in recorded_support:
  from scripts.wuji_direct_thumb_servo import DirectThumbServo
  direct_thumb_servo=DirectThumbServo(recorded_support['direct_thumb_servo'],a.output)
 if recorded_support and 'direct_coordinated_servo' in recorded_support:
  from scripts.wuji_direct_coordinated_servo import DirectCoordinatedServo
  direct_thumb_servo=DirectCoordinatedServo(recorded_support['direct_coordinated_servo'],a.output)
 if recorded_support and 'direct_contact_gait_servo' in recorded_support:
  from scripts.wuji_direct_contact_gait_servo import DirectContactGaitServo
  direct_thumb_servo=DirectContactGaitServo(recorded_support['direct_contact_gait_servo'],a.output)
 if recorded_support and 'thumb_material_servo' in recorded_support:
  from scripts.wuji_kinematics import WujiKinematics
  recorded_thumb_kin=WujiKinematics()
 recorded_servo_relative=None
 recorded_servo_initial=None
 if recorded_support:assert recorded_handoff is not None
 if recorded_handoff is not None:
  assert (a.grasp_only and a.seconds<=30 and not a.postpush_pose_update) or (a.recorded_b_start_s is not None and a.seconds<=24 and a.postpush_pose_update)
  prefix_duration=a.recorded_b_start_s or 0.
  (a.output/'recorded-initialization.json').write_text(json.dumps(dict(source=str(a.recorded_handoff),scope='Development only; actual positions/object velocity/slider/issued targets; robot velocity finite-difference estimate; solver cache absent; no full restore equivalence'),indent=2))
 pose_updated=False;pose_update_diagnostics=None;pose_bridge_start=None
 loaded_table_transport=None;adaptive_exit=None
 if a.loaded_table_pose_transport:
  from scripts.wuji_loaded_table_pose_transport import LoadedTablePoseTransport
  loaded_table_transport=LoadedTablePoseTransport()
 thumb_tracking=None
 if a.pickup_thumb_pose_tracking:
  from scripts.wuji_flat_thumb_tracking import PickupThumbTracking
  thumb_tracking=PickupThumbTracking()
 learned_prefix=bool(a.residual_checkpoint and (torch.load(a.residual_checkpoint,map_location='cpu').get('scene_spec') or {}).get('learned_acquisition_prefix',False))
 resistance_profile=json.loads(a.measured_resistance_profile.read_text()) if a.measured_resistance_profile else None
 if resistance_profile:
  assert a.resistance_integration=='solver-brake' and resistance_profile['format']=='wuji-passive-resistance-profile-v1'
  assert set(resistance_profile['directions'])=={'extend','retract'}
 newknife_resistance=json.loads(a.newknife_resistance.read_text()) if a.newknife_resistance else None
 if newknife_resistance:
  assert a.resistance_integration=='solver-brake' and a.load==0 and a.detent==0 and not a.measured_resistance_profile and not a.opposing_axial_test_load
  from scripts.wuji_newknife_resistance import capacity as newknife_capacity,distribution
  (a.output/'resistance-distribution.json').write_text(json.dumps(distribution(newknife_resistance)))
 rng=np.random.default_rng(a.seed);sensor_bias=rng.uniform(-a.observation_bias,a.observation_bias,20);knife_path=R/a.knife_asset;knife_parameters=json.loads((knife_path.parent/'parameters.json').read_text());cell_spec=knife_parameters.get('serial_load_cell') if a.serial_load_cell_diagnostic else None
 if a.serial_load_cell_diagnostic:assert cell_spec and a.physics_hz==960 and a.resistance_integration=='solver-brake'
 else:assert 'serial_load_cell' not in knife_parameters,'Diagnostic asset requires explicit label'
 load_profile=a.load_profile or ('sinusoidal' if a.variable_load else 'constant')
 assert a.hand_friction>=0 and a.knife_friction>=0 and a.observation_noise>=0 and a.observation_bias>=0
 initial_estimate=json.loads(a.grasp_plan.read_text()).get('initial_geometry_estimate') if a.grasp_plan else None
 estimated_geometry=list(initial_estimate['handle_size_WTL_m'])+initial_estimate.get('slider_size_WTL_m',[.01,.003,.03]) if initial_estimate else None
 cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
 if a.paired_normal_load_servo:
  from scripts.wuji_paired_normal_load_servo import PairedNormalLoadServo
  loaded_thumb_servo=PairedNormalLoadServo(np.asarray(cfg.hand.dof_props.stiffness))
 if a.paired_vector_load_servo:
  from scripts.wuji_paired_vector_load_servo import PairedVectorLoadServo
  loaded_thumb_servo=PairedVectorLoadServo(np.asarray(cfg.hand.dof_props.stiffness))
 if dual_push:dual_push.kp=np.asarray(cfg.hand.dof_props.stiffness,dtype=float)
 policy=G2R800Policy(cfg,R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',geometry=estimated_geometry,thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,residual_checkpoint=a.residual_checkpoint,thumb_reference_override=a.thumb_reference_override,support_residual_scale_override=a.support_residual_scale_override,thumb_residual_scale_override=a.thumb_residual_scale_override);kin=G2Kinematics()
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
  if initial_estimate.get('newknife_contact_geometry'):initial_delta[1]-=(initial_estimate['slider_size_WTL_m'][1]-.003)/2
  policy_slider_estimate=policy_slider_estimate.copy();policy_slider_estimate[:3,3]+=policy_relative[:3,:3]@initial_delta
 def initial_takeover_priors():
  if policy.table_initial_prior_from_measured_arm:
   from scripts.wuji_initial_table_prior import measured_arm_relative
   return measured_arm_relative(plan,initial_estimate,kin.forward(dof[arm,0].numpy()))
  return policy_relative,(policy_slider_estimate if policy_slider_estimate is not None else policy_relative@transform([0,.0075,.010624586881962734+lower]))
 if policy.support_load_features is not None:
  policy.support_load_features.reset(torch.tensor([0],device=policy.player.device),policy.tensor(policy_relative[:3,1]))
 if a.final_issued_target_hold:assert a.seconds==36 and a.residual_checkpoint and not a.thumb_script and not a.held_diagnostic
 if a.scheduled_target_holds:assert a.residual_checkpoint and not a.thumb_script and policy.thumb_reference is not None and not policy.thumb_reference.pacing and policy.thumb_reference.duration<5
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
  if pressure_spec.get('control')=='thumb-pressure-and-index-retention':
   from scripts.wuji_thumb_index_retention import ThumbIndexRetention
   adapter=ThumbIndexRetention
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
 if flat_prefix:
  knife0[:2,3]=flat_prefix['physical_initial_xy']
  knife0[:3,:3]=(Rotation.from_euler('z',flat_prefix['physical_initial_yaw_deg'],degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_matrix()
  if flat_prefix.get('physical_initial_object_world') is not None:
   knife0=np.asarray(flat_prefix['physical_initial_object_world'],dtype=float)
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
 opt=gymapi.AssetOptions();opt.fix_base_link=True;tableasset=gym.create_box(sim,.60,.80,.05,opt);table=gym.create_actor(env,tableasset,gt(transform([.60,a.table_y,a.table_height-.025])),'table',0,0)
 opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;opt.density=1000;knifeasset=gym.load_asset(sim,str(knife_path.resolve().parent),knife_path.name,opt);
 if recorded_handoff is not None:knife0=transform(recorded_handoff['object_state'][:3],recorded_handoff['object_state'][3:7])
 knife=gym.create_actor(env,knifeasset,gt(knife0),'knife',0,0);bodies=gym.get_actor_rigid_body_properties(env,knife);knife_xml=ET.parse(knife_path)
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
 op=gym.get_actor_dof_properties(env,knife);lower=float(op['lower'][0]);op['driveMode'][:]=gymapi.DOF_MODE_EFFORT;op['stiffness'][:]=0;op['damping'][:]=.3;op['friction'][:]=0. if newknife_resistance else .001;op['armature'][:]=.001;
 if a.resistance_integration=='solver-brake':
  op['driveMode'][:]=gymapi.DOF_MODE_VEL;op['damping'][:]=float(newknife_resistance.get('damping_Ns_m',25000)) if newknife_resistance else 250.;op['effort'][:]=max(a.load,1e-8);gym.set_actor_dof_properties(env,knife,op);gym.set_actor_dof_velocity_targets(env,knife,np.zeros(len(op),dtype=np.float32))
 else:gym.set_actor_dof_properties(env,knife,op)
 if cell_spec:
  cell_local=gym.get_actor_dof_names(env,knife).index('serial_load_cell');op['driveMode'][cell_local]=gymapi.DOF_MODE_EFFORT;op['damping'][cell_local]=0.;op['friction'][cell_local]=0.;op['armature'][cell_local]=0.;op['effort'][cell_local]=10.;gym.set_actor_dof_properties(env,knife,op)
 ds=np.zeros(27,dtype=gymapi.DofState.dtype);ds['pos'][arm]=qlift if a.held_diagnostic else qabove;ds['pos'][hand]=np.asarray(plan['touch_q']) if a.held_diagnostic else opened;
 if flat_prefix:
  ds['pos'][arm]=flat_prefix['rows'][0]['arm_q'];ds['pos'][hand]=flat_prefix['rows'][0]['hand_q']
 os=np.zeros(len(op),dtype=gymapi.DofState.dtype);os['pos'][0]=float(knife_parameters.get('initial_slider_q_m',lower))
 if recorded_handoff is not None:
  ds['pos'][:]=recorded_handoff['robot_q'];ds['vel'][:]=recorded_handoff['estimated_robot_velocity'];os['pos'][0]=recorded_handoff['slider_q'];os['vel'][0]=recorded_handoff['slider_velocity']
 gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL)
 cam=None;writer=None;supportwriter=None;supportcam=None
 if a.video:
  import imageio.v2 as imageio
  cp=gymapi.CameraProperties();cp.use_collision_geometry=a.collision_geometry_video;cp.width=960;cp.height=720;cam=gym.create_camera_sensor(env,cp);gym.set_camera_location(cam,env,gymapi.Vec3(1.25,-1.4,1.5),gymapi.Vec3(.4,-.3,.85));cp2=gymapi.CameraProperties();cp2.use_collision_geometry=a.collision_geometry_video;cp2.width=960;cp2.height=720;cp2.horizontal_fov=65;closecam=gym.create_camera_sensor(env,cp2);close_aim=knife0[:3,3]+np.array([0.,0.,.085]);gym.set_camera_location(closecam,env,gymapi.Vec3(*(close_aim+np.array([.34,-.12,.24]))),gymapi.Vec3(*close_aim));closewriter=imageio.get_writer(str(a.output/'hand-closeup.mp4'),fps=30,codec='libx264',quality=7);writer=imageio.get_writer(str(a.output/'continuous.mp4'),fps=30,codec='libx264',quality=7)
  if a.support_camera_direction is not None:
   supportcam=gym.create_camera_sensor(env,cp2);supportwriter=imageio.get_writer(str(a.output/'hand-support-view.mp4'),fps=30,codec='libx264',quality=7)
   (a.output/'support-camera.json').write_text(json.dumps(dict(direction=a.support_camera_direction,fps=30,scope='Additional nativecamera of samephysicalepisode, allframes; underside initially obscuredbytable, primaryview supplements; no state/targetwrites'),indent=2))
 gym.prepare_sim(sim);gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL);dof=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));contact=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));jac=gymtorch.wrap_tensor(gym.acquire_jacobian_tensor(sim,'robot'));oid=gym.get_actor_rigid_body_index(env,knife,0,gymapi.DOMAIN_SIM);sid=gym.get_actor_dof_index(env,knife,0,gymapi.DOMAIN_SIM);robotb=gym.get_actor_rigid_body_properties(env,robot);masses=torch.tensor([b.mass for b in robotb][1:]);force=torch.zeros(len(dof));target=torch.tensor(ds['pos'].copy());K=torch.tensor(kp,dtype=torch.float32);C=torch.tensor(kd,dtype=torch.float32);limits=torch.tensor(props['effort'].copy());limitlow=torch.tensor(props['lower'].copy());limithi=torch.tensor(props['upper'].copy());rows=[];started=time.monotonic();taken=False;operation_reference=None;max_positive_power=0.;groove_work=0.;startup_work=0.;passive_energy_error_max=0.;dissipative_work=0.;total_load_energy_residual_max=0.
 capid=gym.get_actor_rigid_body_index(env,knife,gym.get_actor_rigid_body_names(env,knife).index('link_1'),gymapi.DOMAIN_SIM)
 cell_id=gym.get_actor_dof_index(env,knife,cell_local,gymapi.DOMAIN_SIM) if cell_spec else None
 cell_stream=(a.output/'serial-load-cell-physical-steps.jsonl').open('w') if cell_spec else None
 cell_samples=[]
 test_forces=torch.zeros((len(rb),3));test_torques=torch.zeros((len(rb),3));test_stream=(a.output/'opposing-load-physical-steps.jsonl').open('w') if a.opposing_axial_test_load else None
 assert a.opposing_axial_test_load>=0 and not (cell_spec and a.opposing_axial_test_load)
 if recorded_handoff is not None:
  root_states=gymtorch.wrap_tensor(gym.acquire_actor_root_state_tensor(sim));gym.refresh_actor_root_state_tensor(sim);knife_actor_index=gym.get_actor_index(env,knife,gymapi.DOMAIN_SIM);root_states[knife_actor_index]=torch.tensor(recorded_handoff['object_state'],dtype=root_states.dtype);root_ids=torch.tensor([knife_actor_index],dtype=torch.int32);gym.set_actor_root_state_tensor_indexed(sim,gymtorch.unwrap_tensor(root_states),gymtorch.unwrap_tensor(root_ids),1);target=torch.tensor(recorded_handoff['issued_target'],dtype=torch.float32)
 physical_target=target.clone()
 def passive_potential(travel):
  q=np.clip(travel,0,.004);start=a.detent*.004/np.pi*(1-np.cos(np.pi*q/.004));x=(travel-.021)/.0015;groove=-a.detent*.0015*.5*(1+np.cos(np.pi*x)) if abs(x)<1 else 0.;return start+groove
 newknife_previous_q=float(os['pos'][0]);newknife_previous_velocity=0.
 potential_initial=passive_potential(0.)
 (a.output/'physics.json').write_text(json.dumps(dict(physics_hz=a.physics_hz,motor_pd_hz=240,policy_history_hz=30,robot_rigid_body_names=rbnames,robot_dof_names=names,hand_indices=hand.tolist(),arm_indices=arm.tolist(),kp=kp.tolist(),kd=kd.tolist(),effort=limits.tolist(),mass_kg=[b.mass for b in robotb],knife_mass_properties=[dict(mass_kg=b.mass,com_m=[b.com.x,b.com.y,b.com.z],inertia_diagonal_kg_m2=[b.inertia.x.x,b.inertia.y.y,b.inertia.z.z]) for b in gym.get_actor_rigid_body_properties(env,knife)],gravity='All bodies enabled; model-based robot generalized gravity compensation via arm/hand motor efforts; total torque clipped to URDF limits',controller='Explicit finite-torque PD240Hz; original hand gains retained; deployment actuator timing assumption',object=('Free floating, calibrated passive zero-velocity solverbrake capacity; no motion trajectory or grasp constraint' if a.resistance_integration=='solver-brake' else 'Free floating; original passive joint damping/friction plus optional opposing external load'),initial_state_writes_only=True,platform='G2+Wuji v1',policy_inputs='q,FK,50 actual q/action frames, issued targets and known scheduled command, once-loaded relative grip calibration; no live object/slider/contact truth'),indent=2))
 # Reuse the existing G2 contact-pair evaluation API. These values never enter control.
 from scripts.wuji_kinematics import FINGERS
 contact_names={}
 for actor in [robot,table,knife]:
  for n,name in enumerate(gym.get_actor_rigid_body_names(env,actor)):
   contact_names[gym.get_actor_rigid_body_index(env,actor,n,gymapi.DOMAIN_ENV)]=('table' if actor==table else name)
 pair_stream=(a.output/'knife-contact-pairs.jsonl').open('w')
 obstacle_pair_stream=(a.output/'hand-obstacle-contact-pairs.jsonl').open('w')
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
   if not any(n in ['link_0','link_1'] for n in pair):
    if c['lambda']>1e-6 and any(n.startswith('hand_r_') for n in pair):
     normal=c['normal'];obstacle_pair_stream.write(json.dumps(dict(time_s=t,body0=first,body1=second,normal_world=[float(normal[n]) for n in ['x','y','z']],solver_lambda=float(c['lambda']),scope='Evaluation-only 30Hz native contact; not a controller input'))+'\n')
    continue
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
 development_early_stop=None
 if recorded_support and recorded_support.get('development_abort_on_translation_m') is not None:
  assert recorded_handoff is not None and a.grasp_only and not flat_prefix
 fresh_development_abort=flat_prefix.get('development_abort_min_knife_height') if flat_prefix else None
 if fresh_development_abort:assert a.grasp_only and recorded_handoff is None
 try:
  for step in range(int((a.seconds+prefix_duration)*a.physics_hz)):
   gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_jacobian_tensors(sim);t=step/a.physics_hz-prefix_duration
   if step%(a.physics_hz//30)==0:
    previously_issued_target=target.clone()
    q=dof[hand,0].numpy().copy()+sensor_bias+rng.normal(0.,a.observation_noise,20);act=np.zeros(20,dtype=np.float32);policy.record(q,policy.last_action if taken else act)
    if regrasp and pressure_spec is not None and pressure_spec.get('transfer_normal_from_known_arm_fk',False):
     assert isinstance(policy.pressure_adapter,ProprioceptivePressure) or pressure_spec.get('model_implementation')=='analytic-torch-v1'
     fixed_knife_axis=np.asarray(regrasp['expected_knife_world'])[:3,1];measured_wrist=kin.forward(dof[arm,0].numpy());policy.pressure_adapter.normal=measured_wrist[:3,:3].T@fixed_knife_axis
     if pressure_spec.get("preserve_axial_pressure_step") or pressure_spec.get("axial_motor_preload_N"):policy.pressure_adapter.model.axial[0]=torch.as_tensor(measured_wrist[:3,:3].T@np.asarray(regrasp["expected_knife_world"])[:3,2],dtype=torch.float32)
    if policy.support_load_features is not None:
     policy.support_load_features.observe(policy.tensor(q),policy.tensor(previously_issued_target[hand].numpy()),torch.tensor([round(t*30)],device=policy.player.device))
    if a.postpush_pose_update and not pose_updated and t>=0:
     from scripts.wuji_flat_pose_adapter import adapt
     measured_pose=rb[oid].numpy().copy();np.savez_compressed(a.output/'preupdate-trace.npz',**{k:np.asarray([x[k] for x in rows]) for k in rows[0]});estimated_world=transform(measured_pose[:3],measured_pose[3:7]);estimated_world[0,3]+=a.pose_estimate_bias_m
     if a.postpush_pose_input:
      observation=json.loads(a.postpush_pose_input.read_text());assert observation['frame']=='robot_base' and observation['units']=='m_rad';estimated_world=np.asarray(observation['object_world_matrix']);assert estimated_world.shape==(4,4)
     pose_bridge_start=dof[arm,0].numpy().copy();adapted=adapt(estimated_world,planned_knife,acquisition,regrasp,pose_bridge_start,a.table_y,a.pickup_extra_lift_m)
     qabove=adapted['start_q'];qgrasp=adapted['grasp_q'];qlift=adapted['lift_q'];approach_path=adapted['approach'];lift_path=adapted['lift']
     if regrasp:
      regrasp_arm=adapted['regrasp_arm'];regrasp['expected_knife_world']=adapted['expected_knife_world']
     pose_update_diagnostics=adapted['diagnostics'];pose_update_diagnostics.update(time_s=float(t+prefix_duration),pose_source=observation['source'] if a.postpush_pose_input else 'sim_estimate' if a.pose_estimate_bias_m else 'sim_oracle',frequency='one postpush update',translation_bias_x_m=a.pose_estimate_bias_m,visibility_assumption='unoccluded knife after withdrawal')
     (a.output/'postpush-pose-update.json').write_text(json.dumps(pose_update_diagnostics,indent=2));pose_updated=True
    if flat_prefix and t<0:
     ix=min(int(round((t+prefix_duration)*30)),len(flat_prefix['rows'])-1);row=flat_prefix['rows'][ix];aq=np.array(row['arm_q']);hq=np.array(row['hand_q'])
    elif flat_prefix and a.grasp_only and a.seconds<1:
     aq=np.array(flat_prefix['rows'][-1]['arm_q']);hq=np.array(flat_prefix['rows'][-1]['hand_q'])
    elif a.held_diagnostic and t<16:aq=qlift;hq=hold_motor(t,aq)
    elif t<2:aq=pose_bridge_start+smooth(t/2)*(qabove-pose_bridge_start) if pose_bridge_start is not None else qabove;hq=opened
    elif t<5:aq=acquisition_motor(approach_path,smooth((t-2)/3)) if a.acquisition_path else path_motor(1-smooth((t-2)/3)) if a.cartesian_path else qabove+smooth((t-2)/3)*(qgrasp-qabove);hq=opened
    elif t<(6 if a.slow_lift else 8):
     aq=qgrasp;hq=close_motor((t-5)/(1 if a.slow_lift else 3))
     if learned_prefix and not a.grasp_only and t>=a.takeover_seconds:
      if not taken:
       object_est,slider_est=initial_takeover_priors();policy.takeover_estimate(q,target[hand].numpy(),object_est,slider_est,clock_s=t);taken=True
      hq,act=policy.command(q,0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,known_prefix_target=hq)
    elif t<12:
     aq=acquisition_motor(lift_path,smooth((t-(6 if a.slow_lift else 8))/(6 if a.slow_lift else 4))) if a.acquisition_path else path_motor(smooth((t-8)/4)) if a.cartesian_path else qgrasp+smooth((t-8)/4)*(qlift-qgrasp);hq=hold_motor(t,aq) if lift_preload_height else closed
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
      phase=int((t-16)/5);fraction=smooth(min(1.,((t-16)%5)/script_travel_seconds));shift=a.task_stroke_m*(fraction if phase%2==0 else 1-fraction)
      desired=operating_closed.copy();desired[16:]=np.array([np.interp(shift,script_shifts,script_q[:,n]) for n in range(4)])+script_preload
      if a.middle_load_lag_regulation:
       if middle_regulator is None:
        from scripts.g2_middle_deflection_support import MiddleLoadLagRegulator
        middle_regulator=MiddleLoadLagRegulator(middle_spec,middle_support.target)
       desired=middle_regulator.command(q,target[hand].numpy(),desired)
      hq,act=policy.scripted_target(desired)
     else:
      diagnostic_offset=truth_body_diagnostic.correction(q,dof[arm,0].numpy(),rb[oid,3:7].numpy()) if truth_body_diagnostic is not None else None
      hq,act=policy.command(q,a.task_stroke_m if a.extension_only or int((t-16)/5)%2==0 else 0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]),clock_s=t,diagnostic_motor_offset=diagnostic_offset,issued_target_hold=(a.final_issued_target_hold and t>=35) or (a.scheduled_target_holds and ((t-16) if a.extension_only else ((t-16)%5))>=policy.thumb_reference.duration+1/30-1e-7))
    if policy.pressure_adapter is not None and not taken and t>=8:hq=policy.pressure_adapter.command(q,target[hand].numpy(),hq,t)
    if middle_entry and 0<=t<12:
     alpha=smooth((t-10.5)/1.5) if t>=10.5 else 0.
     hq[4:8]=np.asarray(middle_entry['middle_q'])*(1-alpha)+closed[4:8]*alpha
    if a.preclose_middle and 0<=t<8:
     hq[4:8]=closed[4:8]
    if a.fold_outside_fingers and 0<=t<a.fold_release_start+2.5:
     fold=np.array([1.45,closed[9],1.45,1.45,1.45,closed[13],1.45,1.45]);unfold=smooth((t-a.fold_release_start)/2.5) if t>=a.fold_release_start else 0.
     support_closed=closed[8:16].copy()
     if tail_support:support_closed[4:8]=tail_support['ring']
     hq[8:16]=fold*(1-unfold)+support_closed*unfold
    if a.pickup_wrist_pose_follow and 6<=t<12 and pose_updated:
     estimated_rotation=Rotation.from_quat(rb[oid,3:7].numpy()).as_matrix();initial_rotation=np.asarray(pose_update_diagnostics['estimated_world'])[:3,:3];nominal_wrist=kin.forward(aq);nominal_wrist[:3,:3]=estimated_rotation@initial_rotation.T@nominal_wrist[:3,:3]
     aq,follow_error=kin.solve_near(nominal_wrist,dof[arm,0].numpy(),max_step=.08)
    if thumb_tracking is not None and 6<=t<12:
     estimated_knife=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());measured_wrist=kin.forward(dof[arm,0].numpy());hq=thumb_tracking.command(q,hq,np.linalg.inv(estimated_knife)@measured_wrist,float(dof[sid,0]))
    if regrasp and t>=regrasp_times[0]:aq=np.array([np.interp(t,regrasp_times,regrasp_arm[:,i]) for i in range(7)])
    if wrist_roll_curve is not None and t>=16:aq=interpolate(wrist_roll_curve,np.deg2rad(a.wrist_roll_reference_degrees)*smooth((t-16)/2))
    if a.contact_preserving_regrasp and not partial_second_updated and t>=11.8:
     from scripts.wuji_contact_preserving_regrasp import ContactPreservingRegrasp
     actual_object=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());planner=ContactPreservingRegrasp(a.partial_tail_regrasp.parent.parent/'actual-joint-v55/asset-spec.json')
     if a.rail_contact_regrasp:
      from scripts.wuji_rail_contact_regrasp import RailContactRegrasp
      planner=RailContactRegrasp(a.partial_tail_regrasp.parent.parent/'actual-joint-v55/asset-spec.json')
     if a.native_point_regrasp:
      from scripts.wuji_native_point_regrasp import NativePointRegrasp
      planner=NativePointRegrasp(a.partial_tail_regrasp.parent.parent/'actual-joint-v55/asset-spec.json')
     newrows,patherrors=planner.plan(actual_object,dof[arm,0].numpy().copy(),q.copy())
     if a.retain_loaded_motor_offset:
      loaded_offset=previously_issued_target[hand].numpy()-q;loaded_offset[16:]=0.
      for rr in newrows:rr['hand_q']=(np.array(rr['hand_q'])+loaded_offset).tolist()
      newrows[0]['hand_q']=previously_issued_target[hand].numpy().tolist()
     partial_tail['rows']=[r for r in partial_tail['rows'] if r['time_s']<11.8]+newrows;partial_second_updated=True;(a.output/'contact-preserving-pose-plan.json').write_text(json.dumps(dict(time_s=t,pose_source='sim_oracle one update',object_world=actual_object.tolist(),patherrors=patherrors,rows=newrows,physical_state_resets=0),indent=2))
    if a.partial_tail_second_pose_update and not partial_second_updated and t>=11.8:
     actual_object=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());expected_object=np.array(partial_tail['source']['object_world']);delta=actual_object@np.linalg.inv(expected_object);actual_start=kin.forward(dof[arm,0].numpy());actual_hand=q.copy();second_goal=delta@kin.forward(np.array(partial_tail['rows'][min(range(len(partial_tail['rows'])),key=lambda j:abs(partial_tail['rows'][j]['time_s']-13.8))]['arm_q']));goal_hand=np.array(partial_tail['source']['hand_q']);prev_arm=dof[arm,0].numpy().copy()
     from scipy.spatial.transform import Slerp
     rotations=Slerp([0,1],Rotation.from_matrix([actual_start[:3,:3],second_goal[:3,:3]]));newrows=[]
     for row in partial_tail['rows']:
      if row['time_s']<11.8:newrows.append(row);continue
      tt=row['time_s'];u=smooth(np.clip((tt-11.8)/2,0,1));mat=actual_start.copy();mat[:3,:3]=rotations(u).as_matrix();mat[:3,3]=actual_start[:3,3]*(1-u)+second_goal[:3,3]*u
      if tt>=13.8:mat[2,3]+=.16*smooth(np.clip((tt-13.8)/4,0,1))
      prev_arm,err=kin.solve_near(mat,prev_arm);newrows.append(dict(time_s=tt,arm_q=prev_arm.tolist(),hand_q=((1-u)*actual_hand+u*goal_hand).tolist(),ik=err))
     partial_tail['rows']=newrows;partial_second_updated=True;(a.output/'second-pose-update.json').write_text(json.dumps(dict(time_s=t,pose_source='sim_oracle one postregrasp update',estimated_object=actual_object.tolist(),physical_state_resets=0,rows=newrows),indent=2))
    if partial_tail and t>=partial_tail['start_s']:
     tail_times=np.array([r['time_s'] for r in partial_tail['rows']]);tail_arm=np.array([r['arm_q'] for r in partial_tail['rows']]);tail_hand=np.array([r['hand_q'] for r in partial_tail['rows']]);aq=np.array([np.interp(t,tail_times,tail_arm[:,j]) for j in range(7)]);hq=np.array([np.interp(t,tail_times,tail_hand[:,j]) for j in range(20)])
    if partial_clamp and 11.4<=t<partial_tail.get('pose_clamp_end_s',16.):
     current_knife=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());current_wrist=kin.forward(dof[arm,0].numpy());hq=partial_clamp.command(q,hq,np.linalg.inv(current_knife)@current_wrist)
    if a.partial_tail_maintain_index and partial_clamp and 11.8<=t<18:
     current_knife=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());current_wrist=kin.forward(dof[arm,0].numpy());tracked=partial_clamp.command(q,hq,np.linalg.inv(current_knife)@current_wrist);hq[:4]=tracked[:4]
    if fixed_support and t>=fixed_support['start_s']:
     if fixed_support_latch is None:
      fixed_support_latch=dict(arm=previously_issued_target[arm].numpy().copy(),hand=previously_issued_target[hand].numpy().copy(),wrist=kin.forward(previously_issued_target[arm].numpy()))
      (a.output/'fixed-support-latch.json').write_text(json.dumps(dict(time_s=t,arm_target=fixed_support_latch['arm'].tolist(),hand_target=fixed_support_latch['hand'].tolist(),actual_q=q.tolist(),pose_source='sim_oracle development prior at9.8s',physical_state_resets=0),indent=2))
     aq=fixed_support_latch['arm'].copy();hq=fixed_support_latch['hand'].copy();ids=fixed_support['digit_indices'];u=smooth(np.clip((t-fixed_support['start_s'])/fixed_support['close_seconds'],0,1));hq[ids]=(1-u)*hq[ids]+u*np.array(fixed_support['digit_target'])
     lift_start=fixed_support['start_s']+fixed_support['close_seconds']+fixed_support['hold_seconds']
     if t>=lift_start:
      mat=fixed_support_latch['wrist'].copy();mat[2,3]+=fixed_support['lift_m']*smooth(np.clip((t-lift_start)/fixed_support['lift_seconds'],0,1));aq,err=kin.solve_near(mat,dof[arm,0].numpy().copy())
    if dual_push and -prefix_duration+3<=t<-prefix_duration+7:
     observed=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());measured_wrist=kin.forward(dof[arm,0].numpy())
     if dual_push.s.get('follow_actual_wrist'):
      wrist_goal=observed@np.asarray(dual_push.s['wrist_in_knife']);wrist_goal[:3,3]-=observed[:3,0]*.002*smooth(np.clip((t+prefix_duration-3)/.5,0,1));aq,follow_ik=kin.solve_near(wrist_goal,dof[arm,0].numpy().copy(),max_step=.06)
     hq=dual_push.command(q,hq,observed,measured_wrist,t+prefix_duration)
    if dual_push and t<-prefix_duration+12:
     hq[8:16]=np.array([1.45,0.,1.45,1.45,1.45,0.,1.45,1.45])
    if pickup_policy and t>=9.8:
     observed=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());measured_wrist=kin.forward(dof[arm,0].numpy());relmat=np.linalg.inv(measured_wrist)@observed;relpose=np.r_[relmat[:3,3],Rotation.from_matrix(relmat[:3,:3]).as_quat()];measured_all=dof[:27,0].numpy().copy();velocity_all=dof[:27,1].numpy().copy();ix=min(pickup_policy.age,len(pickup_motor_path)-1);motor=pickup_policy.command(measured_all,velocity_all,previously_issued_target.numpy(),relpose,pickup_motor_path[ix]);aq=motor[:7];hq=motor[7:]
    if loaded_thumb_servo and 47<=t+prefix_duration<62:
     aq,hq=loaded_thumb_servo.command(transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),q.copy(),previously_issued_target[arm].numpy().copy(),previously_issued_target[hand].numpy().copy(),t+prefix_duration-47)
    if recorded_handoff is not None and (a.recorded_b_start_s is None or t<0):
     aq=recorded_handoff['issued_target'][:7].copy();hq=recorded_handoff['issued_target'][7:].copy()
     if recorded_support:
      if direct_thumb_servo:
       aq,hq=direct_thumb_servo.command(t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[arm].numpy().copy(),previously_issued_target[hand].numpy().copy(),float(dof[sid,0]))
      elif recorded_live_ring:
       aq,hq=recorded_live_ring.command(t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[arm].numpy().copy(),previously_issued_target[hand].numpy().copy(),float(dof[sid,0]))
      elif 'thumb_material_servo' in recorded_support:
       cfg=recorded_support['thumb_material_servo'];actual_object=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());actual_arm=dof[arm,0].numpy().copy();actual_hand=dof[hand,0].numpy().copy();relative=np.linalg.inv(actual_object)@kin.forward(actual_arm);material=np.array(cfg['material_point']);desired=np.array(cfg['rearface_target']);desired[2]+=cfg.get('stroke_m',.03)*smooth(np.clip((t-cfg.get('push_start_s',3.))/cfg.get('push_duration_s',6.),0,1))
       if cfg.get('slider_paced_roof',False):
        desired=np.array([cfg.get('roof_x_m',0.),cfg.get('roof_y_m',.0045),-.026+float(dof[sid,0])+cfg.get('lead_m',.004)*smooth(np.clip((t-1.)/2.,0,1))]);desired[2]=min(desired[2],cfg.get('final_material_z_m',.004))
       def point(h):
        T=relative@recorded_thumb_kin.forward(h)['hand_r_thumb_pad_link'];return T[:3,:3]@material+T[:3,3]
       current=point(actual_hand);J=np.zeros((3,4))
       for j in range(4):
        hh=actual_hand.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)-current)/1e-5
       error=desired-current;delta=J.T@np.linalg.solve(J@J.T+np.eye(3)*1e-5,error);delta=np.clip(delta,-.025,.025);hq=recorded_handoff['issued_target'][7:].copy();hq[16:]=previously_issued_target[hand].numpy()[16:]+delta
      elif a.recorded_planar_servo:
       actual_object=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());actual_arm=dof[arm,0].numpy().copy()
       if recorded_servo_relative is None:
        recorded_servo_relative=np.linalg.inv(actual_object)@kin.forward(actual_arm);recorded_servo_initial=actual_object[:3,3].copy()
       destination=recorded_servo_initial.copy();destination[1]-=.055;error=destination-actual_object[:3,3];error[2]=0;step_delta=error*np.minimum(1.,.002/max(np.linalg.norm(error),1e-9));desired_wrist=actual_object@recorded_servo_relative;desired_wrist[:3,3]+=step_delta
       aq,ik_diag=kin.solve_near(desired_wrist,actual_arm)
       if a.recorded_planar_retain_arm_load:aq+=recorded_handoff['issued_target'][:7]-recorded_handoff['robot_q'][:7]
       hq=recorded_handoff['issued_target'][7:].copy()
      elif 'rows' in recorded_support:
       rr=recorded_support['rows'];tt=np.array([r['time_s'] for r in rr]);aq=np.array([np.interp(t+(a.recorded_b_start_s or 0.),tt,[r['arm_q'][j] for r in rr]) for j in range(7)]);hq=np.array([np.interp(t+(a.recorded_b_start_s or 0.),tt,[r['hand_q'][j] for r in rr]) for j in range(20)])
      else:
       u=smooth(np.clip((t-recorded_support['start_s'])/recorded_support['ramp_s'],0,1));hq+=np.array(recorded_support['hand_delta'])*u
    if recorded_grip_roll_servo:
     hq=recorded_grip_roll_servo.correct(t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[hand].numpy().copy(),hq)
    if recorded_joint_path_tracking:
     hq=recorded_joint_path_tracking.correct(t,dof[hand,0].numpy().copy(),hq)
    if recorded_material_carrier:
     hq=recorded_material_carrier.correct(t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[hand].numpy().copy(),hq,float(dof[sid,0]))
    if recorded_idle_middle_clearance:
     hq=recorded_idle_middle_clearance.correct(t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[arm].numpy().copy(),previously_issued_target[hand].numpy().copy(),aq,hq,float(dof[sid,0]))
    # The route clock must not depend on the planned later episode duration.
    # Subtracting then adding a large prefix changed a float32 wrist target by
    # one ULP during the acquired lift; derive time directly from step instead.
    elapsed=step/a.physics_hz
    if direct_pickup:
     aq,hq=direct_pickup.command(elapsed,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),dof[hand,0].numpy().copy(),previously_issued_target[arm].numpy().copy(),previously_issued_target[hand].numpy().copy(),float(dof[sid,0]))
    if prefix_pose_adapter and ((recorded_handoff is None and t<0) or (recorded_handoff is not None and a.grasp_only)):
     adaptation_elapsed=elapsed if recorded_handoff is None else t+float(json.loads((a.recorded_handoff/"manifest.json").read_text())["takeover_elapsed_s"])
     aq=prefix_pose_adapter.command(adaptation_elapsed,aq,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),a.pose_estimate_bias_m)
    transport_t=t if recorded_handoff is not None else elapsed-36.
    if loaded_table_transport and 0<=transport_t<24:
     aq=loaded_table_transport.command(transport_t,transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy()),dof[arm,0].numpy().copy(),previously_issued_target[arm].numpy().copy())
    if loaded_table_transport and recorded_handoff is None and 60<=elapsed<82:
     if adaptive_exit is None:
      adaptive_exit=dict(arm=previously_issued_target[arm].numpy().copy(),hand=previously_issued_target[hand].numpy().copy(),wrist=kin.forward(dof[arm,0].numpy().copy()),seed=dof[arm,0].numpy().copy())
      release_rows=json.loads(Path('runs/flat-table-20261006/development/b-compatible-clamp-release-native-20261006/support.json').read_text())['rows'];adaptive_exit['delta']=np.array(release_rows[-1]['hand_q'])-np.array(release_rows[0]['hand_q'])
     exit_t=elapsed-60
     if exit_t<5:
      aq=adaptive_exit['arm'];hq=adaptive_exit['hand']+smooth(np.clip(exit_t/3.,0,1))*adaptive_exit['delta']
     elif exit_t<12:
      exit_w=adaptive_exit['wrist'].copy();exit_w[0,3]-=.1*min((exit_t-5)/3,1);exit_w[2,3]+=.18*np.clip((exit_t-8)/3,0,1);aq,exit_ik=kin.solve_near(exit_w,adaptive_exit['seed']);adaptive_exit['seed']=aq.copy();hq=adaptive_exit['hand']+adaptive_exit['delta'];adaptive_exit['end_arm']=aq.copy()
     else:
      bridge_u=smooth(np.clip((exit_t-12)/8,0,1));bridge_row=flat_prefix['rows'][-1];aq=(1-bridge_u)*adaptive_exit['end_arm']+bridge_u*np.array(bridge_row['arm_q']);hq=(1-bridge_u)*(adaptive_exit['hand']+adaptive_exit['delta'])+bridge_u*np.array(bridge_row['hand_q'])
    if a.relax_idle_ring and t>=14.5:
     hq[14]=(1-smooth((t-14.5)/2.))*hq[14]+smooth((t-14.5)/2.)*min(float(hq[14]),1.1)
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
    if newknife_resistance:brake_capacity=newknife_capacity(newknife_resistance,float(dof[sid,0])-float(knife_parameters['initial_slider_q_m']),newknife_previous_velocity)
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
   gym.refresh_dof_state_tensor(sim);next_travel=float(dof[sid,0])-lower;newknife_previous_velocity=(float(dof[sid,0])-newknife_previous_q)*a.physics_hz;newknife_previous_q=float(dof[sid,0]);delta_travel=next_travel-travel;groove_work+=groove_load*delta_travel;startup_work+=start_load*delta_travel;dissipative_work+=run_load*delta_travel;passive_energy_error=groove_work+startup_work+passive_potential(next_travel)-potential_initial;passive_energy_error_max=max(passive_energy_error_max,passive_energy_error);total_load_energy_residual_max=max(total_load_energy_residual_max,passive_energy_error+dissipative_work)
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
     close_aim=rb[oid,:3].numpy()+np.array([0.,0.,.055]);close_offset=np.array([.40,-.18,.30])*a.close_camera_scale
     if a.frame_complete_hand:
      hand_points=rb[[j for j,n in enumerate(rbnames) if n.startswith('hand_r_')],:3].numpy();obj_frame=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());knife_points=obj_frame[:3,3]+np.array([[-.073],[.073]])*obj_frame[:3,2];points=np.r_[hand_points,knife_points];close_aim=(points.min(0)+points.max(0))*.5;direction=np.array(a.close_camera_direction or [.40,-.18,.30]);direction/=np.linalg.norm(direction);right=np.cross(-direction,np.array([0.,0.,1.]));right/=np.linalg.norm(right);up=np.cross(right,-direction);rel=points-close_aim;depth=rel@direction;vertical_tan=np.tan(np.deg2rad(65/2))*720/960;required=np.maximum(abs(rel@right)/np.tan(np.deg2rad(65/2)),abs(rel@up)/vertical_tan)+depth;distance=max(.24,float(required.max())+.08);close_offset=direction*distance
     if supportwriter:
      spoints=rb[[j for j,n in enumerate(rbnames) if n.startswith('hand_r_')],:3].numpy();so=transform(rb[oid,:3].numpy(),rb[oid,3:7].numpy());spoints=np.r_[spoints,so[:3,3]+np.array([[-.073],[.073]])*so[:3,2]];sa=(spoints.min(0)+spoints.max(0))*.5;sd=np.array(a.support_camera_direction,dtype=float);sd/=np.linalg.norm(sd);sr=np.cross(-sd,np.array([0.,0.,1.]));sr/=np.linalg.norm(sr);su=np.cross(sr,-sd);rel=spoints-sa;req=np.maximum(abs(rel@sr)/np.tan(np.deg2rad(65/2)),abs(rel@su)/(np.tan(np.deg2rad(65/2))*720/960))+rel@sd;distance=max(.24,float(req.max())+.08);gym.set_camera_location(supportcam,env,gymapi.Vec3(*(sa+sd*distance)),gymapi.Vec3(*sa))
     gym.set_camera_location(closecam,env,gymapi.Vec3(*(close_aim+close_offset)),gymapi.Vec3(*close_aim));gym.step_graphics(sim);gym.render_all_camera_sensors(sim);im=np.asarray(gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(720,960,4)[...,:3];writer.append_data(im);im2=np.asarray(gym.get_camera_image(sim,env,closecam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(720,960,4)[...,:3];closewriter.append_data(im2)
     if supportwriter:
      simage=np.asarray(gym.get_camera_image(sim,env,supportcam,gymapi.IMAGE_COLOR),dtype=np.uint8).reshape(720,960,4)[...,:3];supportwriter.append_data(simage)
   if recorded_support and recorded_support.get('development_abort_on_translation_m') is not None and step%(a.physics_hz//30)==a.physics_hz//30-1:
    drift=float(np.linalg.norm(rb[oid,:3].numpy()-recorded_handoff['object_state'][:3]))
    if drift>recorded_support['development_abort_on_translation_m']:
     development_early_stop=dict(time_s=float(t+1/a.physics_hz),translation_m=drift,threshold_m=recorded_support['development_abort_on_translation_m'],scope='Development-only evaluation cutoff after invalidating intendedconstantknife reference; trace/contact/bothvideos saved; truncatedrun not success')
     (a.output/'development-early-stop.json').write_text(json.dumps(development_early_stop,indent=2));print(json.dumps(development_early_stop),flush=True);break
   if fresh_development_abort and step%(a.physics_hz//30)==a.physics_hz//30-1:
    elapsed=t+prefix_duration+1/a.physics_hz
    if elapsed>=fresh_development_abort['after_elapsed_s'] and float(rb[oid,2])<fresh_development_abort['minimum_z_m']:
     development_early_stop=dict(time_s=float(t+1/a.physics_hz),elapsed_s=float(elapsed),knife_z_m=float(rb[oid,2]),threshold=fresh_development_abort,scope='Development-only cutoff of failed fresh lift, trace/native/bothvideos retained; no success claim or physical intervention')
     (a.output/'development-early-stop.json').write_text(json.dumps(development_early_stop,indent=2));print(json.dumps(development_early_stop),flush=True);break
   if step%1200==0:print(json.dumps(dict(t=t,object_height=float(rb[oid,2]),slider=float(dof[sid,0]),arm_tracking_max=float(abs(target[arm]-dof[arm,0]).max()))),flush=True)
  if prefix_pose_adapter:(a.output/'prefix-pose-adaptation.json').write_text(json.dumps(dict(first=prefix_pose_adapter.first if prefix_pose_adapter.delta is not None else None,records=prefix_pose_adapter.records,physical_state_resets=0),indent=2))
  if loaded_table_transport:(a.output/'loaded-table-pose-records.json').write_text(json.dumps(dict(source='sim_oracle30Hz',records=loaded_table_transport.records,physical_state_resets=0),indent=2))
  if pickup_policy:(a.output/'pickup-policy-records.json').write_text(json.dumps(dict(source='sim_oracle30Hz',records=pickup_policy.records,physical_state_resets=0),indent=2))
  if dual_push:(a.output/'dual-push-pose-records.json').write_text(json.dumps(dict(source='sim_oracle30Hz',records=dual_push.records,physical_state_resets=0),indent=2))
  trace={k:np.asarray([x[k] for x in rows]) for k in rows[0]};np.savez_compressed(a.output/'trace.npz',**trace);h=trace['object'][:,2];held=(trace['time']>=12)&(trace['time']<16);opmask=trace['time']>=16
  endpoints=[]
  for end in [21,26,31,36]:
   mask=(trace['time']>end-.3)&(trace['time']<=end)
   endpoints.append(float((trace['slider'][mask]-lower).mean()) if mask.any() and a.seconds>=end and not a.grasp_only else None)
  opened_ok=all(x is not None and x>.025 for x in [endpoints[0],endpoints[2]])
  closed_ok=all(x is not None and x<.008 for x in [endpoints[1],endpoints[3]])
  report=dict(start='Knife resting on table; hand initially open at planned clearance (11.5cm for registered Cartesian path,16cm otherwise)',methods=('Motor-only scripted continuous-IK approach/close/lift' if a.cartesian_path or a.acquisition_path else 'Motor-only scripted joint-space approach/close/lift')+'; finite-torque gravity-compensated arm/hand; '+('pickup-only diagnostic' if a.grasp_only else ('offline-calibrated scheduled thumb IK with static joint preload' if thumb_script is not None else 'Scheduled calibrated rolling-thumb reference plus learned bounded residual using R800 legal features' if a.residual_checkpoint and policy.action_base_mode=='geometric' else 'R800 legal features plus learned bounded direct action' if a.residual_checkpoint and policy.action_base_mode=='zero' else 'R800+bounded residual' if a.residual_checkpoint else 'R800')+' after16s with once-loaded relative-grip calibration estimate'),lifted_clear=bool((h[held]>a.table_height+.03).all()) if held.any() else False,operation_stays_clear=bool((h[opmask]>a.table_height+.03).all()) if opmask.any() else False,meaningful_extension=opened_ok,retraction_after31s=closed_ok,full_success=False,minimum_hold_height_m=float(h[held].min()) if held.any() else None,max_object_height_m=float(h.max()),wall_seconds=time.monotonic()-started,positive_load_power_max_W=max_positive_power,weight_sha256={(str(x.relative_to(R)) if R in x.parents else str(x)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth']+([R/a.residual_checkpoint] if a.residual_checkpoint else [])},scope='Continuous physics attempt, no stage state writes. Meaningful25mm extension and8mm return are predeclared demo diagnostics; inherited40mm command unchanged. No preciseS5claim.')
  report['actual_recorded_duration_s']=float(trace['time'][-1]-trace['time'][0]+1/30)
  report['development_early_stop']=development_early_stop
  if pose_update_diagnostics:report['pose_update']=pose_update_diagnostics
  if partial_tail:report['partial_tail_regrasp']=dict(input=partial_tail,physical_state_resets=0,stageB='not connected; new pickup diagnostic motor reference')
  if flat_prefix:report['flat_table_prefix']=dict(input=flat_prefix,physical_state_resets_after_initialization=0,stage_clock_offset_s=prefix_duration)
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
   report['integration_diagnostics']=dict(physics_hz=a.physics_hz,motor_pd_hz=240,policy_history_hz=30,brake_capacity_max_N=float(trace['solver_brake_capacity_N'].max()),brake_capacity_operation_min_N=float(trace['solver_brake_capacity_N'][opmask].min()) if opmask.any() else None,scope='Passive nativezero-velocity jointbrake with250 damping and calibratedNewtonforcecap; physics-only time/position modulatescap. Replaces explicit regularizedfriction and conservativepotential by dissipative startup/groove barriers. No positivevelocity/positiontarget, nohanddrive/rail/criteriachange. Actualbrakeforce incontactdemo unavailable; cap isverifiedfixtureparameter, notmeasuredworldtraction or realresistance.',calibration='runs/support-pressure-20261003/calibration/solver-brake-v3/calibration.json')
  if newknife_resistance:
   report['integration_diagnostics'].update(damping_Ns_m=float(newknife_resistance.get('damping_Ns_m',25000)),scope='Passive native zero-velocity brake; capacity depends only on relative slider position and previous physical-step displacement velocity. No command/clock modulation and no measured brake-force claim.',calibration='research/newknife-20261005/RESISTANCE-CALIBRATION.json')
  report['opposing_axial_test_load_N']=a.opposing_axial_test_load
  report['serial_load_cell_diagnostic']=cell_spec
  report['original_scene_axial_force_measurement_completed']=False
  report['thumb_reference_override']=str(a.thumb_reference_override) if a.thumb_reference_override else None
  report['scheduled_target_holds']=a.scheduled_target_holds
  report['scheduled_target_hold_scope']='Knownclock finitePD positionhold after fullreference stroke plusoneframe, network/reference/measuredhistory continue; no pressure/force targetguarantee' if a.scheduled_target_holds else None
  report['learned_action_parameterization']=policy.action_parameterization
  report['support_load_feature_spec']=policy.support_load_feature_spec
  report['support_command_period_frames']=policy.support_command_period
  report['support_decision_scope']='Knownclock supportresidual held between decisions; thumb30Hz; oneactual issuedhistory update each30Hz'
  report['learned_takeover_seconds']=a.takeover_seconds if a.residual_checkpoint else None
  report['support_latch_after_preparation']=policy.support_latch_after_preparation
  report['support_delta_coordinates']={k:v for k,v in policy.support_delta_coordinates.spec.items() if k!='reference_actor_state'} if policy.support_delta_coordinates is not None else None
  report['known_task_schedule_seconds']=[16,20+1/30,a.seconds] if a.extension_only else [16,21,26,31,36]
  report['extension_only']=a.extension_only
  if a.extension_only:report.update(operation_evaluated=a.seconds>=22,diagnostic='Single forward known-clock goal then hold; no retraction, no object state trigger',scope='Continuous pickup and single-extension physical simulation; extension-only evaluator is authoritative')
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
  report.update(task_stroke_m=a.task_stroke_m,initial_slider_q_m=knife_parameters.get('initial_slider_q_m',lower),newknife_resistance=newknife_resistance,physical_asset=str(a.knife_asset),physical_asset_sha256=hashlib.sha256(knife_path.read_bytes()).hexdigest(),physical_dimensions_WTL_m=knife_parameters['handle_size'],physical_slider_size_WTL_m=knife_parameters['slider_size'],initial_geometry_estimate=initial_estimate,policy_geometry_estimate_scope=('Explicit initial noisy geometry estimate, common offline IK adaptation and once-loaded prior; no physicalasset ID or runtime object/contact input' if initial_estimate else 'Unchanged nominal geometry and once-loaded prior calibration; physical asset identity never given to actor'),hand_friction=a.hand_friction,knife_friction=a.knife_friction,load_profile=load_profile,load_frequency_rad_s=a.load_frequency,observation_noise_std_rad=a.observation_noise,observation_bias_bound_rad=a.observation_bias,seed=a.seed,initial_pose_prior_scope=('Once known tabletop+initialgeometry estimate transformedby measuredG2armFK atclosure takeover; no currentobject/slidertruth' if policy.table_initial_prior_from_measured_arm else 'Once loaded nominal heldprior'),loaded_weight_use='Interface initialization only; learned actor never called' if a.grasp_only or thumb_script is not None else 'Frozen R800 and optional residual actor executed after50 actual history frames',residual_checkpoint=str(a.residual_checkpoint),thumb_script=str(a.thumb_script),thumb_script_scope='Known 40mm schedule+offline geometric trajectory and joint preload, not constant force or live state feedback' if thumb_script is not None else None,thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,added_load_N=a.load,passive_startup_detent_amplitude_N=a.detent,variable_load=a.variable_load,load_scope='Calibrated passive zero-velocity solverbrake capacity with dissipative startup/groove; no realtotalresistance or instantaneousfrictionmeasurement claim.' if a.resistance_integration=='solver-brake' else 'Engineering added load plus original passive friction/damping; no measured real total-resistance ceiling. Groove is finite passive potential; positive descent power is stored energy.')
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
  if force_meter and opmask.any():
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
  report['thumb_residual_scale_override_rad']=a.thumb_residual_scale_override
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
 except BaseException as error:
  # Keep the actual prefix when a controller fails. It is an incomplete
  # episode, never a successful demonstration or an exact simulator resume.
  import traceback
  failure=dict(exception_type=type(error).__name__,message=str(error),
      traceback=traceback.format_exc(),incomplete_episode=True,
      physical_asset=str(a.knife_asset),full_success=False,
      stage_clock_offset_s=prefix_duration,saved_actual_frames=len(rows))
  if rows:
   partial={key:np.asarray([row[key] for row in rows]) for key in rows[0]}
   np.savez_compressed(a.output/'trace.npz',**partial)
   failure['actual_recorded_duration_s']=float(partial['time'][-1]-partial['time'][0]+1/30)
  (a.output/'failure.json').write_text(json.dumps(failure,indent=2))
  if not (a.output/'report.json').exists():
   (a.output/'report.json').write_text(json.dumps(failure,indent=2))
  raise
 finally:
  if force_meter:force_meter.close()
  if cell_stream:cell_stream.close()
  if test_stream:test_stream.close()
  pair_stream.close()
  if candidate_stream:candidate_stream.close()
  if writer:writer.close();closewriter.close()
  if supportwriter:supportwriter.close()
  gym.destroy_sim(sim)
if __name__=='__main__':main()
