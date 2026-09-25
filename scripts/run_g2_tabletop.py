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
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_frozen_policy import FrozenPolicy,pose

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
    parser.add_argument('--seat-feedback',choices=['none','object-truth'],default='none',help='Explicit oracle localization control during seating only; not a deployable estimator.')
    parser.add_argument('--wrist-posture',type=float,help='Redundant arm joint7 target for initial approach/grasp/lift IK only.')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    assert not args.hand_only_diagnostic or args.group=='A'
    cfg=configuration('wuji_acquisition_bridge3_hemisphere',1,
        ['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=True','rl_device=cpu'],train='wujiAcquisitionSAPG')
    (args.output/'frozen-config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    assert cfg.task.env.forceScale==0 and cfg.task.env.actionsMovingAverage==1 and not cfg.task.env.useRelativeControl
    k=G2Kinematics(); model=json.loads((ROOT/'assets/robots/g2_wuji/audit.json').read_text())
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[args.grasp]
    operation=transform([.40,-.30,1.05],(Rotation.from_euler('z',args.operation_yaw,degrees=True)*Rotation.from_euler('y',-90,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
    op_q,op_error=k.solve(operation)
    assert op_error['position_m']<1e-4 and op_error['rotation_rad']<1e-3,op_error
    table_z=.75
    table_obj=transform([.50+args.dx,-.30+args.dy,table_z+.0041],
        (Rotation.from_euler('z',args.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat())
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
    lifted=grasp_pose.copy(); lifted[2,3]+=.20
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
    opened=np.clip(opened,policy.fk.lower,policy.fk.upper)
    initial_hand=s[:20] if args.group=='A' else opened
    arm=op_q if args.group=='A' else high_q
    states=np.zeros(len(names),dtype=gymapi.DofState.dtype)
    states['pos'][hand_idx]=initial_hand;states['pos'][arm_idx]=arm[:len(arm_idx)]
    obj_states=np.zeros(1,dtype=gymapi.DofState.dtype);obj_states['pos'][0]=slider_lower
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
        for c in gym.get_env_rigid_contacts(env):
            if c['lambda']<=1e-6:continue
            pair={int(c['body0']),int(c['body1'])}
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
            slider=sl,goal=goal,wrist=pose(w),object=pose(o),slider_pose=pose(l),
            table_force=contact[table_id].cpu().numpy().copy(),hand_force=contact[hand_bodies].cpu().numpy().copy(),
            observation=np.zeros(138,dtype=np.float32) if obs is None else obs))
        if writer:
            gym.step_graphics(sim);gym.render_all_camera_sensors(sim)
            frame=gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR)
            writer.append_data(np.asarray(frame).reshape(720,960,4)[:,:,:3])
        global_step+=1
        if global_step%150==0:print(json.dumps(dict(step=global_step,phase=phase,slider=sl,object=pose(o)[:3].tolist(),
            arm_error_max_rad=float(np.max(np.abs(qa-targets[arm_idx]))) if len(qa) else 0.,
            finger_table_contacts=finger_table.tolist(),finger_knife_contacts=finger_knife.tolist())),flush=True)
        return q,qa,sl,w,o,l
    try:
        refresh()
        if args.group!='A':
            for _ in range(60):tick('table_settle')
            phases=[('approach',grasp_q,opened,4),('close',grasp_q,closed,3),('lift',lift_q,closed,4)]
            if args.seat_seconds>0:phases.append(('seat',lift_q,functional,args.seat_seconds))
            phases.append(('transport',op_q,functional if args.seat_seconds>0 else closed,5))
            for label,end_arm,end_hand,seconds in phases:
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
                    for i in range(steps):
                        loc=(i+1)/steps*count;segment=min(int(loc),count-1);fraction=loc-segment
                        targets[arm_idx]=arm_path[segment]*(1-fraction)+arm_path[segment+1]*fraction
                        if args.seat_feedback=='object-truth':
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
                            desired=actual_o@relative_pose
                            motor,err=k.solve_near(desired,last_feedback_target,max_step=np.minimum(k.velocity*dt*.8,.15))
                            # Feedback IK is rate-limited, so small transient
                            # tracking error is expected. Do not confuse a
                            # 1 mm residual with a discontinuous arm branch.
                            if err['position_m']>.005 or err['rotation_rad']>.05:raise ValueError('Seating feedback tracking bound exceeded: '+str(err))
                            last_feedback_target=motor.copy()
                            targets[arm_idx]=motor
                            feedback.append(dict(step=global_step,object_observed=pose(actual_o).tolist(),wrist_target=pose(desired).tolist(),ik=err))
                        targets[hand_idx]=hand_path[segment]*(1-fraction)+hand_path[segment+1]*fraction
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
            q=s[:20].copy();qa=arm[:len(arm_idx)].copy();sl=slider_lower;w=operation.copy();o=initial_obj.copy()
            l=operation@transform(s[47:50],s[50:54])
        policy.takeover(q,targets[hand_idx],w,o,l,slider_lower,reference_state=s if args.group=='A' else None)
        policy.previous_slider=sl
        rel=pose(np.linalg.inv(w)@o)
        grasp_success=bool(o[2,3]>.85 and np.linalg.norm(rel[:3]-s[40:43])<.05)
        takeover=dict(step=global_step,time=global_step*dt,q=q.tolist(),targets=targets[hand_idx].tolist(),
            arm_q=qa.tolist(),object_world=pose(o).tolist(),wrist_world=pose(w).tolist(),object_hand=rel.tolist(),
            grasp_success=grasp_success if args.group!='A' else None,slider_at_takeover=sl,slider_command_origin=slider_lower,
            student_initialization='ideal_simulation_truth_at_takeover' if args.group=='C' else None,
            acquisition_localization='live simulation object truth during seating' if args.seat_feedback=='object-truth' else 'configured table placement and one-time truth for seating planning',
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
    out={'grasp_success':takeover['grasp_success'],'operation_steps':int(sel.sum()),
         'table_contact_peak_N':float(np.linalg.norm(trace['table_force'],axis=-1).max()),
         'max_object_height_m':float(trace['object'][:,2].max())}
    lift=np.where(trace['phase']=='lift')[0]
    out['lift_success']=bool(len(lift) and (trace['object'][lift[-15:],2]>.85).all()) if group!='A' else None
    if group!='A':
        out['acquisition_stage_failure']=None if takeover['grasp_success'] else ('not_lifted' if not out['lift_success'] else 'lost_after_lift')
        for phase in ['seat','transport','settle_history']:
            mask=trace['phase']==phase
            if out['lift_success'] and mask.any() and (trace['object'][mask,2]<.80).any():
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
    out.update(slider_travel_m=float(np.ptp(slider)),endpoints=endpoints,basic_10mm=basic,
        completed_cycles=sum(endpoints[i]['within_10mm'] and endpoints[i+1]['within_10mm'] for i in range(0,len(endpoints)-1,2)),
        strict_2mm=all(e['within_2mm'] for e in endpoints),
        world_drift_max_m=float(drift.max()),world_rotation_max_rad=float(rotation.max()),
        hand_relative_drift_max_m=float(rel_drift.max()),hand_relative_rotation_max_rad=float(rel_rotation.max()),
        stable_world_10mm_025rad=bool((drift<.01).all() and (rotation<.25).all()),
        natural_no_drop=bool((rel_drift<.05).all() and (rel_rotation<1.57).all()),
        below_table=bool((obj[:,2]<.75).any()),
        whole_success=bool((group=='A' or takeover['grasp_success']) and basic and (rel_drift<.05).all() and (rel_rotation<1.57).all()),
        operation_success_given_grasp=bool(basic and (rel_drift<.05).all() and (rel_rotation<1.57).all()) if group!='A' else None,
        whole_stable_success=bool((group=='A' or takeover['grasp_success']) and basic and (drift<.01).all() and (rotation<.25).all()))
    return out


if __name__=='__main__':main()
