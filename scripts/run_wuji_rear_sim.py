"""Fixed wrist deployment entry: physical placement tray, withdrawal, fresh history, shared control.
No knife state writes after the initial placement; temporary support is explicitly withdrawn.
"""
import argparse,json,time,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from isaacgym import gymapi,gymtorch
import numpy as np
import torch
from scipy.spatial.transform import Rotation
from scripts.wuji_rear_controller import RearController,load_bundle,ROOT
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.record_wuji_rear_event import record

def gt(t):
    p=gymapi.Transform();p.p=gymapi.Vec3(*t[:3,3]);p.r=gymapi.Quat(*Rotation.from_matrix(t[:3,:3]).as_quat());return p
def smooth(u):
    u=np.clip(u,0,1);return u**3*(10-15*u+6*u*u)
def main(a):
    out=a.output;out.mkdir(parents=True,exist_ok=False)
    spec=load_bundle(a.bundle);record('rear_sim_started',[out],dict(args=vars(a),bundle_sha256=hashlib.sha256(a.bundle.read_bytes()).hexdigest(),source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['scripts/run_wuji_rear_sim.py','scripts/wuji_rear_controller.py','scripts/wuji_rear_diagnostics.py']},initialization='Explicit physical placement tray; no loaded state/history restored'))
    c=RearController(spec,pressure_enabled=not a.pressure_off and a.operation!='response',estimate_delta_m=a.estimate_delta,operation=a.operation);cfg=c.cfg;kin=G2Kinematics()
    wrist=kin.forward(np.array(spec['arm_q_rad']));rel=np.array(spec['placement_object_in_wrist']);object0=wrist@rel
    delta=object0[:3,:3]@np.asarray(a.pose_delta);object0[:3,3]+=delta
    object0[:3,:3]=object0[:3,:3]@Rotation.from_rotvec(np.radians(a.pose_rotation)).as_matrix()
    gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2;sp.physx.contact_offset=.001;sp.physx.rest_offset=0;sp.physx.max_depenetration_velocity=1.;sp.physx.num_threads=4
    sim=gym.create_sim(0,0 if a.video else -1,gymapi.SIM_PHYSX,sp);assert sim
    plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);gym.add_ground(sim,plane);env=gym.create_env(sim,gymapi.Vec3(-1,-1,0),gymapi.Vec3(1,1,2),1)
    opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=False;opt.collapse_fixed_joints=False;opt.thickness=.001;opt.use_physx_armature=True
    asset=gym.load_asset(sim,str(ROOT),'assets/robots/g2_wuji/g2_wuji.urdf',opt);robot=gym.create_actor(env,asset,gymapi.Transform(),'robot',0,0)
    names=gym.get_actor_dof_names(env,robot);hand=np.array([names.index(n) for n in spec['runtime_joint_names']]);arm=np.array([names.index(n) for n in kin.names]);rbnames=gym.get_actor_rigid_body_names(env,robot)
    props=gym.get_actor_dof_properties(env,robot);kp=np.zeros(27);kd=np.zeros(27);armcfg=json.loads((ROOT/'assets/robots/g2_wuji/audit.json').read_text())['active_arm']
    kp[arm]=[j['stiffness'] for j in armcfg];kd[arm]=[j['damping'] for j in armcfg]
    kp[hand]=np.asarray(cfg.hand.dof_props.stiffness)*a.stiffness_scale;kd[hand]=np.asarray(cfg.hand.dof_props.damping)*a.damping_scale
    for key in ['armature','friction']:props[key][hand]=np.asarray(cfg.hand.dof_props[key])*(a.joint_friction_scale if key=='friction' else 1.)
    props['armature'][arm]=.01;props['driveMode'][:]=gymapi.DOF_MODE_EFFORT;props['stiffness'][:]=0;props['damping'][:]=0;gym.set_actor_dof_properties(env,robot,props)
    shapes=gym.get_actor_rigid_shape_properties(env,robot);indices=gym.get_actor_rigid_body_shape_indices(env,robot);digits=['thumb','index','middle','ring','pinky'];allbits=sum(1<<(8+i) for i in range(5))+sum(1<<(16+i) for i in range(5))
    for name,idx in zip(rbnames,indices):
        if not name.startswith('hand_r_'):mask=(1<<7)|allbits
        elif name=='hand_r_base_link':mask=sum(1<<(16+i) for i in range(5))
        else:
            digit=next(i for i,d in enumerate(digits) if '_'+d+'_' in name);mask=1<<(8+digit)
            if name.endswith(('link1','link2')):mask|=1<<(16+digit)
        for n in range(idx.start,idx.start+idx.count):shapes[n].filter=mask;shapes[n].friction=a.hand_friction
    gym.set_actor_rigid_shape_properties(env,robot,shapes)
    opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;opt.density=1000
    path=ROOT/spec['asset'];ka=gym.load_asset(sim,str(path.parent),path.name,opt);knife=gym.create_actor(env,ka,gt(object0),'knife',0,0)
    bodies=gym.get_actor_rigid_body_properties(env,knife);xml=ET.parse(path)
    for b,name in zip(bodies,gym.get_actor_rigid_body_names(env,knife)):
        node=xml.find("./link[@name='%s']/inertial"%name);b.mass=float(node.find('mass').get('value'));v=node.find('inertia');b.inertia.x.x=float(v.get('ixx'));b.inertia.y.y=float(v.get('iyy'));b.inertia.z.z=float(v.get('izz'))
    gym.set_actor_rigid_body_properties(env,knife,bodies,False);shapes=gym.get_actor_rigid_shape_properties(env,knife)
    for s in shapes:s.friction=a.knife_friction;s.filter=1
    gym.set_actor_rigid_shape_properties(env,knife,shapes)
    op=gym.get_actor_dof_properties(env,knife);op['driveMode'][:]=gymapi.DOF_MODE_VEL;op['stiffness'][:]=0;op['damping'][:]=25000.;op['friction'][:]=0;op['armature'][:]=.001;op['effort'][:]=a.load;gym.set_actor_dof_properties(env,knife,op);gym.set_actor_dof_velocity_targets(env,knife,np.zeros(len(op),np.float32))
    # Physical tray touches the lowest housing corner; only knife/tray collision.
    corners=np.array([[x,y,z] for x in [-.0095,.0095] for y in [-.004,.004] for z in [-.072,.072]])
    lowest=float((corners@object0[:3,:3].T+object0[:3,3])[:,2].min())
    opt=gymapi.AssetOptions();opt.fix_base_link=True;trayasset=gym.create_box(sim,.20,.20,.006,opt);tray=gym.create_actor(env,trayasset,gt(transform([*object0[:2,3],lowest-.0031])),'manual_placement_tray',0,0)
    shapes=gym.get_actor_rigid_shape_properties(env,tray)
    for s in shapes:s.filter=allbits|(1<<7);s.friction=.8
    gym.set_actor_rigid_shape_properties(env,tray,shapes)
    ds=np.zeros(27,dtype=gymapi.DofState.dtype);ds['pos'][arm]=spec['arm_q_rad'];ds['pos'][hand]=spec['open_q_rad'];os=np.zeros(1,dtype=gymapi.DofState.dtype);os['pos'][0]=spec['placement_slider_q_m']+a.slider_delta
    gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL)
    writers=[];cams=[]
    if a.video:
        import imageio.v2 as imageio
        for label,offset,fov in [('overall',np.array([.85,-.9,.6]),70),('closeup',np.array([.23,-.20,.17]),40)]:
            cp=gymapi.CameraProperties();cp.width=960;cp.height=720;cp.horizontal_fov=fov;cam=gym.create_camera_sensor(env,cp);aim=object0[:3,3]+np.array([0,0,.02]);gym.set_camera_location(cam,env,gymapi.Vec3(*(aim+offset)),gymapi.Vec3(*aim));cams.append(cam);writers.append(imageio.get_writer(str(out/(label+'.mp4')),fps=30,codec='libx264',quality=7))
    gym.prepare_sim(sim);gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL)
    dof=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));jac=gymtorch.wrap_tensor(gym.acquire_jacobian_tensor(sim,'robot'));masses=torch.tensor([b.mass for b in gym.get_actor_rigid_body_properties(env,robot)][1:])
    oid=gym.get_actor_rigid_body_index(env,knife,0,gymapi.DOMAIN_SIM);sid=gym.get_actor_dof_index(env,knife,0,gymapi.DOMAIN_SIM)
    K=torch.tensor(kp,dtype=torch.float32);C=torch.tensor(kd,dtype=torch.float32);limits=torch.tensor(props['effort'].copy());target=torch.tensor(ds['pos'].copy());force=torch.zeros(len(dof));queue=[];rows=[];commands=[];released=False;begin=time.monotonic()
    c.seed_issued(np.asarray(spec['open_q_rad']));c.response_anchor=np.asarray(spec['hold_target_rad']);push_start=spec['release_seconds']+spec['settle_seconds'];total=push_start+(a.response_seconds+2 if a.operation=='response' else spec['push_seconds']);contact_names={}
    for actor in [robot,knife,tray]:
        for n,name in enumerate(gym.get_actor_rigid_body_names(env,actor)):contact_names[gym.get_actor_rigid_body_index(env,actor,n,gymapi.DOMAIN_ENV)]=name
    f=(out/'commands.jsonl').open('w');pairs=(out/'contacts.jsonl').open('w');rng=np.random.default_rng(20261009)
    try:
        for step in range(round(total*240)):
            gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_jacobian_tensors(sim);t=step/240
            if not released and t>=spec['release_seconds']:
                roots=gym.get_actor_rigid_body_states(env,tray,gymapi.STATE_ALL);roots['pose']['p']['z'][:]=-1;gym.set_actor_rigid_body_states(env,tray,roots,gymapi.STATE_POS);released=True
            if step%8==0:
                if a.operation=='response' and abs(t-push_start)<1e-6:c.response_anchor=c.issued.copy()
                loop_begin=time.perf_counter();q=dof[hand,0].numpy().copy()+rng.normal(0,a.observation_noise,20);c.observe(q)
                if t<spec['prepare_seconds']:
                    raw=c.propose_hold(np.asarray(spec['open_q_rad'])+smooth(t/spec['prepare_seconds'])*(np.asarray(spec['hold_target_rad'])-np.asarray(spec['open_q_rad'])))
                elif t<push_start:
                    warm_at=spec['release_seconds']+spec.get('prewarm_after_release_seconds',spec['settle_seconds']-.1)
                    if a.operation!='response' and t>=warm_at and not c.taken:c.takeover(q)
                    raw=c.propose_hold(spec['hold_target_rad'])
                elif a.operation=='response':
                    from scripts.wuji_rear_diagnostics import local_response_target
                    raw=c.propose_hold(local_response_target(c.response_anchor,a.joint,a.step_rad,t-push_start,a.response_seconds))
                else:raw=c.propose_push(q,t-push_start)
                sent=c.constrain(raw);c.commit(sent);target[hand]=torch.tensor(sent,dtype=torch.float32)
                queue.append(target.clone());physical_target=queue[max(0,len(queue)-1-a.delay_frames)]
                row=dict(time_s=t,phase='approach_placement' if t<3 else 'independent_hold_history' if t<push_start else 'loaded_local_response' if a.operation=='response' else 'probe_hold' if a.operation=='probe' else 'push_hold',measured_q_rad=q.tolist(),raw_target_rad=raw.tolist(),issued_target_rad=sent.tolist(),applied_delayed_target_rad=physical_target[hand].tolist(),executed_action=c.last_action.tolist(),history_frames=len(c.policy.history),loop_ms=(time.perf_counter()-loop_begin)*1000,pressure_proxy_N=c.policy.pressure_adapter.last_estimate if c.policy.pressure_adapter else None);commands.append(row);f.write(json.dumps(row)+'\n')
            gravity_ff=(jac[0,:,2,:]*masses[:,None]*9.81).sum(0);torque=K*(physical_target-dof[:27,0])-C*dof[:27,1]+gravity_ff;force[:27]=torch.maximum(torch.minimum(torque,limits),-limits);force[sid]=0.
            # Only passive zero-velocity capacity; local bump is a dissipative cap.
            capacity=a.load
            if a.local_peak and .009<float(dof[sid,0])<.012:capacity*=1.4
            op['effort'][0]=capacity;gym.set_actor_dof_properties(env,knife,op)
            gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(force));gym.simulate(sim);gym.fetch_results(sim,True)
            if step%8==7:
                gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);support=False;thumb=False;traycontact=False;normal=0.
                for ct in gym.get_env_rigid_contacts(env):
                    a0=contact_names.get(int(ct['body0']),'ground');a1=contact_names.get(int(ct['body1']),'ground');pair=[a0,a1]
                    if not ('link_0' in pair or 'link_1' in pair) or ct['lambda']<=1e-6:continue
                    thumb|='link_1' in pair and any('_thumb_' in n for n in pair)
                    support|='link_0' in pair and any('hand_r_' in n and '_thumb_' not in n for n in pair)
                    traycontact|='manual_placement_tray' in pair
                    if 'link_1' in pair and any('_thumb_' in n for n in pair):normal+=float(ct['lambda'])
                    pairs.write(json.dumps(dict(time_s=t+1/240,body0=a0,body1=a1,normal_solver_N=float(ct['lambda']),local_point0_m=[float(ct['localPos0'][k]) for k in ['x','y','z']],local_point1_m=[float(ct['localPos1'][k]) for k in ['x','y','z']],normal_world=[float(ct['normal'][k]) for k in ['x','y','z']]))+'\n')
                rows.append(dict(time=t+1/240,q=dof[hand,0].numpy().copy(),q_velocity=dof[hand,1].numpy().copy(),object=rb[oid].numpy().copy(),slider=float(dof[sid,0]),target=sent.copy(),raw=raw.copy(),torque=force[:27].numpy().copy()[hand],saturated=(np.abs(torque.numpy()[hand])>=limits.numpy()[hand]),thumb=thumb,support=support,traycontact=traycontact,normal_solver_N=normal,capacity_N=capacity,arm_q=dof[arm,0].numpy().copy()))
                if writers:
                    gym.step_graphics(sim);gym.render_all_camera_sensors(sim)
                    for cam,writer in zip(cams,writers):writer.append_data(np.asarray(gym.get_camera_image(sim,env,cam,gymapi.IMAGE_COLOR),np.uint8).reshape(720,960,4)[...,:3])
            if step%240==0:print(json.dumps(dict(t=t,z=float(rb[oid,2]),slider=float(dof[sid,0]))),flush=True)
        trace={k:np.asarray([x[k] for x in rows]) for k in rows[0]};np.savez_compressed(out/'trace.npz',**trace)
        from scripts.evaluate_wuji_rear import evaluate,evaluate_diagnostic
        result=evaluate(trace,spec,push_start) if a.operation=='push' else evaluate_diagnostic(trace,spec,push_start,a.operation);result.update(bundle_sha256=hashlib.sha256(a.bundle.read_bytes()).hexdigest(),source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['scripts/run_wuji_rear_sim.py','scripts/wuji_rear_controller.py','scripts/wuji_rear_diagnostics.py']},controller=c.summary(),wall_seconds=time.monotonic()-begin,config=vars(a),physics=dict(physics_hz=240,policy_hz=30,actual_kp_rad=kp[hand].tolist(),controller_kp_nominal=np.asarray(cfg.hand.dof_props.stiffness).tolist(),gravity_enabled=True,object_fixture_after_release=False,rail_drive='zero-velocity passive brake only',actual_axial_contact_force_N=None),real_robot_ran=False)
        loops=np.array([r['loop_ms'] for r in commands]);result['loop_ms']=dict(p50=float(np.median(loops)),p95=float(np.quantile(loops,.95)),max=float(loops.max()),over33ms=int((loops>1000/30).sum()),scope='Simulation read/control/commit/log preparation; no USB, warmup included separately in max')
        (out/'result.json').write_text(json.dumps(result,default=str,indent=2));print(json.dumps(result,default=str),flush=True);record('rear_sim_terminal',[out/'result.json',out/'trace.npz'],dict(passed=result['passed'],active_displacement_mm=result['active_displacement_mm']),next_step='Inspect first failure and fix startup/interface before training' if not result['passed'] else 'Short targeted tolerance/model checks, then hardware materials')
    except Exception as e:
        record('rear_sim_failed',[out],dict(error=repr(e)));raise
    finally:
        f.close();pairs.close()
        for writer in writers:writer.close()
        gym.destroy_sim(sim)

