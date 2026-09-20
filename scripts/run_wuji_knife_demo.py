"""Evaluate free-object Wuji grasps and a contact-driven slider controller.

Only the hand receives position commands. The knife root is free and its slider
has zero drive stiffness. Reports distinguish grasp stability from slider motion.
"""
import argparse
import json
from pathlib import Path

from isaacgym import gymapi, gymtorch
import imageio.v2 as imageio
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image, ImageDraw, ImageFont
import torch
import yaml

from scripts.wuji_kinematics import ROOT, FINGERS, WujiKinematics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=ROOT/'tmp/knife-demo/candidates.npz')
    parser.add_argument('--asset', default='assets/objects/knife_wuji_demo/000/mobility.urdf')
    parser.add_argument('--output', type=Path, default=ROOT/'tmp/knife-demo/hold')
    parser.add_argument('--candidate-index', type=int)
    parser.add_argument('--seconds', type=float, default=4)
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--no-overlay', action='store_true', help='Render the scene without any text')
    parser.add_argument('--trajectory', type=Path, help='NPZ containing time and qpos arrays for one candidate')
    parser.add_argument('--friction', type=float, default=1.5)
    parser.add_argument('--damping', type=float, default=.3)
    parser.add_argument('--gain', type=float, default=1.)
    parser.add_argument('--gpu-pipeline', action='store_true')
    parser.add_argument('--feedback', action='store_true', help='Use measured object pose and slider state for thumb IK')
    parser.add_argument('--depth', type=float, default=.003)
    parser.add_argument('--lead', type=float, default=.004)
    parser.add_argument('--filtered-self-collisions', action='store_true', help='Use the same hand collision groups as wuji_paper')
    parser.add_argument('--dimension-label', default='', help='Show sourced body dimensions in the video')
    parser.add_argument('--camera-position', type=float, nargs=3, default=[.25,.10,.16], help='Camera position in hand-base coordinates')
    parser.add_argument('--camera-target', type=float, nargs=3, default=[.025,0,.085], help='Camera target in hand-base coordinates')
    parser.add_argument('--record-grip', action='store_true', help='Record palm and per-digit handle support, even beyond the fingertip')
    parser.add_argument('--require-fingertip-grip', action='store_true', help='Require sustained four-fingertip support and thumb-side blade direction')
    args = parser.parse_args(argv)
    if args.require_fingertip_grip: args.record_grip = True
    args.output.mkdir(parents=True, exist_ok=True)
    data = np.load(args.candidates)
    ids = np.arange(len(data['qpos'])) if args.candidate_index is None else np.array([args.candidate_index])
    qs, centers = data['qpos'][ids], data['centers'][ids]
    commands = data['targets'][ids] if 'targets' in data else qs
    n = len(qs)
    cfg = yaml.safe_load((ROOT/'isaacgymenvs/cfg/hand/wuji.yaml').read_text())
    rotations = data['rotations'][ids] if 'rotations' in data else np.tile([0,0,0,1], (n,1))
    trajectory = np.load(args.trajectory) if args.trajectory else None
    if args.feedback:
        from scripts.build_wuji_knife_demo import GraspBuilder
        from scripts.refine_wuji_knife_grasp import thumb_contact
        metadata=json.loads((ROOT/args.asset).with_name('parameters.json').read_text())
        builder=GraspBuilder(metadata)
        feedback_q=commands.copy()
    if trajectory is not None:
        trajectory_q = trajectory['qpos']
        if trajectory_q.ndim == 2:
            trajectory_q = trajectory_q[:,None,:]
        trajectory_q = trajectory_q[:,ids,:]
    gym = gymapi.acquire_gym()
    params = gymapi.SimParams()
    params.dt, params.substeps = 1/120, 4
    params.up_axis = gymapi.UP_AXIS_Z
    params.gravity = gymapi.Vec3(0,0,-9.81)
    params.use_gpu_pipeline = args.gpu_pipeline
    params.physx.use_gpu = True
    params.physx.solver_type = 1
    params.physx.num_threads = 4
    params.physx.num_position_iterations = 16
    params.physx.num_velocity_iterations = 4
    params.physx.contact_offset = .002
    params.physx.rest_offset = 0
    params.physx.contact_collection = gymapi.ContactCollection.CC_ALL_SUBSTEPS
    sim = gym.create_sim(0, 0 if args.render else -1, gymapi.SIM_PHYSX, params)
    if sim is None:
        raise RuntimeError('PhysX initialization failed')
    try:
        options = gymapi.AssetOptions()
        options.fix_base_link, options.disable_gravity = True, True
        options.collapse_fixed_joints = False
        options.use_physx_armature = True
        options.thickness = .001
        options.angular_damping = .01
        hand = gym.load_asset(sim, str(ROOT), cfg['asset'], options)
        hand_props = gym.get_asset_dof_properties(hand)
        for key, values in cfg['dof_props'].items():
            hand_props[key][:] = values
        hand_props['driveMode'][:] = gymapi.DOF_MODE_POS
        hand_props['stiffness'] *= args.gain
        hand_props['damping'] *= np.sqrt(args.gain)
        options = gymapi.AssetOptions()
        options.fix_base_link, options.disable_gravity = False, False
        options.collapse_fixed_joints = False
        options.override_com = True
        options.override_inertia = True
        options.thickness = .01
        knife = gym.load_asset(sim, str(ROOT), args.asset, options)
        knife_props = gym.get_asset_dof_properties(knife)
        knife_props['driveMode'][:] = gymapi.DOF_MODE_POS
        knife_props['stiffness'][:] = 0
        knife_props['damping'][:] = args.damping
        knife_props['friction'][:] = .001
        knife_props['armature'][:] = .001
        hand_pose = gymapi.Transform()
        hand_pose.p = gymapi.Vec3(0,0,.5)
        hand_pose.r = gymapi.Quat(.5,-.5,.5,.5)
        hand_r = Rotation.from_quat([.5,-.5,.5,.5])
        object_positions = hand_r.apply(centers) + [0,0,.5]
        object_rotations = (hand_r * Rotation.from_quat(rotations)).as_quat()
        envs, pad_ids, handle_ids, slider_ids = [], [], [], []
        support_ids = []
        camera = None
        for i in range(n):
            env = gym.create_env(sim, gymapi.Vec3(-.3,-.3,0),gymapi.Vec3(.3,.3,1),int(np.ceil(np.sqrt(n))))
            envs.append(env)
            actor = gym.create_actor(env,hand,hand_pose,'hand',i,8)
            gym.set_actor_dof_properties(env,actor,hand_props)
            state = np.zeros(20,dtype=gymapi.DofState.dtype); state['pos'] = qs[i]
            gym.set_actor_dof_states(env,actor,state,gymapi.STATE_ALL)
            shapes = gym.get_actor_rigid_shape_properties(env,actor)
            for shape in shapes:
                shape.friction = 1.0
            if args.filtered_self_collisions:
                names = gym.get_actor_rigid_body_names(env, actor)
                ranges = gym.get_actor_rigid_body_shape_indices(env, actor)
                for name, span in zip(names, ranges):
                    if name == 'hand_r_base_link':
                        mask = sum(1 << (16+i) for i in range(5))
                    else:
                        digit = next(i for i, finger in enumerate(FINGERS) if f'_{finger}_' in name)
                        mask = 1 << (8+digit)
                        if name.endswith(('link1', 'link2')): mask |= 1 << (16+digit)
                    for j in range(span.start, span.start+span.count): shapes[j].filter = mask
            gym.set_actor_rigid_shape_properties(env,actor,shapes)
            pad_ids.append([gym.find_actor_rigid_body_index(env,actor,name,gymapi.DOMAIN_ENV) for name in cfg['force_links']])
            support_ids.append([{gym.find_actor_rigid_body_index(env,actor,name,gymapi.DOMAIN_ENV)
                                 for name in gym.get_actor_rigid_body_names(env,actor)
                                 if (name=='hand_r_base_link' if group=='palm' else f'_{group}_' in name)}
                                for group in ('palm', 'index', 'middle', 'ring', 'pinky')])
            pose = gymapi.Transform()
            pose.p = gymapi.Vec3(*object_positions[i]); pose.r = gymapi.Quat(*object_rotations[i])
            obj = gym.create_actor(env,knife,pose,'object',i,0)
            gym.set_actor_dof_properties(env,obj,knife_props)
            shapes = gym.get_actor_rigid_shape_properties(env,obj)
            for shape in shapes:
                shape.friction = args.friction
                shape.filter = 1
            gym.set_actor_rigid_shape_properties(env,obj,shapes)
            state = np.zeros(1,dtype=gymapi.DofState.dtype)
            if 'slider' in data:
                state['pos'] = data['slider'][ids[i]]
            gym.set_actor_dof_states(env,obj,state,gymapi.STATE_ALL)
            handle_ids.append(gym.find_actor_rigid_body_index(env,obj,'link_0',gymapi.DOMAIN_ENV))
            slider_ids.append(gym.find_actor_rigid_body_index(env,obj,'link_1',gymapi.DOMAIN_ENV))
            if args.render and i == 0:
                cp = gymapi.CameraProperties(); cp.width, cp.height = 960,720
                cp.horizontal_fov = 48
                camera = gym.create_camera_sensor(env,cp)
                # Palm +X faces the camera; knife lies across the four fingers.
                camera_pos = hand_r.apply(args.camera_position)+[0,0,.5]
                camera_target = hand_r.apply(args.camera_target)+[0,0,.5]
                gym.set_camera_location(camera,env,gymapi.Vec3(*camera_pos),gymapi.Vec3(*camera_target))
        gym.prepare_sim(sim)
        dofs = gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim)).view(n,21,2)
        roots = gymtorch.wrap_tensor(gym.acquire_actor_root_state_tensor(sim)).view(n,2,13)
        forces = gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim)).view(n,-1,3)
        targets = torch.zeros((n,21),dtype=torch.float32,device=dofs.device)
        targets[:,:20] = torch.as_tensor(commands,dtype=torch.float32,device=dofs.device)
        records, contacts, frames, grip_records = [], [], [], []
        try:
            overlay_font=ImageFont.truetype('DejaVuSans.ttf',22)
        except OSError:
            overlay_font=ImageFont.load_default()
        max_drift = np.zeros(n)
        limit_violation=np.zeros(n)
        for step in range(int(args.seconds/params.dt)):
            t = step*params.dt
            if trajectory is not None:
                target = np.array([[np.interp(t,trajectory['time'],trajectory_q[:,i,j]) for j in range(20)] for i in range(n)])
                targets[:,:20] = torch.as_tensor(target,dtype=torch.float32,device=dofs.device)
            if args.feedback and step%4==0 and t>=.5:
                states=roots[:,1,:].cpu().numpy()
                slider=dofs[:,-1,0].cpu().numpy()
                goal=.04 if t<6 else 0.
                for i in range(n):
                    center=hand_r.inv().apply(states[i,:3]-[0,0,.5])
                    rotation=(hand_r.inv()*Rotation.from_quat(states[i,3:7])).as_matrix()
                    s=slider[i]+np.clip(goal-slider[i],-args.lead,args.lead)
                    feedback_q[i],_=thumb_contact(builder,feedback_q[i],center,rotation,s,args.depth)
                targets[:,:20]=torch.as_tensor(feedback_q,dtype=torch.float32,device=dofs.device)
            gym.set_dof_position_target_tensor(sim,gymtorch.unwrap_tensor(targets))
            gym.simulate(sim); gym.fetch_results(sim,True)
            gym.refresh_dof_state_tensor(sim)
            gym.refresh_actor_root_state_tensor(sim)
            gym.refresh_net_contact_force_tensor(sim)
            if not torch.isfinite(dofs).all() or not torch.isfinite(roots).all():
                raise RuntimeError(f'Non-finite simulation at step {step}')
            root = roots[:,1,:].cpu().numpy().copy()
            # Isaac Gym actor-root tensors use each environment's local frame.
            drift = np.linalg.norm(root[:,:3]-object_positions,axis=1)
            max_drift = np.maximum(max_drift,drift)
            hand_q=dofs[:,:20,0].cpu().numpy()
            violation=np.maximum(hand_props['lower']-hand_q,hand_q-hand_props['upper']).max(1)
            limit_violation=np.maximum(limit_violation,violation)
            if step % 12 == 0:
                pair_contacts = np.zeros((n,5),dtype=bool)
                support_contacts = np.zeros((n,5),dtype=bool)
                if not args.gpu_pipeline:
                    for e,env in enumerate(envs):
                        for contact in gym.get_env_rigid_contacts(env):
                            if contact['lambda'] <= 1e-6: continue
                            pair = {int(contact['body0']),int(contact['body1'])}
                            for f,pad in enumerate(pad_ids[e]):
                                if pair == {pad, slider_ids[e] if f==0 else handle_ids[e]}:
                                    pair_contacts[e,f] = True
                            if args.record_grip and handle_ids[e] in pair:
                                for g, bodies in enumerate(support_ids[e]):
                                    support_contacts[e,g] |= bool((pair-{handle_ids[e]}) & bodies)
                else:
                    for e in range(n):
                        pair_contacts[e] = (torch.linalg.norm(forces[e,pad_ids[e]],dim=-1)>.05).cpu().numpy()
                contacts.append(pair_contacts)
                grip_records.append(support_contacts)
                records.append(np.concatenate([np.full((n,1),t),root,dofs[:,:,0].cpu().numpy()],axis=1))
            if camera is not None and step % 4 == 0:
                gym.step_graphics(sim); gym.render_all_camera_sensors(sim)
                frame = np.asarray(gym.get_camera_image(sim,envs[0],camera,gymapi.IMAGE_COLOR)).reshape(720,960,4)
                rgb = frame[:,:,:3].copy()
                if not args.no_overlay:
                    canvas=Image.fromarray(rgb);draw=ImageDraw.Draw(canvas)
                    font=overlay_font
                    draw.text((24,22),'Wuji | Contact-driven utility knife',font=font,fill='white',stroke_width=2,stroke_fill='black')
                    draw.text((24,56),f't = {t:4.1f} s     slider = {float(dofs[0,-1,0])*1000:5.1f} mm',font=font,fill='white',stroke_width=2,stroke_fill='black')
                    if args.dimension_label:
                        draw.text((24,90),args.dimension_label,font=font,fill='white',stroke_width=2,stroke_fill='black')
                    draw.text((24,665),'Scripted hand control | Free handle | Passive slider',font=font,fill='white',stroke_width=2,stroke_fill='black')
                    rgb = np.asarray(canvas)
                frames.append(rgb)
        records = np.stack(records); contacts = np.stack(contacts)
        grip_records = np.stack(grip_records)
        drift = np.linalg.norm(records[-1,:,:3+1][:,1:4]-object_positions,axis=1)
        angle = (Rotation.from_quat(records[-1,:,4:8])*Rotation.from_quat(object_rotations).inv()).magnitude()
        fraction = contacts[len(contacts)//2:].mean(0)
        reports=[]
        for i in range(n):
            reports.append(dict(candidate=int(ids[i]),final_drift_m=float(drift[i]),max_drift_m=float(max_drift[i]),
                                final_rotation_rad=float(angle[i]),contact_fraction=fraction[i].tolist(),
                                slider_min_m=float(records[:,:, -1][:,i].min()),slider_max_m=float(records[:,:,-1][:,i].max()),
                                score=float(drift[i]+angle[i]*.01-.002*fraction[i].sum())))
            reports[-1]['max_joint_limit_violation_rad']=float(limit_violation[i])
            if args.record_grip:
                reports[-1]['handle_support_fraction_palm_index_middle_ring_pinky'] = grip_records[len(grip_records)//2:,i].mean(0).tolist()
                blade_world = Rotation.from_quat(records[:,i,4:8]).apply([0,-1,0])
                reports[-1]['minimum_blade_direction_toward_thumb'] = float(hand_r.inv().apply(blade_world)[:,1].min())
            if trajectory is not None or args.feedback:
                extend = float(records[(records[:,i,0]>=4)&(records[:,i,0]<6),i,-1].max())
                retract = float(records[-1,i,-1])
                reports[-1].update(extension_m=extend,retraction_m=retract,
                                   cycle_pass=bool(extend>=.035 and retract<=.005 and max_drift[i]<=.015))
                cycles=[]
                for start in range(0,int(args.seconds)-11,12):
                    mask=(records[:,i,0]>=start+4)&(records[:,i,0]<start+6)
                    endmask=(records[:,i,0]>=start+10)&(records[:,i,0]<start+12)
                    extension=float(records[mask,i,-1].max())
                    retraction=float(records[endmask,i,-1][-1])
                    cycles.append(dict(extension_m=extension,retraction_m=retraction,
                                       passed=bool(extension>=.035 and retraction<=.005 and max_drift[i]<=.015)))
                reports[-1]['cycles']=cycles
                reports[-1]['all_cycles_pass']=all(c['passed'] for c in cycles) and bool(cycles)
                if args.require_fingertip_grip:
                    grip_ok = min(fraction[i,1:])>.7 and reports[-1]['minimum_blade_direction_toward_thumb']>.7
                    reports[-1]['fingertip_grip_pass'] = bool(grip_ok)
                    reports[-1]['all_cycles_pass'] &= bool(grip_ok)
        reports.sort(key=lambda r:r['score'])
        np.savez(args.output/'rollout.npz',states=records,contacts=contacts,candidate_ids=ids,handle_support=grip_records)
        report=dict(settings=vars(args),ranked=reports,
                    object_fixed_base=False,slider_drive_stiffness=0.0,
                    contact_measurement='net_force_only' if args.gpu_pipeline else 'rigid_body_pairs')
        (args.output/'report.json').write_text(json.dumps(report,indent=2,default=str))
        if frames:
            imageio.imwrite(args.output/'demo.png',frames[len(frames)//2])
            imageio.mimwrite(args.output/'demo.mp4',frames,fps=30)
        print(json.dumps(reports[:10],indent=2))
    finally:
        gym.destroy_sim(sim)


if __name__ == '__main__':
    main()
