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
    parser.add_argument('--video',action='store_true')
    parser.add_argument('--seconds',type=float,default=20)
    parser.add_argument('--arm-gain-scale',type=float,default=1.)
    parser.add_argument('--arm-damping-scale',type=float,default=1.)
    parser.add_argument('--arm-gravity',choices=['on','off'],default='on')
    parser.add_argument('--dx',type=float,default=0.)
    parser.add_argument('--dy',type=float,default=0.)
    parser.add_argument('--yaw',type=float,default=0.)
    parser.add_argument('--close-height',type=float,default=0.)
    parser.add_argument('--settle-seconds',type=float,default=2.)
    parser.add_argument('--only-grasp',action='store_true')
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
    parser.add_argument('--seat-at-operation',action='store_true',help='Carry held knife to the trained object attitude before changing grasp contacts.')
    parser.add_argument('--operation-pose',type=Path,help='Explicit wrist 4x4 pose for labeled gravity/interface diagnostics.')
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
    parser.add_argument('--air-flip-shift',type=float,nargs=3,default=[0.,0.,0.],help='Smooth world translation of the planned wrist-flip pivot; robot motion only.')
    parser.add_argument('--air-flip-only',action='store_true',help='Diagnostic: stop after free-space flip and actual settling, without transport or policy operation.')
    parser.add_argument('--lift-height',type=float,default=.20,help='Vertical wrist lift in metres; no object state changes.')
    parser.add_argument('--slider-face',choices=['up','down'],default='up',help='Initial tabletop placement; down starts above the protruding passive slider and settles freely.')
    parser.add_argument('--table-localization',choices=['configured','settled-truth'],default='configured',help='Acquisition-only ideal localization after natural tabletop settling.')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    assert not args.hand_only_diagnostic or args.group=='A'
    assert not args.seat_object_servo or args.seat_finger_feedback=='object-truth'
    assert args.seat_finger_mode!='residual' or args.seat_object_servo
    assert not args.table_supported_seat or (args.group!='A' and (args.table_regrasp_plan or (args.seating_plan and args.seat_seconds>0)) and not args.seat_at_operation)
    assert not args.table_regrasp_plan or args.table_supported_seat
    assert (args.preset_slider_offset==0 and args.preset_object_axis_offset==0) or args.group=='A'
    assert not (args.level_standing_knife or args.measured_release) or args.table_regrasp_plan
    assert 5<=args.upright_orient_seconds<=20
    assert not args.gravity_close_before_takeover or (args.table_regrasp_plan and args.group!='A')
    assert args.gravity_close_support!='tray' or args.gravity_close_before_takeover
    assert abs(args.gravity_close_yaw)<=30
    assert not args.post_acquisition_pose or (args.group!='A' and args.table_supported_seat)
    assert not args.air_flip or (args.group!='A' and not args.table_supported_seat and not args.seat_at_operation)
    assert not args.air_flip_only or (args.air_flip and args.only_grasp and args.seat_seconds==0)
    assert 5<=args.air_flip_seconds<=20 and .20<=args.lift_height<=.40
    assert np.linalg.norm(args.air_flip_shift)<=.25
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',1,
        ['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=True','rl_device=cpu'],train='wujiAcquisitionSAPG')
    (args.output/'frozen-config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    assert cfg.task.env.forceScale==0 and cfg.task.env.actionsMovingAverage==1 and not cfg.task.env.useRelativeControl
    k=G2Kinematics(); model=json.loads((ROOT/'assets/robots/g2_wuji/audit.json').read_text())
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[args.grasp]
    operation=transform([.40,-.30,1.05],(Rotation.from_euler('z',args.operation_yaw,degrees=True)*Rotation.from_euler('y',-90,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
    if args.operation_pose:operation=np.asarray(json.loads(args.operation_pose.read_text()),dtype=float)
    post_acquisition_pose=None
    if args.post_acquisition_pose:
        post_acquisition_pose=np.asarray(json.loads(args.post_acquisition_pose.read_text()),dtype=float)
        assert np.linalg.norm(post_acquisition_pose[:3,3]-operation[:3,3])<=.020
        assert Rotation.from_matrix(operation[:3,:3].T@post_acquisition_pose[:3,:3]).magnitude()<=np.deg2rad(15)+1e-8
    op_q,op_error=k.solve(operation)
    assert op_error['position_m']<1e-4 and op_error['rotation_rad']<1e-3,op_error
    table_z=args.table_height
    from scripts.g2_table_collision import ArmTableCollision
    arm_table_check=ArmTableCollision(table_z)
    table_obj=transform([.50+args.dx,-.30+args.dy,table_z+(.0071 if args.slider_face=='down' else .0041)],
        (Rotation.from_euler('z',args.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
    if args.slider_face=='down':table_obj=table_obj@transform(quaternion=Rotation.from_euler('z',180,degrees=True).as_quat())
    grasp_pose=table_obj@transform(quaternion=Rotation.from_euler('z',args.grasp_roll,degrees=True).as_quat())@np.linalg.inv(transform(s[40:43],s[43:47]))
    grasp_pose[2,3]+=args.close_height
    custom_plan=None
    if args.grasp_plan:
        assert args.group!='A'
        custom_plan=json.loads(args.grasp_plan.read_text())
        (args.output/'grasp-plan.json').write_text(json.dumps(custom_plan,indent=2)+'\n')
        grasp_pose=table_obj@np.asarray(custom_plan['wrist_in_knife'])
        grasp_pose[2,3]+=args.close_height
    above=grasp_pose.copy(); above[2,3]+=.16
    lifted=grasp_pose.copy(); lifted[2,3]+=args.lift_height
    high_q,high_error=k.solve(above,op_q)
    grasp_q,grasp_error=k.solve(grasp_pose,high_q)
    lift_q,lift_error=k.solve(lifted,grasp_q)
    if args.wrist_posture is not None:
        high_q,high_error=k.solve_wrist_posture(above,high_q,args.wrist_posture)
        grasp_q,grasp_error=k.solve_wrist_posture(grasp_pose,high_q,args.wrist_posture)
        lift_q,lift_error=k.solve_wrist_posture(lifted,grasp_q,args.wrist_posture)
    plan=dict(operation=op_error,approach=high_error,grasp=grasp_error,lift=lift_error,
              operation_q=op_q.tolist(),approach_q=high_q.tolist(),grasp_q=grasp_q.tolist(),lift_q=lift_q.tolist(),
              table_top=table_z,knife_pose=pose(table_obj).tolist(),planned_wrist_pose=pose(grasp_pose).tolist())
    (args.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    assert max(e['position_m'] for e in [high_error,grasp_error,lift_error])<.001
    policy=FrozenPolicy(cfg,args.teacher,args.student if args.group=='C' else None)
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
        # Frozen hand has gravity disabled. G2 retains gravity unless a labeled diagnostic requests otherwise.
        p.flags=1 if name.startswith('hand_r_') or args.arm_gravity=='off' else 0
    gym.set_actor_rigid_body_properties(env,robot,rb_props)
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
    obj_asset=gym.load_asset(sim,str(ROOT),'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf',options)
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
        knife_asset_sha256=hashlib.sha256((ROOT/'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf').read_bytes()).hexdigest(),
        robot_dof_properties={n:props[n].tolist() for n in props.dtype.names},
        knife_dof_properties={n:p[n].tolist() for n in p.dtype.names},
        robot_body_names=rb_names,robot_gravity_flags=[int(v.flags) for v in gym.get_actor_rigid_body_properties(env,robot)],
        collision_filters=[int(v.filter) for v in gym.get_actor_rigid_shape_properties(env,robot)],
        knife_mass=[float(v.mass) for v in gym.get_actor_rigid_body_properties(env,knife)],
        table_friction=[float(v.friction) for v in gym.get_actor_rigid_shape_properties(env,table)],
        source_self_collision='G2 non-hand self-contact disabled per asset; existing Wuji digit filtering retained')
    (args.output/'physics.json').write_text(json.dumps(effective,indent=2)+'\n')
    closed=s[20:40].copy();opened=closed.copy()
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
    targets=np.zeros(len(names)+1,dtype=np.float32);targets[hand_idx]=closed if args.group=='A' else opened
    targets[arm_idx]=arm[:len(arm_idx)];targets[-1]=slider_lower
    writer=None;cam=None
    if args.video:
        import imageio.v2 as imageio
        cp=gymapi.CameraProperties();cp.width=960;cp.height=720;cp.horizontal_fov=65;cp.use_collision_geometry=False
        cam=gym.create_camera_sensor(env,cp)
        camera_pos=[1.5,-1.6,1.65] if args.camera=='wide' else [.95,-.85,1.45]
        camera_target=[.35,-.25,1.0] if args.camera=='wide' else [.4,-.3,1.0]
        gym.set_camera_location(cam,env,gymapi.Vec3(*camera_pos),gymapi.Vec3(*camera_target))
        writer=imageio.get_writer(str(args.output/'continuous.mp4'),fps=30,macro_block_size=8)
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
    pair_records=[]
    arm_integral=np.zeros(len(arm_idx))
    def tick(phase,action=None,goal=0.,obs=None):
        nonlocal global_step
        reference_targets=targets.copy();command_targets=targets.copy()
        if args.arm_integral_gain:
            measured=dof[arm_idx,0].cpu().numpy()
            arm_integral[:]=np.clip(arm_integral+args.arm_integral_gain*dt*(targets[arm_idx]-measured),-.08,.08)
            command_targets[arm_idx]=np.clip(targets[arm_idx]+arm_integral,k.lower,k.upper)
        gym.set_dof_position_target_tensor(sim,gymtorch.unwrap_tensor(torch.from_numpy(command_targets)))
        for _ in range(4):gym.simulate(sim);gym.fetch_results(sim,True)
        refresh();q,qa,sl,w,o,l=current()
        executed=np.zeros(20,dtype=np.float32) if action is None else action
        policy.record(q,executed)
        finger_table=np.zeros(5,dtype=np.int32);finger_knife=np.zeros(5,dtype=np.int32)
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
            for i,f in enumerate(digits):
                digit_contact=any('_'+f+'_' in env_names.get(b,'') for b in pair)
                if digit_contact and table_env in pair:finger_table[i]+=1
                if digit_contact and pair & knife_env:finger_knife[i]+=1
        records.append(dict(time=(global_step+1)*dt,phase=phase,q=q,arm_q=qa,targets=command_targets,reference_targets=reference_targets,action=executed.copy(),
            dof_velocity=dof[:,1].cpu().numpy().copy(),dof_effort=efforts.cpu().numpy().copy() if efforts is not None else np.full(len(names)+1,np.nan),
            finger_table_contacts=finger_table,finger_knife_contacts=finger_knife,
            knife_table_contacts=knife_table_count,robot_table_contacts=robot_table_count,
            slider=sl,goal=goal,wrist=pose(w),object=pose(o),slider_pose=pose(l),
            table_force=contact[table_id].cpu().numpy().copy(),hand_force=contact[hand_bodies].cpu().numpy().copy(),
            observation=np.zeros(138,dtype=np.float32) if obs is None else obs))
        if writer:
            gym.step_graphics(sim);gym.render_all_camera_sensors(sim)
            frame=gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR)
            writer.append_data(np.asarray(frame).reshape(720,960,4)[:,:,:3])
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
        if args.group!='A':
            for _ in range(60):tick('table_settle')
            if args.table_localization=='settled-truth':
                assert custom_plan is not None
                _,_,_,_,actual_table_object,_=current()
                measured_grasp=actual_table_object@np.asarray(custom_plan['wrist_in_knife'])
                measured_grasp[2,3]+=args.close_height
                measured_lift=measured_grasp.copy();measured_lift[2,3]+=args.lift_height
                grasp_q,grasp_error=k.solve_near(measured_grasp,grasp_q,max_step=.4)
                lift_q,lift_error=k.solve_near(measured_lift,lift_q,max_step=.4)
                if max(grasp_error['position_m'],lift_error['position_m'])>.001 or max(grasp_error['rotation_rad'],lift_error['rotation_rad'])>.005:
                    raise ValueError('Settled-table localization IK failed')
                (args.output/'settled-table-localization.json').write_text(json.dumps(dict(
                    object=pose(actual_table_object).tolist(),grasp_q=grasp_q.tolist(),lift_q=lift_q.tolist(),
                    grasp_ik=grasp_error,lift_ik=lift_error,method='One simulated truth sample after natural tabletop settling; only arm motor targets replanned.'),indent=2)+'\n')
            phases=[('approach',grasp_q,opened,4),('close',grasp_q,closed,3),('lift',lift_q,closed,4)]
            if args.air_flip:phases.append(('air_flip',None,closed,args.air_flip_seconds))
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
            if not args.air_flip_only:phases.append(('transport',op_q,functional if args.seat_seconds>0 or table_regrasp else closed,5))
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
            for label,end_arm,end_hand,seconds in phases:
                if label=='air_flip':
                    from scripts.g2_air_flip import plan_flip, check_flip
                    _,_,_,actual_w,actual_o,_=current()
                    path,diagnostic=plan_flip(k,actual_w,actual_o,targets[arm_idx],args.air_flip,seconds,dt,arm_table_check,args.air_flip_shift)
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
                for i in range(steps):
                    alpha=smooth((i+1)/steps)
                    targets[arm_idx]=start_arm+(end_arm-start_arm)*alpha
                    targets[hand_idx]=start_hand+(end_hand-start_hand)*alpha
                    tick(label)
            for _ in range(round(args.settle_seconds/dt)):tick('settle_history')
        q,qa,sl,w,o,l=current()
        if args.group=='A':
            # RB tensors do not run FK after an initialization write until the
            # first simulate. Use the declared initial state for the first
            # observation, exactly as original ArtManip's at_reset_ids path.
            q=s[:20].copy();qa=arm[:len(arm_idx)].copy();sl=slider_lower+args.preset_slider_offset;w=operation.copy();o=initial_obj.copy()
            l=operation@transform(s[47:50],s[50:54])
            l[:3,3]+=o[:3,:3]@np.array([0,0,args.preset_slider_offset+args.preset_object_axis_offset])
        preset_reference=s.copy()
        if args.group=='A' and (args.preset_slider_offset or args.preset_object_axis_offset):
            preset_reference[40:47]=pose(np.linalg.inv(w)@o);preset_reference[47:54]=pose(np.linalg.inv(w)@l)
        policy.takeover(q,targets[hand_idx],w,o,l,slider_lower,reference_state=preset_reference if args.group=='A' else None)
        policy.previous_slider=sl
        rel=pose(np.linalg.inv(w)@o)
        hold_check=acquisition_hold({key:[r[key] for r in records] for key in records[0]},s,table_z) if args.group!='A' else None
        grasp_success=hold_check['success'] if hold_check is not None else True
        takeover=dict(step=global_step,time=global_step*dt,q=q.tolist(),targets=targets[hand_idx].tolist(),
            arm_q=qa.tolist(),object_world=pose(o).tolist(),wrist_world=pose(w).tolist(),object_hand=rel.tolist(),
            grasp_success=grasp_success if args.group!='A' else None,slider_at_takeover=sl,slider_command_origin=slider_lower,
            acquisition_hold_check=hold_check,
            table_height=table_z,
            student_initialization='ideal_simulation_truth_at_takeover' if args.group=='C' else None,
            acquisition_localization='live simulation object truth during seating: '+args.seat_feedback if args.seat_feedback!='none' else 'configured table placement and one-time truth for seating planning',
            acquisition_finger_localization=args.seat_finger_feedback,table_supported_regrasp=bool(table_regrasp),
            additional_acquisition_truth_sources=dict(settled_table_pose=args.table_localization=='settled-truth',air_flip_pivot=bool(args.air_flip),standing_level_samples=4 if args.level_standing_knife else 0,
                measured_release_pose=args.measured_release,functional_reapproach_pose=bool(table_regrasp),
                gravity_closure_orientation=args.gravity_close_before_takeover),
            history_frames=len(policy.history),rnn='zeroed once at takeover',history='actual settled q and zero hold actions',
            force_sensor_enabled=force_sensor_enabled,
            hand_gravity='disabled as frozen training',arm_gravity=args.arm_gravity,
            gravity_in_wrist=(w[:3,:3].T@np.array([0,0,-9.81])).tolist())
        (args.output/'takeover.json').write_text(json.dumps(takeover,indent=2)+'\n')
        if not args.only_grasp and (args.group=='A' or grasp_success):
            for step in range(round(args.seconds/dt)):
                if step>0 or args.group!='A':q,qa,sl,w,o,l=current()
                offset=.04 if (step//150)%2==0 else 0.
                target,action,obs=policy.step(q,w,o,l,sl,offset)
                targets[hand_idx]=target
                tick('operate',action,policy.slider_initial+offset,obs)
        trace={k:np.asarray([r[k] for r in records]) for k in records[0]}
        np.savez_compressed(args.output/'trace.npz',**trace)
        report=score(trace,takeover,args.group)
        report.update(group=args.group,args={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
            teacher_sha256=hashlib.sha256(args.teacher.read_bytes()).hexdigest(),
            student_sha256=hashlib.sha256(args.student.read_bytes()).hexdigest() if args.group=='C' else None,
            model_sha256=model['urdf_sha256'],initial_state_writes='only before first physics step',
            slider_drive_stiffness=0.,object_external_forces=False,object_constraints=False)
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
                              within_10mm=bool((error<.01).all()),within_2mm=bool((error<.002).all())))
    basic=all(e['within_10mm'] for e in endpoints)
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
        strict_2mm=all(e['within_2mm'] for e in endpoints),
        world_drift_max_m=float(drift.max()),world_rotation_max_rad=float(rotation.max()),
        hand_relative_drift_max_m=float(rel_drift.max()),hand_relative_rotation_max_rad=float(rel_rotation.max()),
        stable_world_10mm_025rad=bool((drift<.01).all() and (rotation<.25).all()),
        natural_no_drop=bool((rel_drift<.05).all() and (rel_rotation<1.57).all()),
        below_table=bool((obj[:,2]<table_height).any()),
        whole_success=bool((group=='A' or takeover['grasp_success']) and basic and held.all() and not physical_drop and not acquisition_drop),
        operation_success_given_grasp=bool(basic and held.all() and not physical_drop) if group!='A' else None,
        whole_stable_success=bool((group=='A' or takeover['grasp_success']) and basic and stable and not physical_drop and not acquisition_drop))
    return out


if __name__=='__main__':main()