def parser():
    p=argparse.ArgumentParser();p.add_argument('--operation',choices=['push','probe','response'],default='push');p.add_argument('--joint',type=int,default=17);p.add_argument('--step-rad',type=float,default=.01);p.add_argument('--response-seconds',type=float,default=2.);p.add_argument('--bundle',type=Path,default=Path('research/rear-sim2real-20261009/bundle-deploy-v7.json'));p.add_argument('--output',type=Path,required=True);p.add_argument('--video',action='store_true');p.add_argument('--load',type=float,default=.73549875);p.add_argument('--pose-delta',type=float,nargs=3,default=[0,0,0]);p.add_argument('--pose-rotation',type=float,nargs=3,default=[0,0,0]);p.add_argument('--estimate-delta',type=float,nargs=3,default=[0,0,0]);p.add_argument('--slider-delta',type=float,default=0.);p.add_argument('--stiffness-scale',type=float,default=1.);p.add_argument('--damping-scale',type=float,default=1.);p.add_argument('--joint-friction-scale',type=float,default=1.);p.add_argument('--delay-frames',type=int,default=0);p.add_argument('--hand-friction',type=float,default=.8);p.add_argument('--knife-friction',type=float,default=1.8);p.add_argument('--observation-noise',type=float,default=0.);p.add_argument('--local-peak',action='store_true');p.add_argument('--pressure-off',action='store_true');return p
if __name__=='__main__':main(parser().parse_args())
