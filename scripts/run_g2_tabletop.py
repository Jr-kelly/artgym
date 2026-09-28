"""Continuous G2+Wuji tabletop baseline, no object constraint or slider actuation.

All state setters occur once, before the first physics step. Afterward only
joint drive targets are written; frozen policies drive the operation phase.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

from isaacgym import gymapi, gymtorch
import numpy as np
import torch
from scipy.spatial.transform import Rotation, Slerp
from omegaconf import OmegaConf

from scripts.wuji_goal_common import configuration
from scripts.g2_kinematics import G2Kinematics,transform,minimal_alignment
from scripts.g2_frozen_policy import FrozenPolicy,pose
from scripts.g2_tabletop_metrics import acquisition_hold

ROOT=Path(__file__).resolve().parents[1]
PUBLISHED=Path('/data/research/artgym-experiments-20260921/runs/wuji-goal/release-core-teacher-student-20260924-v1')
PREFIX='wuji-core-teacher-student-20260924-'


def smooth(s): return 10*s**3-15*s**4+6*s**5


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group',choices=['A','B','C'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--teacher',type=Path,default=PUBLISHED/(PREFIX+'teacher.pth'))
    parser.add_argument('--student',type=Path,default=PUBLISHED/(PREFIX+'student.pth'))
    parser.add_argument('--grasp',type=int,default=0,choices=[0,1,2])
    parser.add_argument('--preset-support-gate',action='store_true',help='A v2: judge stable nonthumb support without requiring thumb contact; original acquisition gate separately retained')
    parser.add_argument('--preset-preparation',type=Path,help='A-only motor-only single-digit preparation after actual settle; fixed-reference hold gates')
    parser.add_argument('--preset-candidate',type=Path,help='A-only explicit70-value candidate state before the first physics step, followed by2s actual settling; never a continuous acquisition result.')
    parser.add_argument('--video',action='store_true')
    parser.add_argument('--seconds',type=float,default=20)
    parser.add_argument('--arm-gain-scale',type=float,default=1.)
    parser.add_argument('--arm-damping-scale',type=float,default=1.)
    parser.add_argument('--arm-gravity',choices=['on','off'],default='on')
    parser.add_argument('--hand-gravity',action='store_true',help='Labeled alternate physics: enable all hand-body gravity from the first physics step; default frozen baseline remains OFF')
    parser.add_argument('--hand-gravity-compensation',action='store_true',help='Explicit motor-only URDF gravity/stiffness bias, capped .08rad and original total target slew/limits; requires --hand-gravity')
    parser.add_argument('--dx',type=float,default=0.)
    parser.add_argument('--dy',type=float,default=0.)
    parser.add_argument('--yaw',type=float,default=0.)
    parser.add_argument('--close-height',type=float,default=0.)
    parser.add_argument('--settle-seconds',type=float,default=2.)
    parser.add_argument('--only-grasp',action='store_true')
    parser.add_argument('--policy-action-mode',choices=['full','thumb-only'],default='full',help='Explicit frozen-policy action-component ablation. Thumb-only holds other motor references; raw and executed actions are both recorded.')
    parser.add_argument('--geometric-operation',type=Path,help='Named privileged thumb IK feedback baseline; frozen actor not executed')
    parser.add_argument('--learned-operation-policy',type=Path,help='New privileged local S controller; requires thumb-only teacher channel for support route. Never original full-teacher success.')
    parser.add_argument('--operation-static-policy',action='store_true',help='Named S ablation: one actual initial network inference, then fixed20-joint output plus unchanged geometric thumb path; not a trained student')
    parser.add_argument('--local-reset-quaternion-compat',action='store_true',help='Frozen local policy diagnostic: match the legacy reset wrist quaternion sign on the FIRST observation only; no physical state write.')
    parser.add_argument('--learned-hold-policy',type=Path,help='Diagnostic22s learned H after actual gait, before real settling. Not slider-operation success.')
    parser.add_argument('--fixed-preparation-hold',action='store_true',help='Named22s fixed-motor H control after actual gait, before real settling; same hold criteria, no learned H output')
    parser.add_argument('--camera',choices=['wide','hand'],default='wide')
    parser.add_argument('--operation-yaw',type=float,default=0.)
    parser.add_argument('--hand-only-diagnostic',action='store_true')
    parser.add_argument('--grasp-roll',type=float,default=0.,help='Rotate wrist about knife long axis; initial knife stays flat.')
    parser.add_argument('--pregrasp',choices=['extended','support-curled'],default='extended')
    parser.add_argument('--grasp-plan',type=Path,help='Explicit, recorded geometric motor plan; never sets physics state.')
    parser.add_argument('--seat-seconds',type=float,default=0.,help='After lift interpolate fingers to original functional targets.')
    parser.add_argument('--arm-integral-gain',type=float,default=0.,help='Joint-error integral compensation through existing finite torque drives.')
    parser.add_argument('--transport-path',choices=['joint','level'],default='joint')
    parser.add_argument('--seating-plan',type=Path,help='Contact-guided wrist/finger motor waypoints, executed in air without object constraints.')
    parser.add_argument('--seat-feedback',choices=['none','object-truth','translation-truth'],default='none',help='Explicit oracle localization control during seating only; not a deployable estimator.')
    parser.add_argument('--wrist-posture',type=float,help='Redundant arm joint7 target for initial approach/grasp/lift IK only.')
    parser.add_argument('--acquisition-arm-seed',type=Path,help='G2 IK seed for the initial above-table pose; only initialization before physics.')
    parser.add_argument('--cartesian-acquisition',action='store_true',help='Approach/lift through continuous Cartesian IK; close holds the reached arm command. Separate acquisition control condition.')
    parser.add_argument('--post-gait-roll',type=float,default=0.,help='Declared assembly roll about knife length after successful gait; bound45deg, no object actuation.')
    parser.add_argument('--assembly-roll-seconds',type=float,default=4.)
    parser.add_argument('--roll-tracking-correction',action='store_true',help='One bounded motor correction toward the unchanged declared roll endpoint before release; oracle control diagnostic.')
    parser.add_argument('--post-roll-gait-plan',type=Path,help='Optional motor gait after assembly roll; fixed planned roll endpoint remains world reference.')
    parser.add_argument('--seat-at-operation',action='store_true',help='Carry held knife to the trained object attitude before changing grasp contacts.')
    parser.add_argument('--operation-pose',type=Path,help='Explicit wrist 4x4 pose for labeled gravity/interface diagnostics.')
    parser.add_argument('--operation-seed',type=Path,help='A-only measured G2 joint seed for solving an already reached wrist pose; never changes limits.')
    parser.add_argument('--post-acquisition-pose',type=Path,help='B/C-only bounded wrist adjustment after acquisition and before history settling; preserves the preceding acquisition path. Hand motor targets stay fixed.')
    parser.add_argument('--seat-finger-feedback',choices=['none','object-truth'],default='none',help='Oracle finger contact correction; requires an inverse-statics plan.')
    parser.add_argument('--seat-object-servo',action='store_true',help='Bounded truth object-pose servo via hand motor targets only, during acquisition.')
    parser.add_argument('--seat-finger-mode',choices=['contact','residual'],default='contact',help='Residual adds only restoring motor corrections to the geometric holding path.')
    parser.add_argument('--table-supported-seat',action='store_true',help='After normal flat pickup, stand the knife on its modeled flat end on the same table, regrasp, then relift.')
    parser.add_argument('--upright-yaw',type=float,default=250.)
    parser.add_argument('--table-regrasp-plan',type=Path,help='Release the standing knife, retract, approach with a functional open hand, and close instead of sliding contacts around it.')
    parser.add_argument('--preset-slider-offset',type=float,default=0.,help='A-only diagnosis of a passively opened slider at takeover; command origin remains the original lower limit.')
    parser.add_argument('--level-standing-knife',action='store_true',help='Use bounded measured wrist corrections to level the supported knife before release.')
    parser.add_argument('--measured-release',action='store_true',help='Unload pinch pressure, then open away from the measured standing knife.')
    parser.add_argument('--upright-end',choices=['positive','negative'],default='positive',help='Modeled knife end placed on the table; negative keeps gravity directed toward slider closure.')
    parser.add_argument('--preset-object-axis-offset',type=float,default=0.,help='A-only measured-init diagnostic, shifting the preset knife along its own long axis.')
    parser.add_argument('--table-height',type=float,default=.75,help='Explicit scene condition in meters; hand and knife physical properties remain frozen.')
    parser.add_argument('--upright-path',choices=['combined','yaw-then-tip','tip-then-yaw'],default='combined',help='Separate turning from tipping to limit gravity across the pinch direction.')
    parser.add_argument('--upright-height',type=float,default=.98,help='Free-space knife center height before lowering onto the table.')
    parser.add_argument('--upright-orient-seconds',type=float,default=5.,help='Duration of the final upright orientation phase; changes motor trajectory timing only.')
    parser.add_argument('--standing-level-gate',choices=['tilt','support-projection'],default='tilt',help='Alternate release precheck uses the actual assembly COM gravity projection inside the modeled end footprint with 0.5mm margin. Physical release must still succeed.')
    parser.add_argument('--gravity-close-before-takeover',action='store_true',help='After functional regrasp, tilt the held knife axis upward for 3s and return to operation, allowing passive gravity closure. Only arm motor targets are commanded.')
    parser.add_argument('--gravity-close-support',choices=['pinch','tray'],default='pinch',help='Tray tilts the knife axis 30 degrees upward, with gravity pressing its back onto the four fingers, and opens only the thumb during passive closure.')
    parser.add_argument('--gravity-close-yaw',type=float,default=0.,help='Additional world yaw during gravity closure to avoid G2 arm limits; preserves the gravity direction in the knife frame.')
    parser.add_argument('--air-flip',type=float,default=0.,choices=[-180.,0.,180.],help='After lifting, pronate the held hand by 180 degrees about its horizontal forward direction using G2 motor targets only.')
    parser.add_argument('--air-flip-seconds',type=float,default=10.)
    parser.add_argument('--air-flip-axis',choices=['wrist-forward','knife-length'],default='wrist-forward',help='Acquisition planning axis; both use a fixed measured horizontal axis and motors only')
    parser.add_argument('--air-flip-shift',type=float,nargs=3,default=[0.,0.,0.],help='Smooth world translation of the planned wrist-flip pivot; robot motion only.')
    parser.add_argument('--air-flip-only',action='store_true',help='Diagnostic: stop after free-space flip and actual settling, without transport or policy operation.')
    parser.add_argument('--lift-height',type=float,default=.20,help='Vertical wrist lift in metres; no object state changes.')
    parser.add_argument('--pickup-retention-hold',type=float,default=0.,choices=[0.,1.],help='Separate fixed-reference1s physical hold after lift, gate before flip; records every finger without asserting force')
    parser.add_argument('--table-settle-only',action='store_true',help='Counted B diagnostic: natural2s settle, save actual pose, no approach/grasp')
    parser.add_argument('--short-lift-diagnostic',action='store_true',help='B-only2-5cm short lift; separate from full acquisition')
    parser.add_argument('--pickup-only',action='store_true',help='Isolated continuous table pickup plus1s hold, no flip/transport/policy; does not claim full task success')
    parser.add_argument('--closed-settle-seconds',type=float,default=0.,choices=[0.,1.],help='Explicit single-factor closed-hand dwell on the original table before first lift; actual state remains continuous')
    parser.add_argument('--pickup-finger-feedback',action='store_true',help='Explicit privileged bounded contact-following motor controller during lift/hold only; no model training or object actuation')
    parser.add_argument('--knife-spec',type=Path,help='New generated asset-spec.json; never overwrites baseline. Only B acquisition diagnostics until frozen policy geometry/interface audit is complete.')
    parser.add_argument('--slider-face',choices=['up','down'],default='up',help='Initial tabletop placement; down starts above the protruding passive slider and settles freely.')
    parser.add_argument('--table-localization',choices=['configured','settled-truth'],default='configured',help='Acquisition-only ideal localization after natural tabletop settling.')
    parser.add_argument('--gait-plan',type=Path,help='Sequential single-digit motor plan with fixed-reference one-second hold gates after actual air flip.')
    parser.add_argument('--gait-arm-retarget-reference',type=Path,help='Explicit alternate controller: rigidly retarget original wrist path at actual gait motor reference; fingers and gates unchanged')
    parser.add_argument('--operation-input-ablation',choices=['fixed-body-live-slider','fixed-body-proprio-slider'],help='S-only frozen-policy input diagnostic with ideal one-time initialization; acquisition/H still privileged')
    parser.add_argument('--gait-translation-before-alignment',action='store_true',help='Separate control variant: physical4mm-capped translation then hold, original alignment5mm gate unchanged')
    parser.add_argument('--gait-pinky-retarget',action='store_true',help='Explicit one-time truth-based adaptation of small-finger touch/close after actual clearance hold; other fingers and all gates unchanged')
    parser.add_argument('--stay-after-gait',action='store_true',help='Keep achieved wrist pose for settling and optional policy operation; no transport.')
    parser.add_argument('--closeup',action='store_true',help='Additional synchronized camera; follows robot wrist, never affects physics.')
    parser.add_argument('--contact-diagnostics',action='store_true',help='Record whole-thumb conservative collision separation every control frame.')
    args=parser.parse_args()
    assert not args.pickup_only or (args.only_grasp and args.pickup_retention_hold==1 and not args.air_flip and not args.gait_plan)
    assert not args.pickup_finger_feedback or args.pickup_only
    knife_geometry=None
    knife_asset_path=ROOT/'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf'
    if args.knife_spec:
        assert (args.group=='A' and args.preset_candidate) or (args.group=='B' and args.only_grasp and (args.pickup_only or args.air_flip_only or args.table_settle_only)), 'New geometry: presetA or acquisition diagnostic only until further interface audit'
        assert not args.pickup_finger_feedback and not args.table_supported_seat and not args.gait_plan
        from scripts.g2_knife_geometry import KnifeGeometry
        knife_geometry=KnifeGeometry(args.knife_spec);knife_asset_path=knife_geometry.urdf
    assert not args.operation_static_policy or (args.learned_operation_policy and args.operation_input_ablation is None)
    assert not args.fixed_preparation_hold or (args.group!='A' and args.learned_hold_policy is None), 'Fixed and learned preparation holds are exclusive continuous conditions'
    if args.hand_gravity_compensation:
        assert args.hand_gravity and not args.hand_only_diagnostic, 'Gravity motor compensation requires full G2 and hand gravity ON'
    # A plan with clearance gates needs actual geometry measurements. Missing
    # diagnostics used to reach step1989 then mislabel an absent value (-1)
    # as a physical clearance failure. Enable the required measurement up front.
    if args.gait_plan:
        gait_requirements=json.loads(args.gait_plan.read_text())
        if any('require_thumb_gap_m' in stage for stage in gait_requirements['stages']):
            args.contact_diagnostics=True
    if args.learned_operation_policy:
        assert args.policy_action_mode=='thumb-only', 'Composite controller requires explicit teacher thumb-only channel'
    if args.learned_operation_policy or args.learned_hold_policy:
        assert args.group!='C', 'New learner is privileged; student history must explicitly encode its separate motor channel before C is evaluated'
    assert not args.learned_hold_policy or args.group!='A'
    args.output.mkdir(parents=True,exist_ok=False)
    if args.knife_spec:
        (args.output/'knife-asset-spec.json').write_text(args.knife_spec.read_text())
    assert not args.hand_only_diagnostic or args.group=='A'
    assert not args.seat_object_servo or args.seat_finger_feedback=='object-truth'
    assert args.seat_finger_mode!='residual' or args.seat_object_servo
    assert not args.table_supported_seat or (args.group!='A' and (args.table_regrasp_plan or (args.seating_plan and args.seat_seconds>0)) and not args.seat_at_operation)
    assert not args.table_regrasp_plan or args.table_supported_seat
    assert not args.post_gait_roll or (args.gait_plan and args.group!='A' and abs(args.post_gait_roll)<=45 and args.assembly_roll_seconds>0)
    assert not args.post_roll_gait_plan or args.post_gait_roll
    assert not args.roll_tracking_correction or args.post_gait_roll
    assert (args.preset_slider_offset==0 and args.preset_object_axis_offset==0) or args.group=='A'
    assert not (args.level_standing_knife or args.measured_release) or args.table_regrasp_plan
    assert 5<=args.upright_orient_seconds<=20
    assert not args.gravity_close_before_takeover or (args.table_regrasp_plan and args.group!='A')
    assert args.gravity_close_support!='tray' or args.gravity_close_before_takeover
    assert abs(args.gravity_close_yaw)<=30
    assert not args.post_acquisition_pose or (args.group!='A' and args.table_supported_seat)
    assert not args.air_flip or (args.group!='A' and not args.table_supported_seat and not args.seat_at_operation)
    assert not args.air_flip_only or (args.air_flip and args.only_grasp and args.seat_seconds==0)
    assert 5<=args.air_flip_seconds<=20
    assert (.02<=args.lift_height<=.05 and args.pickup_only) if args.short_lift_diagnostic else .20<=args.lift_height<=.40
    assert np.linalg.norm(args.air_flip_shift)<=.25
    assert not args.gait_plan or (args.air_flip and not args.table_supported_seat and not args.seating_plan and args.seat_seconds==0)
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',1,
        ['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=True','rl_device=cpu'],train='wujiAcquisitionSAPG')
    (args.output/'frozen-config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    if knife_geometry is not None:
        assumed=knife_geometry.spec['physics_hypothesis']
        assert np.allclose(list(cfg.object.default_props.mass),[assumed['body_mass_kg'],assumed['button_mass_kg']],rtol=0,atol=1e-9)
        assert assumed['knife_friction']==3. and assumed['slider_damping']==.3 and assumed['slider_friction']==.001, 'This diagnostic retains baseline physics; do not silently ignore changed spec values'
    assert cfg.task.env.forceScale==0 and cfg.task.env.actionsMovingAverage==1 and not cfg.task.env.useRelativeControl
    k=G2Kinematics(); model=json.loads((ROOT/'assets/robots/g2_wuji/audit.json').read_text())
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[args.grasp]
    preset_candidate=None
    if args.preset_candidate:
        assert args.group=='A' and not args.grasp_plan and args.settle_seconds>=2
        preset_candidate=json.loads(args.preset_candidate.read_text());s=np.asarray(preset_candidate['state'],dtype=np.float32)
        assert s.shape==(70,) and np.isfinite(s).all()
        assert all(abs(np.linalg.norm(s[begin:begin+4])-1)<1e-5 for begin in [43,50])
        (args.output/'preset-candidate.json').write_text(json.dumps(preset_candidate,indent=2)+'\n')
    operation=transform([.40,-.30,1.05],(Rotation.from_euler('z',args.operation_yaw,degrees=True)*Rotation.from_euler('y',-90,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
    if args.operation_pose:operation=np.asarray(json.loads(args.operation_pose.read_text()),dtype=float)
    post_acquisition_pose=None
    if args.post_acquisition_pose:
        post_acquisition_pose=np.asarray(json.loads(args.post_acquisition_pose.read_text()),dtype=float)
        assert np.linalg.norm(post_acquisition_pose[:3,3]-operation[:3,3])<=.020
        assert Rotation.from_matrix(operation[:3,:3].T@post_acquisition_pose[:3,:3]).magnitude()<=np.deg2rad(15)+1e-8
    assert not args.operation_seed or args.group=='A'
    op_seed=np.asarray(json.loads(args.operation_seed.read_text())) if args.operation_seed else None
    op_q,op_error=k.solve(operation,op_seed)
    assert op_error['position_m']<1e-4 and op_error['rotation_rad']<1e-3,op_error
    table_z=args.table_height
    from scripts.g2_table_collision import ArmTableCollision
    arm_table_check=ArmTableCollision(table_z)
    table_obj=transform([.50+args.dx,-.30+args.dy,table_z+(.0071 if args.slider_face=='down' else .0041)],
        (Rotation.from_euler('z',args.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
    if args.slider_face=='down':table_obj=table_obj@transform(quaternion=Rotation.from_euler('z',180,degrees=True).as_quat())
    if knife_geometry is not None:table_obj=knife_geometry.table_pose(table_obj,table_z)
    grasp_pose=table_obj@transform(quaternion=Rotation.from_euler('z',args.grasp_roll,degrees=True).as_quat())@np.linalg.inv(transform(s[40:43],s[43:47]))
    grasp_pose[2,3]+=args.close_height
    custom_plan=None
    if args.grasp_plan:
        assert args.group!='A'
        custom_plan=json.loads(args.grasp_plan.read_text())
        assert bool(custom_plan.get('knife_spec'))==bool(args.knife_spec),'Grasp plan/knife geometry versions must agree'
        if args.knife_spec:
            assert json.loads((ROOT/custom_plan['knife_spec']).read_text())['file_sha256']==knife_geometry.spec['file_sha256']
        (args.output/'grasp-plan.json').write_text(json.dumps(custom_plan,indent=2)+'\n')
        grasp_pose=table_obj@np.asarray(custom_plan['wrist_in_knife'])
        grasp_pose[2,3]+=args.close_height
    above=grasp_pose.copy(); above[2,3]+=.16
    lifted=grasp_pose.copy(); lifted[2,3]+=args.lift_height
    high_seed=np.asarray(json.loads(args.acquisition_arm_seed.read_text())) if args.acquisition_arm_seed else op_q
    if preset_candidate is None and not args.table_settle_only:
        high_q,high_error=k.solve(above,high_seed)
        grasp_q,grasp_error=k.solve(grasp_pose,high_q)
        lift_q,lift_error=k.solve(lifted,grasp_q)
    else:
        high_q=grasp_q=lift_q=op_q
        high_error=grasp_error=lift_error=dict(not_applicable='Independent presetA has no table acquisition IK or trajectory')
    if args.wrist_posture is not None and preset_candidate is None:
        high_q,high_error=k.solve_wrist_posture(above,high_q,args.wrist_posture)
        grasp_q,grasp_error=k.solve_wrist_posture(grasp_pose,high_q,args.wrist_posture)
        lift_q,lift_error=k.solve_wrist_posture(lifted,grasp_q,args.wrist_posture)
    plan=dict(operation=op_error,approach=high_error,grasp=grasp_error,lift=lift_error,
              operation_q=op_q.tolist(),approach_q=high_q.tolist(),grasp_q=grasp_q.tolist(),lift_q=lift_q.tolist(),
              table_top=table_z,knife_pose=pose(table_obj).tolist(),planned_wrist_pose=pose(grasp_pose).tolist())
    (args.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    if preset_candidate is None and not args.table_settle_only:assert max(e['position_m'] for e in [high_error,grasp_error,lift_error])<.001
    geometry_input=None
    if knife_geometry is not None:
        geometry_input=np.concatenate([np.ptp(v,axis=0) for name,idx,v in knife_geometry.parts if idx==0])
        assert len(geometry_input)==6
    policy=FrozenPolicy(cfg,args.teacher,args.student if args.group=='C' else None,action_mode=args.policy_action_mode,geometry=geometry_input)
    gym=gymapi.acquire_gym(); sp=gymapi.SimParams()
    sp.dt=float(cfg.task.sim.dt);sp.substeps=int(cfg.task.sim.substeps);sp.up_axis=gymapi.UP_AXIS_Z
    sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False
    for name in ['solver_type','num_position_iterations','num_velocity_iterations','contact_offset','rest_offset',
                 'bounce_threshold_velocity','max_depenetration_velocity','default_buffer_size_multiplier','max_gpu_contact_pairs']:
        setattr(sp.physx,name,OmegaConf.to_container(cfg.task.sim.physx,resolve=True)[name])
    sp.physx.num_threads=2;sp.physx.use_gpu=True;sp.physx.contact_collection=gymapi.ContactCollection.CC_ALL_SUBSTEPS
    sim=gym.create_sim(0,0 if args.video else -1,gymapi.SIM_PHYSX,sp)
    assert sim is not None
    env=gym.create_env(sim,gymapi.Vec3(-2,-2,0),gymapi.Vec3(2,2,3),1)
    options=gymapi.AssetOptions();options.fix_base_link=True;options.collapse_fixed_joints=False
    options.disable_gravity=False;options.thickness=.001;options.angular_damping=.01
    options.use_physx_armature=True;options.default_dof_drive_mode=gymapi.DOF_MODE_POS
    asset='assets/hands/wuji_artbot/right.urdf' if args.hand_only_diagnostic else 'assets/robots/g2_wuji/g2_wuji.urdf'
    robot_asset=gym.load_asset(sim,str(ROOT),asset,options)
    root_pose=gymapi.Transform()
    if args.hand_only_diagnostic:
        root_pose.p=gymapi.Vec3(*operation[:3,3]);root_pose.r=gymapi.Quat(*Rotation.from_matrix(operation[:3,:3]).as_quat())
    robot=gym.create_actor(env,robot_asset,root_pose,'g2',0,0)
    names=gym.get_actor_dof_names(env,robot)
    hand_idx=np.array([names.index(n) for n in policy.fk.names]);arm_idx=np.array([names.index(n) for n in k.names if n in names],dtype=int)
    assert len(names)==(20 if args.hand_only_diagnostic else 27)
    props=gym.get_actor_dof_properties(env,robot)
    for key in ['stiffness','damping','armature','friction']:
        props[key][hand_idx]=np.asarray(cfg.hand.dof_props[key])
    for j,index in zip(model['active_arm'],arm_idx):
        props['stiffness'][index]=j['stiffness']*args.arm_gain_scale
        props['damping'][index]=j['damping']*args.arm_damping_scale
        props['armature'][index]=j['armature']
    props['driveMode'][:]=gymapi.DOF_MODE_POS;gym.set_actor_dof_properties(env,robot,props)
    rb_names=gym.get_actor_rigid_body_names(env,robot)
    rb_props=gym.get_actor_rigid_body_properties(env,robot)
    for name,p in zip(rb_names,rb_props):
        # Separate, explicit hand/arm conditions, established before any step.
        p.flags=(0 if args.hand_gravity else 1) if name.startswith('hand_r_') else (1 if args.arm_gravity=='off' else 0)
    gym.set_actor_rigid_body_properties(env,robot,rb_props)
    hand_gravity_model=None
    if args.hand_gravity_compensation:
        from scripts.g2_hand_gravity import HandGravity
        hand_gravity_model=HandGravity(props['stiffness'][hand_idx])
        assert policy.fk.names==hand_gravity_model.hand.names
        audit={}
        for name,prop in zip(rb_names,gym.get_actor_rigid_body_properties(env,robot)):
            if name not in hand_gravity_model.masses:continue
            mass,com=hand_gravity_model.masses[name]
            audit[name]=dict(mass_error_kg=abs(prop.mass-mass),com_error_m=float(np.max(np.abs(np.array([prop.com.x,prop.com.y,prop.com.z])-com))))
        assert max(max(item.values()) for item in audit.values())<1e-7
        (args.output/'hand-gravity-control.json').write_text(json.dumps(dict(
            scope='Model-based motor-target feedforward from first step; no object input or force API',
            mass_com_audit=audit,bias_cap_rad=.08,support_total_slew_rad=.02,thumb_total_slew_rad=.025,
            policy_reference='nominal motor target before gravity feedforward; actual command logged separately',
            gravity_enabled_before_first_step=True),indent=2)+'\n')
    shapes=gym.get_actor_rigid_shape_properties(env,robot)
    counts=gym.get_actor_rigid_body_shape_indices(env,robot)
    digits=['thumb','index','middle','ring','pinky']
    for name,shape in zip(rb_names,counts):
        mask=1<<7
        if name=='hand_r_base_link': mask|=sum(1<<(16+i) for i in range(5))
        elif name.startswith('hand_r_'):
            digit=next(i for i,f in enumerate(digits) if '_'+f+'_' in name)
            mask|=1<<(8+digit)
            if name.endswith(('link1','link2')): mask|=1<<(16+digit)
        for n in range(shape.start,shape.start+shape.count):
            # bit 7 must exclude arm/hand seams, but not cross-finger contact.
            shapes[n].filter=mask if not name.startswith('hand_r_') else mask & ~(1<<7)
            shapes[n].friction=1.
    # Exclude arm/hand seam contact using the hand digit bits only on the arm.
    all_digit_bits=sum(1<<(8+i) for i in range(5)) + sum(1<<(16+i) for i in range(5))
    for name,shape in zip(rb_names,counts):
        if not name.startswith('hand_r_'):
            for n in range(shape.start,shape.start+shape.count): shapes[n].filter|=all_digit_bits
    gym.set_actor_rigid_shape_properties(env,robot,shapes)
    options=gymapi.AssetOptions();options.fix_base_link=True
    table_asset=gym.create_box(sim,.60,.80,.05,options)
    t=gymapi.Transform();t.p=gymapi.Vec3(.60,-.25,table_z-.025)
    table=gym.create_actor(env,table_asset,t,'table',0,0)
    gym.set_rigid_body_color(env,table,0,gymapi.MESH_VISUAL,gymapi.Vec3(.40,.31,.23))
    floor=gymapi.PlaneParams();floor.normal=gymapi.Vec3(0,0,1);gym.add_ground(sim,floor)
    options=gymapi.AssetOptions();options.override_com=True;options.override_inertia=True
    options.fix_base_link=False;options.disable_gravity=False;options.thickness=.01;options.density=1000
    options.collapse_fixed_joints=False;options.default_dof_drive_mode=gymapi.DOF_MODE_POS
    obj_asset=gym.load_asset(sim,str(knife_asset_path.parent),knife_asset_path.name,options)
    initial_obj=operation@transform(s[40:43],s[43:47]) if args.group=='A' else table_obj
    initial_obj[:3,3]+=initial_obj[:3,:3]@np.array([0,0,args.preset_object_axis_offset])
    t=gymapi.Transform();t.p=gymapi.Vec3(*initial_obj[:3,3]);t.r=gymapi.Quat(*Rotation.from_matrix(initial_obj[:3,:3]).as_quat())
    knife=gym.create_actor(env,obj_asset,t,'knife',0,0)
    p=gym.get_actor_rigid_body_properties(env,knife)
    for idx,mass in enumerate(cfg.object.default_props.mass): p[idx].mass=mass
    gym.set_actor_rigid_body_properties(env,knife,p)
    p=gym.get_actor_rigid_shape_properties(env,knife)
    for shape in p:shape.friction=3.;shape.filter=1
    gym.set_actor_rigid_shape_properties(env,knife,p)
    p=gym.get_actor_dof_properties(env,knife)
    p['driveMode'][:]=gymapi.DOF_MODE_POS;p['stiffness'][:]=0.;p['damping'][:]=.3;p['friction'][:]=.001;p['armature'][:]=.001
    gym.set_actor_dof_properties(env,knife,p)
    slider_lower=float(p['lower'][0])
    assert 0<=args.preset_slider_offset<=float(p['upper'][0])-slider_lower+1e-6
    effective=dict(robot_dof_names=names,hand_indices=hand_idx.tolist(),arm_indices=arm_idx.tolist(),
        hand_asset_sha256=hashlib.sha256((ROOT/'assets/hands/wuji_artbot/right.urdf').read_bytes()).hexdigest(),
        knife_asset_sha256=hashlib.sha256(knife_asset_path.read_bytes()).hexdigest(),
        knife_asset_path=str(knife_asset_path),knife_asset_spec=knife_geometry.spec if knife_geometry is not None else None,
        knife_body_names=gym.get_asset_rigid_body_names(obj_asset),
        knife_loaded_shape_count=gym.get_asset_rigid_shape_count(obj_asset),
        knife_loaded_shapes=[{name:(int(getattr(v,name)) if name=='filter' else float(getattr(v,name)))
            for name in ['friction','rolling_friction','torsion_friction','restitution','contact_offset','rest_offset','filter'] if hasattr(v,name)}
            for v in gym.get_actor_rigid_shape_properties(env,knife)],
        robot_dof_properties={n:props[n].tolist() for n in props.dtype.names},
        knife_dof_properties={n:p[n].tolist() for n in p.dtype.names},
        robot_body_names=rb_names,robot_gravity_flags=[int(v.flags) for v in gym.get_actor_rigid_body_properties(env,robot)],
        collision_filters=[int(v.filter) for v in gym.get_actor_rigid_shape_properties(env,robot)],
        knife_mass=[float(v.mass) for v in gym.get_actor_rigid_body_properties(env,knife)],
        table_friction=[float(v.friction) for v in gym.get_actor_rigid_shape_properties(env,table)],
        source_self_collision='G2 non-hand self-contact disabled per asset; existing Wuji digit filtering retained')
    effective['knife_effective_inertial']=[dict(mass=float(v.mass),com=[float(getattr(v.com,n)) for n in ['x','y','z']],
        inertia=[[float(getattr(getattr(v.inertia,row),col)) for col in ['x','y','z']] for row in ['x','y','z']]) for v in gym.get_actor_rigid_body_properties(env,knife)]
    (args.output/'physics.json').write_text(json.dumps(effective,indent=2)+'\n')
    if knife_geometry is not None:
        (args.output/'effective-configuration.json').write_text(json.dumps(dict(
            base_configuration='frozen-config.yaml records inherited controller settings; it is not the effective knife geometry',
            geometry_override='knife-asset-spec.json',effective_simulator_properties='physics.json',
            knife_asset_urdf=str(knife_asset_path),knife_file_sha256=knife_geometry.spec['file_sha256'],
            cli={key:str(value) if isinstance(value,Path) else value for key,value in vars(args).items()},
            geometry_observation=policy.geometry.tolist(),weights_frozen=True,policy_execution='See report.operation_steps; geometry interface corrected without retraining',scope='Independent presetA or continuous acquisition diagnostic'),indent=2)+'\n')
    closed=s[20:40].copy();opened=closed.copy()
    if preset_candidate is not None:
        assert np.all(s[:20]>=policy.fk.lower-1e-6) and np.all(s[:20]<=policy.fk.upper+1e-6)
        assert np.all(closed>=policy.fk.lower-1e-6) and np.all(closed<=policy.fk.upper+1e-6)
    for i,n in enumerate(policy.fk.names):
        if n.endswith(('joint1','joint3','joint4')): opened[i]*=.15
    if args.pregrasp=='support-curled':
        opened=closed.copy()
        opened[16]=.65
        opened[18]=.35
    functional=closed.copy()
    if custom_plan:
        opened=np.asarray(custom_plan['open_q']);closed=np.asarray(custom_plan['close_q'])
    table_regrasp=None
    if args.table_regrasp_plan:
        table_regrasp=json.loads(args.table_regrasp_plan.read_text())
        assert table_regrasp['grasp']==args.grasp and table_regrasp['min_table_clearance_m']>.0005
        assert table_regrasp.get('end','positive')==args.upright_end
        assert max(table_regrasp['open_contact_error_m'])<.001
        functional=np.asarray(table_regrasp['close_q'])
        assert np.all(functional>=policy.fk.lower-1e-6) and np.all(functional<=policy.fk.upper+1e-6)
        (args.output/'table-regrasp-plan.json').write_text(json.dumps(table_regrasp,indent=2)+'\n')
    opened=np.clip(opened,policy.fk.lower,policy.fk.upper)
    initial_hand=s[:20] if args.group=='A' else opened
    arm=op_q if args.group=='A' else high_q
    states=np.zeros(len(names),dtype=gymapi.DofState.dtype)
    states['pos'][hand_idx]=initial_hand;states['pos'][arm_idx]=arm[:len(arm_idx)]
    obj_states=np.zeros(1,dtype=gymapi.DofState.dtype);obj_states['pos'][0]=slider_lower+args.preset_slider_offset
    if preset_candidate is not None:
        assert args.preset_slider_offset==0 and args.preset_object_axis_offset==0
        assert slider_lower-1e-7<=s[54]<=float(p['upper'][0])+1e-7
        obj_states['pos'][0]=s[54]
    targets=np.zeros(len(names)+1,dtype=np.float32);targets[hand_idx]=closed if args.group=='A' else opened
    targets[arm_idx]=arm[:len(arm_idx)];targets[-1]=slider_lower
    writer=None;cam=None;close_writer=None;close_cam=None
    if args.video:
        import imageio.v2 as imageio
        cp=gymapi.CameraProperties();cp.width=960;cp.height=720;cp.horizontal_fov=65;cp.use_collision_geometry=False
        cam=gym.create_camera_sensor(env,cp)
        camera_pos=[1.5,-1.6,1.65] if args.camera=='wide' else [.95,-.85,1.45]
        camera_target=[.35,-.25,1.0] if args.camera=='wide' else [.4,-.3,1.0]
        gym.set_camera_location(cam,env,gymapi.Vec3(*camera_pos),gymapi.Vec3(*camera_target))
        writer=imageio.get_writer(str(args.output/'continuous.mp4'),fps=30,macro_block_size=8)
        if args.closeup:
            close_cp=gymapi.CameraProperties();close_cp.width=960;close_cp.height=720;close_cp.horizontal_fov=45
            close_cam=gym.create_camera_sensor(env,close_cp)
            close_writer=imageio.get_writer(str(args.output/'hand-closeup.mp4'),fps=30,macro_block_size=8)
    digit_geometry=None
    if args.contact_diagnostics:
        from scripts.g2_contact_geometry import DigitGeometry
        digit_geometry=DigitGeometry(knife_spec=args.knife_spec)
        shape_fields={}
        for label,actor in [('robot',robot),('knife',knife)]:
            shape_fields[label]=[{k:float(getattr(v,k)) for k in ['contact_offset','rest_offset','friction','thickness'] if hasattr(v,k)} for v in gym.get_actor_rigid_shape_properties(env,actor)]
        (args.output/'contact-model.json').write_text(json.dumps(dict(sim_contact_offset=float(sp.physx.contact_offset),sim_rest_offset=float(sp.physx.rest_offset),shapes=shape_fields,
            gap_definition='Whole-digit link1-4 plus pad collision convex face-axis separation from both knife links; positive lower bound. Release uses contact absence AND clearance beyond configured pair contact offsets.'),indent=2)+'\n')
    gym.prepare_sim(sim)
    # This runtime prepares an articulation when the scene is finalized.
    # Enable sensing after that point, before acquiring the force tensor.
    force_sensor_enabled=bool(gym.enable_actor_dof_force_sensors(env,robot))
    # Isaac Gym prepares internal articulation state during prepare_sim.
    # Set the single episode initialization afterward, before simulate is ever
    # called by this runner. B/C initialize OPEN fingers and a tabletop knife.
    gym.set_actor_dof_states(env,robot,states,gymapi.STATE_ALL)
    gym.set_actor_dof_states(env,knife,obj_states,gymapi.STATE_ALL)
    gym.set_actor_dof_position_targets(env,robot,targets[:-1].copy())
    gym.set_actor_dof_position_targets(env,knife,targets[-1:].copy())
    roots=gymtorch.wrap_tensor(gym.acquire_actor_root_state_tensor(sim))
    gym.refresh_actor_root_state_tensor(sim)
    object_actor_id=gym.get_actor_index(env,knife,gymapi.DOMAIN_SIM)
    roots[object_actor_id,:7]=torch.as_tensor(pose(initial_obj),dtype=torch.float32)
    roots[object_actor_id,7:]=0
    ids=torch.tensor([object_actor_id],dtype=torch.int32)
    gym.set_actor_root_state_tensor_indexed(sim,gymtorch.unwrap_tensor(roots),gymtorch.unwrap_tensor(ids),1)
    dof=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim))
    rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim))
    contact=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim))
    efforts=gymtorch.wrap_tensor(gym.acquire_dof_force_tensor(sim)) if force_sensor_enabled else None
    print(json.dumps(dict(force_sensor_enabled=force_sensor_enabled)),flush=True)
    def body(actor,name): return gym.find_actor_rigid_body_index(env,actor,name,gymapi.DOMAIN_SIM)
    wrist_id=body(robot,'hand_r_base_link');obj_id=body(knife,'link_0');slider_id=body(knife,'link_1')
    table_id=gym.get_actor_rigid_body_index(env,table,0,gymapi.DOMAIN_SIM)
    hand_bodies=[body(robot,n) for n in rb_names if n.startswith('hand_r_')]
    env_names={gym.get_actor_rigid_body_index(env,a,i,gymapi.DOMAIN_ENV):n
               for a in [robot,table,knife] for i,n in enumerate(gym.get_actor_rigid_body_names(env,a))}
    table_env=gym.get_actor_rigid_body_index(env,table,0,gymapi.DOMAIN_ENV)
    knife_env={gym.get_actor_rigid_body_index(env,knife,i,gymapi.DOMAIN_ENV) for i in range(2)}
    def refresh():
        gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim)
        if efforts is not None:gym.refresh_dof_force_tensor(sim)
    def current():
        a=dof.detach().cpu().numpy();b=rb.detach().cpu().numpy()
        return a[hand_idx,0].copy(),a[arm_idx,0].copy(),float(a[-1,0]),transform(b[wrist_id,:3],b[wrist_id,3:7]),transform(b[obj_id,:3],b[obj_id,3:7]),transform(b[slider_id,:3],b[slider_id,3:7])
    records=[];takeover=None;dt=float(sp.dt)*4;global_step=0
    learned_runtime=None
    geometric_runtime=None
    pair_records=[]
    arm_integral=np.zeros(len(arm_idx))
    previous_hand_command=targets[hand_idx].copy()
    def tick(phase,action=None,goal=0.,obs=None):
        nonlocal global_step
        reference_targets=targets.copy();command_targets=targets.copy()
        if args.arm_integral_gain:
            measured=dof[arm_idx,0].cpu().numpy()
            arm_integral[:]=np.clip(arm_integral+args.arm_integral_gain*dt*(targets[arm_idx]-measured),-.08,.08)
            command_targets[arm_idx]=np.clip(targets[arm_idx]+arm_integral,k.lower,k.upper)
        if hand_gravity_model is not None:
            gravity_input_q=np.concatenate([dof[arm_idx,0].cpu().numpy(),dof[hand_idx,0].cpu().numpy()])
            gravity_bias,gravity_torque=hand_gravity_model.bias(gravity_input_q)
            desired=targets[hand_idx]+gravity_bias.astype(np.float32)
            slew=np.asarray([.02]*16+[.025]*4,dtype=np.float32)
            desired=previous_hand_command+np.clip(desired-previous_hand_command,-slew,slew)
            command_targets[hand_idx]=np.clip(desired,props['lower'][hand_idx],props['upper'][hand_idx])
            previous_hand_command[:]=command_targets[hand_idx]
        gym.set_dof_position_target_tensor(sim,gymtorch.unwrap_tensor(torch.from_numpy(command_targets)))
        for _ in range(4):gym.simulate(sim);gym.fetch_results(sim,True)
        refresh();q,qa,sl,w,o,l=current()
        executed=np.zeros(20,dtype=np.float32) if action is None else action
        policy.record(q,executed)
        finger_table=np.zeros(5,dtype=np.int32);finger_knife=np.zeros(5,dtype=np.int32);finger_slider=np.zeros(5,dtype=np.int32)
        knife_table_count=0;robot_table_count=0;robot_table_links=set()
        for c in gym.get_env_rigid_contacts(env):
            if c['lambda']<=1e-6:continue
            pair={int(c['body0']),int(c['body1'])}
            if table_env in pair:
                if pair & knife_env:knife_table_count+=1
                elif any(env_names.get(b,'') in rb_names for b in pair):
                    robot_table_count+=1
                    robot_table_links.update(env_names[b] for b in pair if env_names.get(b,'') in rb_names)
            if pair & knife_env:
                v=c['normal']
                normal=[float(v[name]) for name in ('x','y','z')] if getattr(v.dtype,'names',None) else [float(x) for x in v]
                pair_records.append(dict(step=global_step,phase=phase,body0=env_names.get(int(c['body0']),'ground'),
                    body1=env_names.get(int(c['body1']),'ground'),normal=normal,lambda_value=float(c['lambda'])))
                if args.gait_plan or preset_candidate is not None or args.contact_diagnostics:
                    if not (args.output/'contact-schema.json').exists():
                        (args.output/'contact-schema.json').write_text(json.dumps(list(c.dtype.names))+'\n')
                    for key in ['local_pos0','local_pos1','localPos0','localPos1']:
                        if key in c.dtype.names:
                            point=c[key]
                            pair_records[-1][key]=[float(point[n]) for n in ('x','y','z')] if getattr(point.dtype,'names',None) else [float(x) for x in point]
            for i,f in enumerate(digits):
                digit_contact=any('_'+f+'_' in env_names.get(b,'') for b in pair)
                if digit_contact and table_env in pair:finger_table[i]+=1
                if digit_contact and pair & knife_env:finger_knife[i]+=1
                if digit_contact and any(env_names.get(b)=='link_1' for b in pair):finger_slider[i]+=1
        records.append(dict(time=(global_step+1)*dt,phase=phase,q=q,arm_q=qa,targets=command_targets,reference_targets=reference_targets,action=executed.copy(),
            geometric_feedback=np.zeros(3,dtype=np.float32),raw_policy_action=policy.last_raw_action.copy() if action is not None else np.zeros(20,dtype=np.float32),
            all_dof_position=dof[:,0].cpu().numpy().copy(),object_rigid_state=rb[obj_id].cpu().numpy().copy(),
            slider_rigid_state=rb[slider_id].cpu().numpy().copy(),arm_integral_state=arm_integral.copy(),
            dof_velocity=dof[:,1].cpu().numpy().copy(),dof_effort=efforts.cpu().numpy().copy() if efforts is not None else np.full(len(names)+1,np.nan),
            finger_table_contacts=finger_table,finger_knife_contacts=finger_knife,finger_slider_contacts=finger_slider,
            knife_table_contacts=knife_table_count,robot_table_contacts=robot_table_count,
            slider=sl,goal=goal,wrist=pose(w),object=pose(o),slider_pose=pose(l),
            table_force=contact[table_id].cpu().numpy().copy(),hand_force=contact[hand_bodies].cpu().numpy().copy(),
            observation=np.zeros(138,dtype=np.float32) if obs is None else obs))
        # Separate channels: the frozen actor output and the new learner output
        # are both actual values, not substituted cached history.
        learned_action=np.zeros(20,dtype=np.float32);learned_residual=learned_action.copy()
        learned_observation=np.zeros(124,dtype=np.float32)
        if learned_runtime is not None:
            size=learned_runtime.action_dim
            learned_action[:size]=learned_runtime.last_action[0].numpy()
            learned_residual[:size]=learned_runtime.residual[0].numpy()
            ob=learned_runtime.last_observation[0].numpy();learned_observation[:len(ob)]=ob
        records[-1].update(learned_action=learned_action,learned_residual=learned_residual,learned_observation=learned_observation)
        if hand_gravity_model is not None:
            records[-1].update(hand_gravity_input_q=gravity_input_q.copy(),hand_gravity_model_torque=gravity_torque.copy(),
                hand_gravity_applied_motor_bias=(command_targets[hand_idx]-reference_targets[hand_idx]).copy())
        if digit_geometry is not None:
            records[-1]['thumb_gap_lower_bound_m']=digit_geometry.minimum_gap(q,np.linalg.inv(o)@w,sl)
        if writer:
            if close_cam is not None:
                camera_target=w[:3,3]+w[:3,:3]@np.array([.035,0,.115])
                camera_position=camera_target+np.array([.16,-.22,.15])
                gym.set_camera_location(close_cam,env,gymapi.Vec3(*camera_position),gymapi.Vec3(*camera_target))
            gym.step_graphics(sim);gym.render_all_camera_sensors(sim)
            frame=gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR)
            writer.append_data(np.asarray(frame).reshape(720,960,4)[:,:,:3])
            if close_writer:
                frame=gym.get_camera_image(sim,env,close_cam,gymapi.IMAGE_COLOR)
                close_writer.append_data(np.asarray(frame).reshape(720,960,4)[:,:,:3])
        global_step+=1
        arm_or_palm_table=[name for name in robot_table_links if not any('_'+digit+'_' in name for digit in digits)]
        if arm_or_palm_table:
            raise ValueError('Actual G2 arm/palm table contact: '+str(sorted(arm_or_palm_table)))
        if global_step%150==0:print(json.dumps(dict(step=global_step,phase=phase,slider=sl,object=pose(o)[:3].tolist(),
            arm_error_max_rad=float(np.max(np.abs(qa-targets[arm_idx]))) if len(qa) else 0.,
            finger_table_contacts=finger_table.tolist(),finger_knife_contacts=finger_knife.tolist())),flush=True)
        return q,qa,sl,w,o,l
    try:
        refresh()
        if preset_candidate is not None:
            for _ in range(round(args.settle_seconds/dt)):tick('settle_history')
        if args.preset_preparation:
            assert args.group=='A' and preset_candidate is not None and args.contact_diagnostics
            plan_pre=json.loads(args.preset_preparation.read_text())
            (args.output/'preset-preparation.json').write_text(json.dumps(plan_pre,indent=2)+'\n')
            checks=[]
            for stage in plan_pre['stages']:
                start=targets[hand_idx].copy();end=start.copy()
                if not stage.get('hold'):
                    ids=stage['indices'];assert len(ids)<=4, 'Only one digit per stage'
                    end[ids]=stage['target']
                    assert np.all(end>=policy.fk.lower) and np.all(end<=policy.fk.upper)
                _,_,_,ref_w,ref_o,_=current();ref_rel=np.linalg.inv(ref_w)@ref_o;first=len(records)
                for frame in range(round(stage['seconds']/dt)):
                    a=smooth((frame+1)/round(stage['seconds']/dt));targets[hand_idx]=start+(end-start)*a
                    tick('preset_'+stage['name'])
                rows=records[first:];objects=np.asarray([r['object'] for r in rows]);rels=np.array([np.linalg.inv(transform(r['wrist'][:3],r['wrist'][3:]))@transform(r['object'][:3],r['object'][3:]) for r in rows])
                wd=float(np.linalg.norm(objects[:,:3]-ref_o[:3,3],axis=1).max());wr=float(Rotation.from_matrix(ref_o[:3,:3].T@Rotation.from_quat(objects[:,3:]).as_matrix()).magnitude().max())
                hd=float(np.linalg.norm(rels[:,:3,3]-ref_rel[:3,3],axis=1).max());hr=float(Rotation.from_matrix(ref_rel[:3,:3].T@rels[:,:3,:3]).magnitude().max())
                c=np.asarray([r['finger_knife_contacts'] for r in rows]);clear=bool((c[:,0]==0).all() and min(r['thumb_gap_lower_bound_m'] for r in rows)>.001)
                stable=wd<.01 and wr<.25 and hd<.01 and hr<.25 and all(r['knife_table_contacts']==0 for r in rows) and objects[:,2].min()>table_z+.1
                check=dict(name=stage['name'],hold=stage.get('hold',False),world_drift_m=wd,world_rotation_rad=wr,hand_drift_m=hd,hand_rotation_rad=hr,stable=bool(stable),thumb_clear=clear,contacts_fraction=(c>0).mean(0).tolist(),first_step=first,last_step=len(records),slider_passive_delta_m=rows[-1]['slider']-rows[0]['slider'])
                checks.append(check);(args.output/'preset-preparation-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
                if stage.get('hold') and (not stable or (stage.get('require_clear') and not clear)):raise ValueError('Preset preparation hold failed: '+stage['name'])
            for _ in range(round(args.settle_seconds/dt)):tick('settle_history')
        if args.group!='A':
            for _ in range(60):tick('table_settle')
            if args.table_settle_only:
                _,_,sl,_,o,_=current()
                (args.output/'settled-table-localization.json').write_text(json.dumps(dict(object=pose(o).tolist(),slider_position_m=sl,grasp_q=grasp_q.tolist(),method='Measured after natural2s free settle; only initial physical setup, no manipulation yet'),indent=2)+'\n')
                np.savez_compressed(args.output/'trace.npz',**{key:np.asarray([r[key] for r in records]) for key in records[0]})
                (args.output/'report.json').write_text(json.dumps(dict(scope='Natural-table-settle-only, not acquisition or operation',physics_steps=global_step,knife_asset_sha256=effective['knife_asset_sha256'])))
                return
            if args.table_localization=='settled-truth':
                assert custom_plan is not None
                _,_,actual_table_slider,_,actual_table_object,_=current()
                measured_grasp=actual_table_object@np.asarray(custom_plan['wrist_in_knife'])
                measured_grasp[2,3]+=args.close_height
                measured_lift=measured_grasp.copy();measured_lift[2,3]+=args.lift_height
                grasp_q,grasp_error=k.solve_near(measured_grasp,grasp_q,max_step=.4)
                lift_q,lift_error=k.solve_near(measured_lift,lift_q,max_step=.4)
                if max(grasp_error['position_m'],lift_error['position_m'])>.001 or max(grasp_error['rotation_rad'],lift_error['rotation_rad'])>.005:
                    raise ValueError('Settled-table localization IK failed')
                (args.output/'settled-table-localization.json').write_text(json.dumps(dict(
                    object=pose(actual_table_object).tolist(),grasp_q=grasp_q.tolist(),lift_q=lift_q.tolist(),
                    slider_position_m=float(actual_table_slider),
                    grasp_ik=grasp_error,lift_ik=lift_error,method='One simulated truth sample after natural tabletop settling; only arm motor targets replanned.'),indent=2)+'\n')
                if knife_geometry is not None:
                    # Bump-down resting may tilt differently from the old
                    # asset used for offline planning. Recheck finger/table
                    # geometry using the actual settled pose before approach.
                    from scripts.g2_contact_geometry import DigitGeometry
                    check_geometry=DigitGeometry(max_face_axes=24)
                    waypoints=custom_plan.get('close_waypoints',[dict(q=opened.tolist()),dict(q=closed.tolist())])
                    table_rows=[]
                    for segment,(start,end) in enumerate(zip(waypoints[:-1],waypoints[1:])):
                        for u in np.linspace(0,1,21):
                            qcheck=np.asarray(start['q'])*(1-u)+np.asarray(end['q'])*u
                            frames=check_geometry.w.forward(qcheck)
                            minimum=float('inf');minimum_link=None
                            for name,meshes in check_geometry.meshes.items():
                                frame=measured_grasp@frames[name]
                                height=min(float((v@frame[2,:3]+frame[2,3]-table_z).min()) for v,_ in meshes)
                                if height<minimum:minimum=height;minimum_link=name
                            table_rows.append(dict(segment=segment,fraction=float(u),table_clearance_m=minimum,hand_link=minimum_link))
                    table_audit=dict(scope='Nominal hand motor path recheck at actual naturally settled newknife pose, before approach; not actual servo tracking',
                        threshold_m=.0005,rows=table_rows,passed=all(r['table_clearance_m']>=.0005 for r in table_rows))
                    (args.output/'settled-hand-table-path-check.json').write_text(json.dumps(table_audit,indent=2)+'\n')
                    if not table_audit['passed']:raise ValueError('New knife settled pose invalidates hand/table path clearance; stop before approach')
            phases=[('approach',grasp_q,opened,4),('close',grasp_q,closed,3)]
            if args.closed_settle_seconds:phases.append(('closed_settle',None,None,args.closed_settle_seconds))
            phases.append(('lift',lift_q,closed,4))
            if args.pickup_retention_hold:phases.append(('pickup_hold',None,closed,args.pickup_retention_hold))
            if args.air_flip:phases.append(('air_flip',None,closed,args.air_flip_seconds))
            if args.gait_plan:phases.append(('finger_gait',None,None,0))
            if args.table_supported_seat:
                if args.upright_path=='yaw-then-tip':phases.append(('stand_yaw',None,closed,5))
                if args.upright_path=='tip-then-yaw':phases.append(('stand_tip',None,closed,5))
                phases.extend([('stand_orient',None,closed,args.upright_orient_seconds),('stand_lower',None,closed,4),('support_settle',None,closed,2)])
            if args.seat_at_operation:phases.append(('preorient',None,closed,5))
            if table_regrasp:
                functional_open=np.asarray(table_regrasp['open_q'])
                if args.level_standing_knife:phases.append(('stand_level',None,closed,4))
                if args.measured_release:phases.append(('unload_pinch',None,None,1))
                phases.extend([('release_pinch',None,opened,3 if args.measured_release else 2),('withdraw',None,opened,4),
                    ('free_reorient',None,functional_open,5),('functional_approach',None,functional_open,4)])
                if 'touch_q' in table_regrasp:phases.append(('functional_touch',None,np.asarray(table_regrasp['touch_q']),3))
                phases.append(('functional_close',None,functional,3))
            elif args.seat_seconds>0:phases.append(('seat',lift_q,functional,args.seat_seconds))
            if args.table_supported_seat:phases.append(('relift',None,functional,4))
            if not args.air_flip_only and not args.stay_after_gait and not args.pickup_only:phases.append(('transport',op_q,functional if args.seat_seconds>0 or table_regrasp else closed,5))
            if args.gravity_close_before_takeover:
                restored=np.asarray(table_regrasp.get('restore_q',functional))
                gravity_hold_hand=functional.copy()
                phases.append(('gravity_close_orient',None,functional,8))
                if args.gravity_close_support=='tray':
                    gravity_hold_hand[16:20]=functional_open[16:20]
                    phases.append(('gravity_close_unload',None,gravity_hold_hand,2))
                phases.extend([('gravity_close_hold',None,gravity_hold_hand,3),
                               ('gravity_close_restore',None,restored,2),('gravity_close_return',None,restored,8)])
            if post_acquisition_pose is not None:phases.append(('operation_adjust',None,None,4))
            pickup_feedback=None
            for label,end_arm,end_hand,seconds in phases:
                if label=='closed_settle':
                    for _ in range(round(seconds/dt)):tick(label)
                    continue
                if label=='pickup_hold':
                    from scripts.g2_tabletop_metrics import fixed_acquisition_hold
                    _,_,_,hold_w,hold_o,_=current();first=len(records)
                    for _ in range(round(seconds/dt)):
                        if pickup_feedback is not None:
                            _,_,_,fw,fo,_=current();targets[hand_idx]=pickup_feedback.command(fw,fo,global_step*dt)
                        tick(label)
                    if pickup_feedback is not None:(args.output/'pickup-finger-feedback.json').write_text(json.dumps(pickup_feedback.report(),indent=2)+'\n')
                    check=fixed_acquisition_hold(records[first:],hold_o,hold_w,table_z)
                    if args.short_lift_diagnostic:
                        corners=knife_geometry.collision_parts(slider_lower)[0]['vertices']
                        clearances=[]
                        for row in records[first:]:
                            ot=transform(row['object'][:3],row['object'][3:]);clearances.append(float((corners@ot[2,:3]+ot[2,3]-table_z).min()))
                        check['full_lift_retained']=check['retained']
                        check['retained']=bool(check['stable'] and check['table_free'] and min(clearances)>.002 and check['opposed_contact_fraction']>=.9)
                        check.update(scope='Short2-5cm lift diagnostic ONLY, not full acquisition',minimum_body_table_clearance_m=min(clearances),short_lift_retained=check['retained'])
                    (args.output/'pickup-hold-check.json').write_text(json.dumps(check,indent=2)+'\n')
                    if not check['retained']:raise ValueError('Pickup failed fixed-reference hold before flip')
                    continue
                if args.cartesian_acquisition and label=='close':end_arm=targets[arm_idx].copy()
                if args.cartesian_acquisition and label in ['approach','lift']:
                    from scripts.g2_cartesian_acquisition import plan_translation
                    arm_path,diagnostic=plan_translation(k,targets[arm_idx],k.forward(end_arm),seconds,dt,arm_table_check)
                    (args.output/(label+'-cartesian-plan.json')).write_text(json.dumps(diagnostic,indent=2)+'\n')
                    start_hand=targets[hand_idx].copy()
                    if label=='lift' and args.pickup_finger_feedback:
                        from scripts.g2_side_pinch_feedback import SidePinchFeedback
                        _,_,_,fw,fo,_=current();pickup_feedback=SidePinchFeedback(targets[hand_idx],fw,fo,table_z)
                    for i,motor in enumerate(arm_path):
                        alpha=smooth((i+1)/len(arm_path));targets[arm_idx]=motor
                        targets[hand_idx]=start_hand+(end_hand-start_hand)*alpha
                        if pickup_feedback is not None:
                            _,_,_,fw,fo,_=current();targets[hand_idx]=pickup_feedback.command(fw,fo,global_step*dt)
                        tick(label)
                    if pickup_feedback is not None:(args.output/'pickup-finger-feedback.json').write_text(json.dumps(pickup_feedback.report(),indent=2)+'\n')
                    continue
                if label=='finger_gait':
                    from scripts.g2_finger_gait import execute_gait
                    execute_gait(args.gait_plan,args.output,targets,hand_idx,arm_idx,current,tick,records,dt,k,policy.fk,table_z,retarget_reference=args.gait_arm_retarget_reference,translate_before_alignment=args.gait_translation_before_alignment,pinky_retarget=args.gait_pinky_retarget)
                    if args.post_gait_roll:
                        from scripts.g2_assembly_roll import execute_roll
                        reference=execute_roll(k,targets,arm_idx,current,tick,records,dt,arm_table_check,args.output,args.post_gait_roll,args.assembly_roll_seconds)
                        if args.roll_tracking_correction:
                            from scripts.g2_assembly_roll import align_to_fixed_goal
                            align_to_fixed_goal(k,targets,arm_idx,current,tick,records,dt,arm_table_check,args.output,reference)
                        if args.post_roll_gait_plan:
                            folder=args.output/'post-roll-gait';folder.mkdir()
                            execute_gait(args.post_roll_gait_plan,folder,targets,hand_idx,arm_idx,current,tick,records,dt,k,policy.fk,table_z,world_reference=reference)
                    continue
                if label=='air_flip':
                    from scripts.g2_air_flip import plan_flip, check_flip
                    _,_,_,actual_w,actual_o,_=current()
                    path,diagnostic=plan_flip(k,actual_w,actual_o,targets[arm_idx],args.air_flip,seconds,dt,arm_table_check,args.air_flip_shift,axis_mode=args.air_flip_axis)
                    (args.output/'air-flip-plan.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
                    if not diagnostic['feasible']:raise ValueError('Air-flip IK/clearance precheck failed: '+str(diagnostic['failure']))
                    first=len(records)
                    for motor in path:
                        targets[arm_idx]=motor;targets[hand_idx]=end_hand
                        tick(label)
                    audit=check_flip(records[first:],actual_w,actual_o,table_z)
                    (args.output/'air-flip-check.json').write_text(json.dumps(audit,indent=2)+'\n')
                    if not audit['retained']:raise ValueError('Knife not retained throughout free-space flip')
                    continue
                if label=='stand_level':
                    _,_,_,initial_w,initial_o,_=current();level_goal=initial_o.copy()
                    # Correct only tilt: loaded pinching may change yaw around
                    # the knife axis, which is irrelevant to standing stability.
                    vertical=np.array([0,0,-1 if args.upright_end=='positive' else 1])
                    tilt_correction=minimal_alignment(initial_o[:3,2],vertical)
                    level_goal[:3,:3]=tilt_correction@initial_o[:3,:3];level_goal[2,3]=table_z+.0735-.0002
                    corrections=[]
                    for iteration in range(4):
                        _,_,_,w,o,_=current();desired=level_goal@np.linalg.inv(o)@w
                        if np.linalg.norm(desired[:3,3]-initial_w[:3,3])>.025:raise ValueError('Standing leveling exceeds 25mm wrist correction bound')
                        end,error=k.solve_near(desired,targets[arm_idx])
                        if error['position_m']>.001 or error['rotation_rad']>.005:raise ValueError('Standing leveling IK failed: '+str(error))
                        begin=targets[arm_idx].copy()
                        for i in range(30):
                            targets[arm_idx]=begin+(end-begin)*smooth((i+1)/30);tick(label)
                        _,_,_,_,actual_o,_=current()
                        corrections.append(dict(iteration=iteration,object=pose(actual_o).tolist(),ik=error))
                        (args.output/'standing-level-corrections.json').write_text(json.dumps(corrections,indent=2)+'\n')
                    tilt=float(np.arccos(np.clip(actual_o[2,2]*(-1 if args.upright_end=='positive' else 1),-1,1)))
                    if args.standing_level_gate=='tilt':
                        if tilt>.02:raise ValueError('Standing knife still tilted more than 0.02rad after leveling')
                    else:
                        _,_,_,_,actual_o,actual_slider=current()
                        slider_local=np.linalg.inv(actual_o)@actual_slider
                        mass=np.asarray(cfg.object.default_props.mass,dtype=float)
                        com=slider_local[:3,3]*mass[1]/mass.sum()
                        gravity=actual_o[:3,:3].T@np.array([0.,0.,-1.])
                        end_z=.0735 if args.upright_end=='positive' else -.0735
                        parameter=(end_z-com[2])/gravity[2]
                        footprint=com[:2]+parameter*gravity[:2]
                        margins=np.array([.0095,.004])-np.abs(footprint)
                        contact_fraction=float(np.mean([r['knife_table_contacts']>0 for r in records[-30:]]))
                        release_gate=dict(tilt_rad=tilt,com_local_m=com.tolist(),end_projection_m=footprint.tolist(),
                            footprint_margin_m=margins.tolist(),required_margin_m=.0005,table_contact_fraction=contact_fraction,
                            interpretation='Geometric candidate for physically tested release; not a guarantee of dynamic standing stability.')
                        (args.output/'standing-release-gate.json').write_text(json.dumps(release_gate,indent=2)+'\n')
                        if parameter<0 or tilt>.15 or margins.min()<.0005 or contact_fraction<.8:
                            raise ValueError('Standing knife fails assembly COM support projection release precheck')
                    continue
                if args.table_supported_seat and label in ['stand_tip','stand_yaw','stand_orient','stand_lower','support_settle','release_pinch','withdraw',
                    'unload_pinch','free_reorient','functional_approach','functional_touch','functional_close','relift','transport',
                    'gravity_close_orient','gravity_close_unload','gravity_close_hold','gravity_close_restore','gravity_close_return','operation_adjust']:
                    start=k.forward(targets[arm_idx]);start_hand=targets[hand_idx].copy()
                    if label=='operation_adjust':end_hand=start_hand.copy()
                    if label=='unload_pinch':end_hand=current()[0].copy()
                    if label=='release_pinch' and args.measured_release:
                        from scripts.g2_seating_feedback import ContactCorrection
                        hand,_,_,w,o,_=current();measured_open,opening=ContactCorrection().opening_target(hand,np.linalg.inv(o)@w)
                        (args.output/'measured-release-plan.json').write_text(json.dumps(opening,indent=2)+'\n');end_hand=measured_open
                    if label=='withdraw' and args.measured_release:end_hand=measured_open
                    if label in ['stand_tip','stand_yaw','stand_orient']:
                        _,_,_,w,o,_=current();upright_held_relation=np.linalg.inv(o)@w
                        upright_object=transform([table_obj[0,3],table_obj[1,3],args.upright_height],Rotation.from_euler('zy',[args.upright_yaw,180 if args.upright_end=='positive' else 0],degrees=True).as_quat())
                        if label=='stand_yaw':upright_object[:3,:3]=upright_object[:3,:3]@Rotation.from_euler('x',90 if args.upright_end=='negative' else -90,degrees=True).as_matrix()
                        if label=='stand_tip':
                            heading=np.arctan2(o[1,0],o[0,0])
                            upright_object[:3,:3]=Rotation.from_euler('z',heading).as_matrix()@Rotation.from_euler('x',np.pi if args.upright_end=='positive' else 0).as_matrix()
                        desired=upright_object@upright_held_relation
                    elif label=='stand_lower':
                        upright_object[2,3]=table_z+.0735-.0002
                        desired=upright_object@upright_held_relation
                    elif label in ['support_settle','unload_pinch','release_pinch','functional_touch','functional_close','gravity_close_unload','gravity_close_hold','gravity_close_restore']:desired=start.copy()
                    elif label=='gravity_close_orient':
                        _,_,_,w,o,_=current();tilted=o.copy()
                        up_in_knife=np.array([0.,np.sqrt(.75),.5]) if args.gravity_close_support=='tray' else np.array([0.,0.,1.])
                        tilted[:3,:3]=minimal_alignment(o[:3,:3]@up_in_knife,[0,0,1])@o[:3,:3]
                        tilted[:3,:3]=Rotation.from_euler('z',args.gravity_close_yaw,degrees=True).as_matrix()@tilted[:3,:3]
                        tilted[2,3]=max(o[2,3],1.10)
                        desired=tilted@np.linalg.inv(o)@w
                    elif label in ['relift','withdraw']:
                        desired=start.copy();desired[2,3]+=.20
                    elif label=='free_reorient':
                        _,_,_,_,actual_o,_=current()
                        tilt=np.arccos(np.clip(actual_o[2,2]*(-1 if args.upright_end=='positive' else 1),-1,1))
                        if actual_o[2,3]<table_z+.06 or tilt>.15:raise ValueError('Released knife did not remain standing')
                        functional_target=actual_o@np.asarray(table_regrasp['wrist_in_knife'])
                        desired=functional_target.copy();desired[2,3]+=.20
                        (args.output/'functional-approach-reference.json').write_text(json.dumps(dict(object_world=pose(actual_o).tolist(),
                            wrist_world=pose(functional_target).tolist(),localization='one-time simulation truth after actual withdrawal'),indent=2)+'\n')
                    elif label=='functional_approach':desired=functional_target.copy()
                    elif label=='operation_adjust':desired=post_acquisition_pose.copy()
                    else:desired=operation.copy()
                    rotations=Slerp([0,1],Rotation.from_matrix([start[:3,:3],desired[:3,:3]]))
                    arm_path=[targets[arm_idx].copy()];errors=[]
                    for alpha in np.linspace(0,1,31)[1:]:
                        waypoint=np.eye(4);waypoint[:3,:3]=rotations([alpha]).as_matrix()[0]
                        waypoint[:3,3]=start[:3,3]*(1-alpha)+desired[:3,3]*alpha
                        motor,error=k.solve_near(waypoint,arm_path[-1])
                        if error['position_m']>.001 or error['rotation_rad']>.005:
                            raise ValueError('Table-supported '+label+' IK failed: '+str(error))
                        arm_path.append(motor);errors.append(error)
                    collision_rows=[dict(knot=i,contacts=arm_table_check.collisions(motor)) for i,motor in enumerate(arm_path)]
                    (args.output/(label+'-table-clearance.json')).write_text(json.dumps(collision_rows,indent=2)+'\n')
                    if any(row['contacts'] for row in collision_rows):
                        raise ValueError('G2 arm/palm path intersects tabletop with 2mm planning margin: '+label)
                    (args.output/(label+'-arm-plan.json')).write_text(json.dumps(dict(q=[q.tolist() for q in arm_path],errors=errors,
                        wrist_target=pose(desired).tolist(),method='continuous Cartesian IK and finite joint drives',
                        condition='Normal flat initial knife; robot subsequently stands the modeled flat end on the original tabletop. No fixture or pose write.'),indent=2)+'\n')
                    steps=round(seconds/dt)
                    for i in range(steps):
                        alpha=smooth((i+1)/steps);loc=alpha*30;segment=min(int(loc),29);fraction=loc-segment
                        targets[arm_idx]=arm_path[segment]*(1-fraction)+arm_path[segment+1]*fraction
                        targets[hand_idx]=start_hand*(1-alpha)+end_hand*alpha
                        tick(label)
                    if label=='support_settle':
                        tail=records[-30:];support_fraction=np.mean([r['knife_table_contacts']>0 for r in tail])
                        _,_,_,_,supported_o,_=current()
                        support_tilt=float(np.arccos(np.clip(supported_o[2,2]*(-1 if args.upright_end=='positive' else 1),-1,1)))
                        (args.output/'table-support-check.json').write_text(json.dumps(dict(contact_fraction=float(support_fraction),
                            tilt_rad=support_tilt,center_height_m=float(supported_o[2,3]),modeled_end=args.upright_end,
                            required_fraction=.8,hand_table_contact_frames=sum(bool(np.any(r['finger_table_contacts'])) for r in tail),
                            object_world=records[-1]['object'].tolist()),indent=2)+'\n')
                        if support_fraction<.8:raise ValueError('Knife end support was not physically established for the final second')
                        if support_tilt>.15 or supported_o[2,3]<table_z+.06:raise ValueError('Table contact is not upright knife-end support')
                        if any(np.any(r['finger_table_contacts']) for r in tail):raise ValueError('Finger/table collision during standing support')
                    if label=='relift':
                        tail=records[-15:]
                        high_fraction=float(np.mean([r['object'][2]>table_z+.10 for r in tail]))
                        contacts=np.asarray([r['finger_knife_contacts'] for r in tail])>0
                        opposed=float(np.mean(contacts[:,0] & (contacts[:,1:].sum(1)>=2)))
                        (args.output/'functional-relift-check.json').write_text(json.dumps(dict(high_fraction=high_fraction,
                            opposed_contact_fraction=opposed,frames=15),indent=2)+'\n')
                        if high_fraction<1 or opposed<.9:raise ValueError('Functional regrasp did not retain knife through relift')
                    if label in ['gravity_close_hold','gravity_close_return']:
                        _,_,actual_slider,_,_,_=current()
                        (args.output/(label+'-check.json')).write_text(json.dumps(dict(slider_m=actual_slider,
                            lower_limit_m=slider_lower,closure_error_m=abs(actual_slider-slider_lower),
                            method='Passive gravity and physical hand contact; zero slider stiffness, no slider command or external object force.'),indent=2)+'\n')
                        if abs(actual_slider-slider_lower)>.002:
                            raise ValueError('Passive slider reclosure did not reach 2mm initialization tolerance: '+label)
                    continue
                if label=='preorient':
                    q,qa,sl,w,o,l=current();held_relation=np.linalg.inv(o)@w
                    desired_object=operation@transform(s[40:43],s[43:47])
                    desired_wrist=desired_object@held_relation
                    end_arm,error=k.solve(desired_wrist,targets[arm_idx])
                    if error['position_m']>.001 or error['rotation_rad']>.005 or np.max(np.abs(end_arm-targets[arm_idx]))>3.2:
                        raise ValueError('Preorientation IK unreachable or large arm branch change: '+str(error))
                    (args.output/'preorientation-plan.json').write_text(json.dumps(dict(wrist_target=pose(desired_wrist).tolist(),
                        object_target=pose(desired_object).tolist(),arm_q=end_arm.tolist(),ik=error,
                        localization='one-time simulation truth at lift end',physics='motor targets only; free object'),indent=2)+'\n')
                if label=='transport' and args.seat_at_operation:
                    end_arm,error=k.solve_near(operation,targets[arm_idx])
                    if error['position_m']>.001 or error['rotation_rad']>.005:raise ValueError('Final local operation IK failed: '+str(error))
                if label=='seat' and args.seating_plan:
                    seating=json.loads(args.seating_plan.read_text());(args.output/'seating-plan.json').write_text(json.dumps(seating,indent=2)+'\n')
                    q,qa,sl,w,o,l=current();fixed_object_reference=o.copy()
                    arm_path=[targets[arm_idx].copy()];hand_path=[targets[hand_idx].copy()];errors=[]
                    for row in seating['waypoints'][1:]:
                        target_pose=fixed_object_reference@np.asarray(row['wrist_in_knife'])
                        waypoint,error=k.solve_near(target_pose,arm_path[-1])
                        if error['position_m']>.001 or error['rotation_rad']>.005 or np.max(np.abs(waypoint-arm_path[-1]))>.6:
                            raise ValueError('Seating arm path unreachable/discontinuous: '+str(error))
                        arm_path.append(waypoint);hand_path.append(np.asarray(row['command_q']));errors.append(error)
                    (args.output/'seating-arm-plan.json').write_text(json.dumps(dict(q=[v.tolist() for v in arm_path],errors=errors,
                        fixed_object_reference=pose(fixed_object_reference).tolist(),object_is_free=True),indent=2)+'\n')
                    steps=round(seconds/dt);count=len(arm_path)-1
                    feedback=[]
                    relative_path=[np.asarray(row['wrist_in_knife']) for row in seating['waypoints']]
                    rotation_path=Slerp(np.arange(len(relative_path)),Rotation.from_matrix([v[:3,:3] for v in relative_path]))
                    initial_correction=np.linalg.inv(o)@w@np.linalg.inv(relative_path[0])
                    correction_rotation=Slerp([0,1],Rotation.from_matrix([initial_correction[:3,:3],np.eye(3)]))
                    last_feedback_target=targets[arm_idx].copy()
                    translation_feedback=np.zeros(3)
                    finger_feedback=None;finger_feedback_records=[]
                    previous_seating_object=o.copy();filtered_velocity=np.zeros(3);filtered_angular_velocity=np.zeros(3)
                    if args.seat_finger_feedback!='none':
                        from scripts.g2_seating_feedback import ContactCorrection
                        assert 'inverse_statics' in seating
                        finger_feedback=ContactCorrection()
                    for i in range(steps):
                        loc=(i+1)/steps*count;segment=min(int(loc),count-1);fraction=loc-segment
                        targets[arm_idx]=arm_path[segment]*(1-fraction)+arm_path[segment+1]*fraction
                        if args.seat_feedback!='none':
                            _,qa,_,actual_w,actual_o,_=current()
                            drift=np.linalg.norm(actual_o[:3,3]-fixed_object_reference[:3,3])
                            tilt=Rotation.from_matrix(fixed_object_reference[:3,:3].T@actual_o[:3,:3]).magnitude()
                            if drift>.05 or tilt>.8:raise ValueError('Seating oracle tracking safety bound exceeded: '+str((drift,tilt)))
                            relative_pose=np.eye(4);relative_pose[:3,:3]=rotation_path([loc]).as_matrix()[0]
                            relative_pose[:3,3]=relative_path[segment][:3,3]*(1-fraction)+relative_path[segment+1][:3,3]*fraction
                            # Start from the actually held relation, then align
                            # gradually. A sudden cached-frame command is not
                            # physically equivalent to an observation reset.
                            blend=smooth(min((i+1)/steps*4,1.))
                            correction=np.eye(4);correction[:3,:3]=correction_rotation([blend]).as_matrix()[0]
                            correction[:3,3]=initial_correction[:3,3]*(1-blend)
                            relative_pose=correction@relative_pose
                            if args.seat_feedback=='translation-truth':
                                # Correct measured sag, without chasing free
                                # object rotation with the seven-joint arm.
                                translation_feedback=.8*translation_feedback+.2*np.clip(actual_o[:3,3]-fixed_object_reference[:3,3],-.015,.015)
                                desired=fixed_object_reference@relative_pose
                                desired[:3,3]+=translation_feedback
                            else:desired=actual_o@relative_pose
                            motor,err=k.solve_near(desired,last_feedback_target,max_step=np.minimum(k.velocity*dt*.8,.15))
                            # Feedback IK is rate-limited, so small transient
                            # tracking error is expected. Do not confuse a
                            # 1 mm residual with a discontinuous arm branch.
                            if err['position_m']>.005 or err['rotation_rad']>.05:raise ValueError('Seating feedback tracking bound exceeded: '+str(err))
                            last_feedback_target=motor.copy()
                            targets[arm_idx]=motor
                            feedback.append(dict(step=global_step,object_observed=pose(actual_o).tolist(),wrist_target=pose(desired).tolist(),ik=err))
                        if finger_feedback is not None:
                            measured_hand,_,_,actual_w,actual_o,_=current()
                            servo=None
                            if args.seat_object_servo:
                                filtered_velocity=.5*filtered_velocity+.5*(actual_o[:3,3]-previous_seating_object[:3,3])/dt
                                filtered_angular_velocity=.5*filtered_angular_velocity+.5*Rotation.from_matrix(actual_o[:3,:3]@previous_seating_object[:3,:3].T).as_rotvec()/dt
                                servo=(actual_o,fixed_object_reference,filtered_velocity,filtered_angular_velocity)
                                previous_seating_object=actual_o.copy()
                            targets[hand_idx],diagnostic=finger_feedback.correct(seating['waypoints'][segment],seating['waypoints'][segment+1],
                                fraction,np.linalg.inv(actual_o)@actual_w,targets[hand_idx],(i+1)/steps,dt,object_servo=servo,
                                residual=args.seat_finger_mode=='residual',measured_q=measured_hand)
                            finger_feedback_records.append(dict(step=global_step,**diagnostic))
                            (args.output/'seating-finger-feedback.json').write_text(json.dumps(finger_feedback_records)+'\n')
                            if args.seat_finger_mode=='contact' and diagnostic['max_contact_error_m']>.01:raise ValueError('Oracle finger contact IK error exceeds 10mm: '+str(diagnostic['max_contact_error_m']))
                            if args.seat_finger_mode=='residual' and (np.linalg.norm(actual_o[:3,3]-fixed_object_reference[:3,3])>.05 or
                                Rotation.from_matrix(fixed_object_reference[:3,:3].T@actual_o[:3,:3]).magnitude()>.8):
                                raise ValueError('Residual seating exceeds 50mm / 0.8rad pose bound')
                        else:targets[hand_idx]=hand_path[segment]*(1-fraction)+hand_path[segment+1]*fraction
                        tick(label)
                        if feedback:
                            (args.output/'seating-feedback.json').write_text(json.dumps(feedback)+'\n')
                    continue
                if label=='transport' and args.transport_path=='level':
                    q,qa,sl,w,o,l=current()
                    path,info=k.level_transport(w,operation,np.linalg.inv(o)@w,targets[arm_idx])
                    (args.output/'transport-plan.json').write_text(json.dumps(dict(**info,q=[v.tolist() for v in path]),indent=2)+'\n')
                    begin=targets[arm_idx].copy();trajectory=np.vstack([begin,path]);steps=round(seconds/dt)
                    for i in range(steps):
                        loc=(i+1)/steps*len(path);segment=min(int(loc),len(path)-1);fraction=loc-segment
                        targets[arm_idx]=trajectory[segment]*(1-fraction)+trajectory[segment+1]*fraction
                        targets[hand_idx]=end_hand
                        tick(label)
                    continue
                start_arm=targets[arm_idx].copy();start_hand=targets[hand_idx].copy();steps=round(seconds/dt)
                close_waypoints=custom_plan.get('close_waypoints') if label=='close' and custom_plan else None
                if close_waypoints:
                    assert close_waypoints[0]['fraction']==0 and close_waypoints[-1]['fraction']==1
                    assert np.max(abs(np.asarray(close_waypoints[0]['q'])-start_hand))<1e-6,'Closing plan must begin at actual previous motor reference'
                for i in range(steps):
                    alpha=smooth((i+1)/steps)
                    targets[arm_idx]=start_arm+(end_arm-start_arm)*alpha
                    targets[hand_idx]=start_hand+(end_hand-start_hand)*alpha
                    if close_waypoints:
                        u=(i+1)/steps
                        for first,last in zip(close_waypoints,close_waypoints[1:]):
                            if first['fraction']<=u<=last['fraction']:
                                v=smooth((u-first['fraction'])/(last['fraction']-first['fraction']))
                                targets[hand_idx]=(1-v)*np.asarray(first['q'])+v*np.asarray(last['q'])
                                break
                    tick(label)
            if args.learned_hold_policy or args.fixed_preparation_hold:
                if args.learned_hold_policy:
                    from scripts.g2_local_runtime import LocalPolicyRuntime
                    learned_runtime=LocalPolicyRuntime(args.learned_hold_policy,dof[:,0].cpu().numpy(),dof[:,1].cpu().numpy(),targets,
                        rb[wrist_id].cpu().numpy(),rb[obj_id].cpu().numpy(),rb[slider_id].cpu().numpy())
                    assert learned_runtime.task=='H'
                    hold_reference=learned_runtime.initial_object[0].numpy().copy()
                    hold_description=learned_runtime.description();hold_phase='learned_hold';hold_file='learned-hold.json'
                else:
                    hold_reference=rb[obj_id,:7].cpu().numpy().copy()
                    hold_description=dict(method='fixed actual hand motor references for22s; G2 servo unchanged',task='H',checkpoint=None)
                    hold_phase='fixed_motor_hold';hold_file='fixed-motor-hold.json'
                hold_start=len(records)
                hold_slider_reference=float(dof[-1,0])
                for _ in range(660):
                    if learned_runtime is not None:
                        targets[hand_idx]=learned_runtime.step(dof[:,0].cpu().numpy(),dof[:,1].cpu().numpy(),
                            rb[wrist_id].cpu().numpy(),rb[obj_id].cpu().numpy(),rb[slider_id].cpu().numpy(),targets[hand_idx])
                    tick(hold_phase)
                held=np.asarray([r['object'] for r in records[hold_start:]])
                drift=np.linalg.norm(held[:,:3]-hold_reference[:3],axis=-1)
                rotation=(Rotation.from_quat(hold_reference[3:]).inv()*Rotation.from_quat(held[:,3:])).magnitude()
                hold_slider_error=max(abs(r['slider']-hold_slider_reference) for r in records[hold_start:])
                hold_table_contact=any(r['knife_table_contacts']>0 for r in records[hold_start:])
                if learned_runtime is not None:hold_description=learned_runtime.description()
                hold_report=dict(**hold_description,duration_s=22.,world_reference=hold_reference.tolist(),
                    max_world_drift_m=float(drift.max()),max_world_rotation_rad=float(rotation.max()),
                    stable_10mm_025rad=bool((drift<.01).all() and (rotation<.25).all()),
                    slider_error_m=float(hold_slider_error),knife_table_contact=hold_table_contact,
                    hold_success=bool((drift<.01).all() and (rotation<.25).all() and hold_slider_error<.01 and not hold_table_contact and (held[:,2]>=table_z+.05).all()),
                    below_table=bool((held[:,2]<table_z+.05).any()),scope='continuous acquired H only, no slider success claim')
                (args.output/hold_file).write_text(json.dumps(hold_report,indent=2)+'\n')
                learned_runtime=None
            for _ in range(round(args.settle_seconds/dt)):tick('settle_history')
        q,qa,sl,w,o,l=current()
        if args.group=='A' and preset_candidate is None:
            # RB tensors do not run FK after an initialization write until the
            # first simulate. Use the declared initial state for the first
            # observation, exactly as original ArtManip's at_reset_ids path.
            q=s[:20].copy();qa=arm[:len(arm_idx)].copy();sl=slider_lower+args.preset_slider_offset;w=operation.copy();o=initial_obj.copy()
            l=operation@transform(s[47:50],s[50:54])
            l[:3,3]+=o[:3,:3]@np.array([0,0,args.preset_slider_offset+args.preset_object_axis_offset])
        preset_reference=s.copy()
        if args.group=='A' and (args.preset_slider_offset or args.preset_object_axis_offset):
            preset_reference[40:47]=pose(np.linalg.inv(w)@o);preset_reference[47:54]=pose(np.linalg.inv(w)@l)
        policy.takeover(q,targets[hand_idx],w,o,l,slider_lower,reference_state=preset_reference if args.group=='A' and preset_candidate is None else None)
        policy.previous_slider=sl
        rel=pose(np.linalg.inv(w)@o)
        hold_check=acquisition_hold({key:[r[key] for r in records] for key in records[0]},s,table_z) if args.group!='A' or preset_candidate is not None else None
        legacy_hold_check=hold_check
        if args.preset_support_gate:
            assert args.group=='A' and preset_candidate is not None and args.knife_spec
            from scripts.g2_tabletop_metrics import preset_support_hold
            hold_check=preset_support_hold(records,table_z)
        grasp_success=hold_check['success'] if hold_check is not None else True
        takeover=dict(step=global_step,time=global_step*dt,q=q.tolist(),targets=targets[hand_idx].tolist(),
            arm_q=qa.tolist(),object_world=pose(o).tolist(),wrist_world=pose(w).tolist(),object_hand=rel.tolist(),
            grasp_success=grasp_success if args.group!='A' else None,slider_at_takeover=sl,slider_command_origin=slider_lower,
            acquisition_hold_check=hold_check,legacy_opposed_grip_check=legacy_hold_check,
            table_height=table_z,
            policy_action_mode=args.policy_action_mode,
            executed_action_provenance='raw actor output' if args.policy_action_mode=='full' else 'thumb actor output; non-thumb components explicitly zeroed before controller, last-action observation and history; raw output saved separately',
            student_initialization='ideal_simulation_truth_at_takeover' if args.group=='C' else None,
            acquisition_localization='live simulation object truth during seating: '+args.seat_feedback if args.seat_feedback!='none' else 'configured table placement and one-time truth for seating planning',
            acquisition_finger_localization=args.seat_finger_feedback,table_supported_regrasp=bool(table_regrasp),
            additional_acquisition_truth_sources=dict(settled_table_pose=args.table_localization=='settled-truth',air_flip_pivot=bool(args.air_flip),standing_level_samples=4 if args.level_standing_knife else 0,
                measured_release_pose=args.measured_release,functional_reapproach_pose=bool(table_regrasp),
                gravity_closure_orientation=args.gravity_close_before_takeover),
            history_frames=len(policy.history),rnn='zeroed once at takeover',history='actual settled q and zero hold actions',
            force_sensor_enabled=force_sensor_enabled,
            hand_gravity='enabled from first physics step' if args.hand_gravity else 'disabled as frozen training',
            hand_gravity_motor_feedforward=args.hand_gravity_compensation,arm_gravity=args.arm_gravity,
            gravity_in_wrist=(w[:3,:3].T@np.array([0,0,-9.81])).tolist())
        if preset_candidate is not None:
            takeover['preset_scope']='Independent geometry candidate initialized before first physics step; actual2s history and actual settled motor reference; not tabletop acquisition.'
            takeover['preset_hold_success']=bool(grasp_success)
        (args.output/'takeover.json').write_text(json.dumps(takeover,indent=2)+'\n')
        if args.geometric_operation:
            assert args.group=='A' and knife_geometry is not None and args.learned_operation_policy is None
            from scripts.g2_v2_thumb_feedback import ThumbFeedback
            config=json.loads(args.geometric_operation.read_text());geometric_runtime=ThumbFeedback(config,knife_geometry,q,targets[hand_idx],w,o,sl)
            (args.output/'geometric-operation.json').write_text(json.dumps(dict(config=config,actual_initialization=geometric_runtime.initialization),indent=2)+'\n')
        if args.learned_operation_policy:
            from scripts.g2_local_runtime import LocalPolicyRuntime
            learned_runtime=LocalPolicyRuntime(args.learned_operation_policy,dof[:,0].cpu().numpy(),dof[:,1].cpu().numpy(),targets,
                rb[wrist_id].cpu().numpy(),rb[obj_id].cpu().numpy(),rb[slider_id].cpu().numpy(),
                reset_quaternion_compat=args.local_reset_quaternion_compat,input_ablation=args.operation_input_ablation,
                freeze_initial_action=args.operation_static_policy)
            assert learned_runtime.task=='S'
            (args.output/'learned-operation.json').write_text(json.dumps(learned_runtime.description(),indent=2)+'\n')
        if not args.only_grasp and ((args.group=='A' and preset_candidate is None) or grasp_success):
            for step in range(round(args.seconds/dt)):
                if step>0 or args.group!='A':q,qa,sl,w,o,l=current()
                offset=.04 if (step//150)%2==0 else 0.
                if geometric_runtime is not None:
                    target=geometric_runtime.step(q,w,o,sl,step);action=np.zeros(20,dtype=np.float32);obs=np.zeros(138,dtype=np.float32);policy.last_raw_action[:]=0
                elif learned_runtime is not None and learned_runtime.thumb_plan is not None:
                    # Explicit new geometric thumb prior, not frozen actor output.
                    target=targets[hand_idx].copy();action=np.zeros(20,dtype=np.float32)
                    obs=np.zeros(138,dtype=np.float32);policy.last_raw_action[:]=0
                else:
                    target,action,obs=policy.step(q,w,o,l,sl,offset)
                if learned_runtime is not None:
                    target=learned_runtime.step(dof[:,0].cpu().numpy(),dof[:,1].cpu().numpy(),
                        rb[wrist_id].cpu().numpy(),rb[obj_id].cpu().numpy(),rb[slider_id].cpu().numpy(),target)
                    if learned_runtime.route=='joint' or learned_runtime.thumb_plan is not None:
                        # Feed actual joint-composite thumb commands into both
                        # incremental reference and next actor/history input.
                        # Keep raw frozen action separately in the trace.
                        action=action.copy()
                        action[16:]=learned_runtime.executed_thumb_action[0].numpy()
                        policy.last_action=action.copy()
                        policy.control.previous_targets=target.copy()
                targets[hand_idx]=target
                # New local task uses the verified physical lower limit as0mm,
                # even if the actual acquisition left the slider partly open.
                zero=learned_runtime.slider_lower if learned_runtime is not None else policy.slider_initial
                tick('operate',action,zero+offset,obs)
                if geometric_runtime is not None:records[-1]['geometric_feedback']=np.array([geometric_runtime.last[n] for n in ['reference_distance_m','long_feedback_m','ik_error_m']])
        trace={k:np.asarray([r[k] for r in records]) for k in records[0]}
        np.savez_compressed(args.output/'trace.npz',**trace)
        report=score(trace,takeover,args.group)
        if args.learned_hold_policy or args.fixed_preparation_hold:
            hold_report=json.loads((args.output/('fixed-motor-hold.json' if args.fixed_preparation_hold else 'learned-hold.json')).read_text())
            report['preparation_hold_success']=hold_report['hold_success']
            if args.learned_hold_policy:report['learned_preparation_hold_success']=hold_report['hold_success']
            report['operation_window_success']=report.get('required_task_success',False)
            if not hold_report['hold_success']:
                for key in ['whole_success','required_task_success','whole_stable_success']:
                    report[key]=False
                report['failure_class']='fixed_hold_preparation_failed' if args.fixed_preparation_hold else 'learned_hold_preparation_failed'
        if preset_candidate is not None:
            report.update(preset_hold_success=bool(grasp_success),preset_scope=takeover['preset_scope'],
                preset_candidate_sha256=hashlib.sha256(args.preset_candidate.read_bytes()).hexdigest())
            if not grasp_success:report['failure_class']='preset_candidate_hold_failed_before_policy'
        if args.short_lift_diagnostic:
            report['short_lift_diagnostic']=True;report['full_acquisition_evaluated']=False;report['short_lift_check']=json.loads((args.output/'pickup-hold-check.json').read_text())
        report.update(group=args.group,args={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
            teacher_sha256=hashlib.sha256(args.teacher.read_bytes()).hexdigest(),
            student_sha256=hashlib.sha256(args.student.read_bytes()).hexdigest() if args.group=='C' else None,
            model_sha256=model['urdf_sha256'],initial_state_writes='only before first physics step',
            slider_drive_stiffness=0.,object_external_forces=False,object_constraints=False)
        report['operation_controller']=learned_runtime.description() if learned_runtime is not None else dict(method='original actor',action_mode=args.policy_action_mode,student=args.group=='C')
        if geometric_runtime is not None:report['operation_controller']=dict(method='privileged geometric thumb feedback',config=str(args.geometric_operation),frozen_actor_executed=False)
        report['original_actor_executed_in_operation']=bool(report['operation_steps'] and geometric_runtime is None and (learned_runtime is None or learned_runtime.thumb_plan is None))
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    except Exception as error:
        failure=dict(exception_type=type(error).__name__,message=str(error),steps=global_step,
            last_phase=records[-1]['phase'] if records else None,group=args.group,physics_trace_preserved=True)
        (args.output/'failure.json').write_text(json.dumps(failure,indent=2)+'\n')
        raise
    finally:
        if pair_records:
            with (args.output/'knife-contact-pairs.jsonl').open('w') as stream:
                for row in pair_records:stream.write(json.dumps(row)+'\n')
        if records and not (args.output/'trace.npz').exists():
            np.savez_compressed(args.output/'partial-trace.npz',**{k:np.asarray([r[k] for r in records]) for k in records[0]})
        if writer:writer.close()
        if close_writer:close_writer.close()
        gym.destroy_sim(sim)


def score(trace,takeover,group):
    sel=trace['phase']=='operate'
    table_height=takeover.get('table_height',.75)
    out={'grasp_success':takeover['grasp_success'],'operation_steps':int(sel.sum()),
         'acquisition_hold_check':takeover.get('acquisition_hold_check'),
         'table_contact_peak_N':float(np.linalg.norm(trace['table_force'],axis=-1).max()),
         'max_object_height_m':float(trace['object'][:,2].max())}
    lift=np.where(trace['phase']=='lift')[0]
    out['lift_success']=bool(len(lift) and (trace['object'][lift[-15:],2]>table_height+.10).all()) if group!='A' else None
    if group!='A':
        out['acquisition_stage_failure']=None if takeover['grasp_success'] else ('not_lifted' if not out['lift_success'] else 'lost_after_lift')
        relift=np.flatnonzero(trace['phase']=='relift')
        if len(relift) and not (trace['object'][relift[-15:],2]>table_height+.10).all():
            out['acquisition_stage_failure']='functional_regrasp_not_retained'
        for phase in ['air_flip','preorient','stand_tip','stand_yaw','stand_orient','stand_lower','support_settle','stand_level','unload_pinch','release_pinch','withdraw','free_reorient',
            'functional_approach','functional_touch','functional_close','seat','relift','transport','gravity_close_orient','gravity_close_unload','gravity_close_hold','gravity_close_restore','gravity_close_return','operation_adjust','settle_history']:
            mask=trace['phase']==phase
            if out['lift_success'] and mask.any() and (trace['object'][mask,2]<table_height+.05).any():
                out['acquisition_stage_failure']='dropped_during_'+phase;break
    if not sel.any():
        out.update(whole_success=False,operation_success_given_grasp=None,
                   required_task_success=False,operation_complete_20s=False,
                   whole_success_evaluated=not takeover['grasp_success'],
                   failure_class=out.get('acquisition_stage_failure') if not takeover['grasp_success'] else 'operation_not_requested')
        return out
    slider=trace['slider'][sel];goal=trace['goal'][sel]
    obj=trace['object'][sel]; wrist=trace['wrist'][sel]
    initial=np.asarray(takeover['object_world']);local_init=np.asarray(takeover['object_hand'])
    drift=np.linalg.norm(obj[:,:3]-initial[:3],axis=1)
    rotation=(Rotation.from_quat(initial[3:]).inv()*Rotation.from_quat(obj[:,3:])).magnitude()
    relative=np.array([pose(np.linalg.inv(transform(w[:3],w[3:]))@transform(o[:3],o[3:])) for w,o in zip(wrist,obj)])
    rel_drift=np.linalg.norm(relative[:,:3]-local_init[:3],axis=1)
    rel_rotation=(Rotation.from_quat(local_init[3:]).inv()*Rotation.from_quat(relative[:,3:])).magnitude()
    endpoints=[]
    for start in range(0,len(slider),150):
        end=min(start+150,len(slider));error=np.abs(slider[max(start,end-9):end]-goal[max(start,end-9):end])
        endpoints.append(dict(stage=len(endpoints),max_error_m=float(error.max()),final_error_m=float(error[-1]),
                              complete_phase=end-start==150,
                              within_10mm=bool(end-start==150 and (error<.01).all()),within_2mm=bool(end-start==150 and (error<.002).all())))
    complete_20s=len(slider)==600 and len(endpoints)==4
    basic=complete_20s and all(e['within_10mm'] for e in endpoints)
    held=(rel_drift<.05)&(rel_rotation<1.57)
    no_contacts=(trace['finger_knife_contacts'][sel]>0).sum(1)==0
    escaped=no_contacts & (rel_drift>.05)
    drop_frames=obj[:,2]<table_height+.05
    if 'knife_table_contacts' in trace:drop_frames=drop_frames | (trace['knife_table_contacts'][sel]>0)
    physical_drop=bool(drop_frames.any() or (len(escaped)>=3 and np.convolve(escaped.astype(int),np.ones(3,dtype=int),'valid').max()>=3))
    retained=held & ~drop_frames
    complete_cycles=sum(endpoints[i]['within_10mm'] and endpoints[i+1]['within_10mm'] and
        retained[i*150:min((i+2)*150,len(held))].all() for i in range(0,len(endpoints)-1,2))
    stable=bool((drift<.01).all() and (rotation<.25).all())
    acquisition_drop=(out.get('acquisition_stage_failure') or '').startswith('dropped_during_')
    out.update(slider_travel_m=float(np.ptp(slider)),endpoints=endpoints,basic_10mm=basic,
        completed_cycles=int(complete_cycles),
        failure_class='operation_drop' if physical_drop else ('operation_pose_escape' if not held.all() else ('operation_endpoint_error' if not basic else ('operation_unstable_drift' if not stable else None))),
        physical_drop_detected=physical_drop,major_relative_rotation=bool((rel_rotation>=1.57).any()),
        retained_within_pose_bounds=bool(held.all()),
        strict_2mm=complete_20s and all(e['within_2mm'] for e in endpoints),
        operation_complete_20s=complete_20s,
        world_drift_max_m=float(drift.max()),world_rotation_max_rad=float(rotation.max()),
        hand_relative_drift_max_m=float(rel_drift.max()),hand_relative_rotation_max_rad=float(rel_rotation.max()),
        stable_world_10mm_025rad=bool((drift<.01).all() and (rotation<.25).all()),
        natural_no_drop=bool((rel_drift<.05).all() and (rel_rotation<1.57).all()),
        below_table=bool((obj[:,2]<table_height).any()),
        legacy_endpoint_retention_success=bool((group=='A' or takeover['grasp_success']) and basic and held.all() and not physical_drop and not acquisition_drop),
        whole_success=bool((group=='A' or takeover['grasp_success']) and basic and stable and not physical_drop and not acquisition_drop),
        required_task_success=bool((group=='A' or takeover['grasp_success']) and basic and stable and not physical_drop and not acquisition_drop),
        operation_success_given_grasp=bool(basic and stable and not physical_drop) if group!='A' else None,
        whole_stable_success=bool((group=='A' or takeover['grasp_success']) and basic and stable and not physical_drop and not acquisition_drop))
    return out


if __name__=='__main__':main()
