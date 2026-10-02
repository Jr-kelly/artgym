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
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--video',action='store_true');p.add_argument('--seconds',type=float,default=36);p.add_argument('--table-height',type=float,default=.75);p.add_argument('--dx',type=float,default=0);p.add_argument('--dy',type=float,default=0);p.add_argument('--yaw',type=float,default=0);p.add_argument('--close-height',type=float,default=0);p.add_argument('--load',type=float,default=0);p.add_argument('--grasp-plan',type=Path);p.add_argument('--slider-face',choices=['up','down'],default='up');p.add_argument('--arm-seed',type=Path);p.add_argument('--grasp-only',action='store_true');p.add_argument('--handover-calibration',type=Path,help='Fixed prior/offline hand-object calibration, loaded once before episode; no live object or slider truth');p.add_argument('--table-calibration',type=Path);p.add_argument('--cartesian-path',type=Path);p.add_argument('--acquisition-path',type=Path);p.add_argument('--thumb-action-gain',type=float,default=1.);p.add_argument('--support-action-gain',type=float,default=1.);p.add_argument('--residual-checkpoint',type=Path);p.add_argument('--detent',type=float,default=0.);p.add_argument('--variable-load',action='store_true');p.add_argument('--thumb-script',type=Path,help='Offline calibrated thumb joint path with scheduled commands and original legal action memory; no live slider/contact feedback');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
 policy=G2R800Policy(cfg,R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,residual_checkpoint=a.residual_checkpoint);kin=G2Kinematics()
 seed=np.load(R/'research/robust-knife-family-20261003/data/repaired-seeds.npy')[1];relative=transform(seed[40:43],seed[43:47]);closed=seed[20:40].copy();opened=np.clip(closed*.30,policy.fk.lower,policy.fk.upper);opened[16:]=np.clip(closed[16:]-[.35,0,.25,0],policy.fk.lower[16:],policy.fk.upper[16:])
 if a.grasp_plan:
  plan=json.loads(a.grasp_plan.read_text());relative=np.linalg.inv(np.asarray(plan['wrist_in_knife']));closed=np.asarray(plan['close_q']);opened=np.asarray(plan['open_q'])
 thumb_script=None
 if a.thumb_script:
  assert a.grasp_plan and not a.residual_checkpoint
  thumb_script=json.loads(a.thumb_script.read_text());script_shifts=np.array([r['shift_m'] for r in thumb_script['rows']]);script_q=np.array([r['q_thumb'] for r in thumb_script['rows']]);assert np.isclose(script_shifts[0],0) and np.isclose(script_shifts[-1],.04)
  script_preload=closed[16:]-np.asarray(plan['touch_q'])[16:];script_travel_seconds=float(thumb_script.get('travel_seconds',3.));assert 0<script_travel_seconds<5.
 policy_relative=relative.copy();policy_slider_estimate=None;handover_calibration=None
 if a.handover_calibration:
  handover_calibration=json.loads(a.handover_calibration.read_text());policy_relative=np.asarray(handover_calibration['object_in_wrist']);policy_slider_estimate=np.asarray(handover_calibration['slider_in_wrist']);assert policy_relative.shape==(4,4) and policy_slider_estimate.shape==(4,4)
 def close_motor(u):
  if not a.grasp_plan or 'close_waypoints' not in plan:return opened+smooth(u)*(closed-opened)
  way=plan['close_waypoints']
  for first,last in zip(way[:-1],way[1:]):
   if u<=last['fraction']:
    alpha=smooth((u-first['fraction'])/(last['fraction']-first['fraction']));return np.asarray(first['q'])*(1-alpha)+np.asarray(last['q'])*alpha
  return closed
 knife0=transform([.50+a.dx,-.30+a.dy,a.table_height+.0061],(Rotation.from_euler('z',a.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());
 if a.slider_face=='down':knife0=knife0@transform(quaternion=Rotation.from_euler('z',180,degrees=True).as_quat())
 # Model envelope placement occurs only before the episode starts.
 if a.slider_face=='down':knife0[2,3]=a.table_height+.0091
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
 (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True));(a.output/'plan.json').write_text(json.dumps(dict(args=vars(a),arm_above=qabove.tolist(),arm_grasp=qgrasp.tolist(),arm_lift=qlift.tolist(),ik=[e1,e2,e3],platform='G2+Wuji v1',object_initial=knife0.tolist(),relative_grasp=relative.tolist(),policy_relative_estimate=policy_relative.tolist(),handover_calibration=handover_calibration,open_q=opened.tolist(),close_q=closed.tolist(),schedule='0-2settle,2-5approach,5-8close,8-12lift,12-16hold/history,16-36R800 external5sopen/close',handover='Once-loaded offline hand-object geometry estimate; no live object truth fed to policy. Measured q/FK, actual command history; no state reset.'),default=str,indent=2))
 assert max(e['position_m'] for e in [e1,e2,e3])<.005,(e1,e2,e3)
 gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.substeps=1;sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81);sp.use_gpu_pipeline=False;sp.physx.use_gpu=True;sp.physx.solver_type=1;sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2;sp.physx.contact_offset=.001;sp.physx.rest_offset=0;sp.physx.max_depenetration_velocity=1.;sp.physx.num_threads=4
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
  for n in range(idx.start,idx.start+idx.count):shapes[n].filter=mask;shapes[n].friction=1.
 gym.set_actor_rigid_shape_properties(env,robot,shapes)
 opt=gymapi.AssetOptions();opt.fix_base_link=True;tableasset=gym.create_box(sim,.60,.80,.05,opt);table=gym.create_actor(env,tableasset,gt(transform([.60,-.25,a.table_height-.025])),'table',0,0)
 opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False;opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;opt.density=1000;knifeasset=gym.load_asset(sim,str(R),'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf',opt);knife=gym.create_actor(env,knifeasset,gt(knife0),'knife',0,0);bodies=gym.get_actor_rigid_body_properties(env,knife);knife_xml=ET.parse(R/'assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf')
 for b,name in zip(bodies,['link_0','link_1']):
  node=knife_xml.find(f"./link[@name='{name}']/inertial");b.mass=float(node.find('mass').get('value'));v=node.find('inertia');b.inertia.x.x=float(v.get('ixx'));b.inertia.y.y=float(v.get('iyy'));b.inertia.z.z=float(v.get('izz'))
 gym.set_actor_rigid_body_properties(env,knife,bodies,False);shapes=gym.get_actor_rigid_shape_properties(env,knife)
 for s in shapes:s.friction=3.;s.filter=1
 gym.set_actor_rigid_shape_properties(env,knife,shapes);op=gym.get_actor_dof_properties(env,knife);lower=float(op['lower'][0]);op['driveMode'][:]=gymapi.DOF_MODE_EFFORT;op['stiffness'][:]=0;op['damping'][:]=.3;op['friction'][:]=.001;op['armature'][:]=.001;gym.set_actor_dof_properties(env,knife,op)
 ds=np.zeros(27,dtype=gymapi.DofState.dtype);ds['pos'][arm]=qabove;ds['pos'][hand]=opened;gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);os=np.zeros(1,dtype=gymapi.DofState.dtype);os['pos'][0]=lower;gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL)
 cam=None;writer=None
 if a.video:
  import imageio.v2 as imageio
  cp=gymapi.CameraProperties();cp.width=960;cp.height=720;cam=gym.create_camera_sensor(env,cp);gym.set_camera_location(cam,env,gymapi.Vec3(1.25,-1.4,1.5),gymapi.Vec3(.4,-.3,.85));cp2=gymapi.CameraProperties();cp2.width=960;cp2.height=720;cp2.horizontal_fov=40;closecam=gym.create_camera_sensor(env,cp2);gym.set_camera_location(closecam,env,gymapi.Vec3(.82,-.8,1.1),gymapi.Vec3(.5,-.3,.84));closewriter=imageio.get_writer(str(a.output/'hand-closeup.mp4'),fps=30,codec='libx264',quality=7);writer=imageio.get_writer(str(a.output/'continuous.mp4'),fps=30,codec='libx264',quality=7)
 gym.prepare_sim(sim);gym.set_actor_dof_states(env,robot,ds,gymapi.STATE_ALL);gym.set_actor_dof_states(env,knife,os,gymapi.STATE_ALL);dof=gymtorch.wrap_tensor(gym.acquire_dof_state_tensor(sim));rb=gymtorch.wrap_tensor(gym.acquire_rigid_body_state_tensor(sim));contact=gymtorch.wrap_tensor(gym.acquire_net_contact_force_tensor(sim));jac=gymtorch.wrap_tensor(gym.acquire_jacobian_tensor(sim,'robot'));oid=gym.get_actor_rigid_body_index(env,knife,0,gymapi.DOMAIN_SIM);sid=gym.get_actor_dof_index(env,knife,0,gymapi.DOMAIN_SIM);robotb=gym.get_actor_rigid_body_properties(env,robot);masses=torch.tensor([b.mass for b in robotb][1:]);force=torch.zeros(len(dof));target=torch.tensor(ds['pos'].copy());K=torch.tensor(kp,dtype=torch.float32);C=torch.tensor(kd,dtype=torch.float32);limits=torch.tensor(props['effort'].copy());limitlow=torch.tensor(props['lower'].copy());limithi=torch.tensor(props['upper'].copy());rows=[];started=time.monotonic();taken=False;operation_reference=None;max_positive_power=0.
 (a.output/'physics.json').write_text(json.dumps(dict(robot_dof_names=names,hand_indices=hand.tolist(),arm_indices=arm.tolist(),kp=kp.tolist(),kd=kd.tolist(),effort=limits.tolist(),mass_kg=[b.mass for b in robotb],gravity='All bodies enabled; model-based robot generalized gravity compensation via arm/hand motor efforts; total torque clipped to URDF limits',controller='Explicit finite-torque PD240Hz; original hand gains retained; deployment actuator timing assumption',object='Free floating, no drive; original passive joint damping/friction plus optional opposing load',initial_state_writes_only=True,platform='G2+Wuji v1',policy_inputs='q,FK,50 actual q/action frames, issued targets and known scheduled command, once-loaded relative grip calibration; no live object/slider/contact truth'),indent=2))
 # Reuse the existing G2 contact-pair evaluation API. These values never enter control.
 from scripts.wuji_kinematics import FINGERS
 contact_names={}
 for actor in [robot,table,knife]:
  for n,name in enumerate(gym.get_actor_rigid_body_names(env,actor)):
   contact_names[gym.get_actor_rigid_body_index(env,actor,n,gymapi.DOMAIN_ENV)]=('table' if actor==table else name)
 pair_stream=(a.output/'knife-contact-pairs.jsonl').open('w')
 (a.output/'contact-schema.json').write_text(json.dumps(dict(sample_hz=30,scope='Evaluation-only solver contacts; no policy/controller input',magnitude='RigidContact.lambda documented as contact force magnitude by installed IsaacGym Preview4; simulated solver quantity, not a measured hardware force',normal='World direction body0 to body1',digits=list(FINGERS),force_note='Normal solver contribution only; friction direction/total tangential force not inferred; position-target preload is not constant force'),indent=2))
 def pair_diagnostics(t):
  body_count=np.zeros(5,np.int32);slider_count=np.zeros(5,np.int32);body_magnitude=np.zeros(5);slider_magnitude=np.zeros(5)
  for c in gym.get_env_rigid_contacts(env):
   if c['lambda']<=1e-6:continue
   first=contact_names.get(int(c['body0']),'ground');second=contact_names.get(int(c['body1']),'ground');pair=[first,second]
   if not any(n in ['link_0','link_1'] for n in pair):continue
   normal=c['normal'];vector=[float(normal[n]) for n in ['x','y','z']]
   pair_stream.write(json.dumps(dict(time_s=t,body0=first,body1=second,normal_world=vector,solver_lambda=float(c['lambda'])))+'\n')
   for index,finger in enumerate(FINGERS):
    if not any('_'+finger+'_' in n for n in pair):continue
    if 'link_1' in pair:slider_count[index]+=1;slider_magnitude[index]+=float(c['lambda'])
    if 'link_0' in pair:body_count[index]+=1;body_magnitude[index]+=float(c['lambda'])
  return dict(finger_body_contacts=body_count,finger_slider_contacts=slider_count,finger_body_solver_magnitude=body_magnitude,finger_slider_solver_magnitude=slider_magnitude)
 try:
  for step in range(int(a.seconds*240)):
   gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_jacobian_tensors(sim);t=step/240
   if step%8==0:
    q=dof[hand,0].numpy().copy();act=np.zeros(20,dtype=np.float32);policy.record(q,policy.last_action if taken else act)
    if t<2:aq=qabove;hq=opened
    elif t<5:aq=acquisition_motor(approach_path,smooth((t-2)/3)) if a.acquisition_path else path_motor(1-smooth((t-2)/3)) if a.cartesian_path else qabove+smooth((t-2)/3)*(qgrasp-qabove);hq=opened
    elif t<8:aq=qgrasp;hq=close_motor((t-5)/3)
    elif t<12:aq=acquisition_motor(lift_path,smooth((t-8)/4)) if a.acquisition_path else path_motor(smooth((t-8)/4)) if a.cartesian_path else qgrasp+smooth((t-8)/4)*(qlift-qgrasp);hq=closed
    elif t<16 or a.grasp_only:aq=qlift;hq=closed
    else:
     aq=qlift
     if not taken:
      slider_est=policy_slider_estimate if policy_slider_estimate is not None else policy_relative@transform([0,.0075,.010624586881962734+lower]);policy.takeover_estimate(q,target[hand].numpy(),policy_relative,slider_est);taken=True;operation_reference=rb[oid].numpy().copy()
     if thumb_script is not None:
      phase=int((t-16)/5);fraction=smooth(min(1.,((t-16)%5)/script_travel_seconds));shift=.04*(fraction if phase%2==0 else 1-fraction)
      desired=closed.copy();desired[16:]=np.array([np.interp(shift,script_shifts,script_q[:,n]) for n in range(4)])+script_preload
      hq,act=policy.scripted_target(desired)
     else:
      hq,act=policy.command(q,.04 if int((t-16)/5)%2==0 else 0.,wrist_gravity=kin.forward(dof[arm,0].numpy())[:3,:3].T@np.array([0.,0.,-1.]))
    target[arm]=torch.tensor(aq,dtype=torch.float32);target[hand]=torch.tensor(hq,dtype=torch.float32);target=torch.minimum(torch.maximum(target,limitlow),limithi)
    # During scripted history settling, actions are the actual equivalent support/target commands (constant targets ->0).
   gravity_ff=(jac[0,:,2,:]*masses[:,None]*9.81).sum(0);torque=K*(target-dof[:27,0])-C*dof[:27,1]+gravity_ff;force[:27]=torch.maximum(torch.minimum(torque,limits),-limits);v=float(dof[sid,1]);travel=float(dof[sid,0])-lower;amplitude=a.load*(.25+.75*np.sin(1.7*t+.4)**2) if a.variable_load else a.load;run_load=-amplitude*np.tanh(v/.002);start_load=-a.detent*np.sin(np.clip(travel/.004,0,1)*np.pi) if 0<=travel<=.004 else 0.;x=(travel-.021)/.0015;groove_load=-a.detent*np.pi*.5*np.sin(np.pi*x) if abs(x)<1 else 0.;load=run_load+start_load+groove_load;force[sid]=load;max_positive_power=max(max_positive_power,run_load*v);gym.set_dof_actuation_force_tensor(sim,gymtorch.unwrap_tensor(force));gym.simulate(sim);gym.fetch_results(sim,True)
   if step%8==7:
    gym.refresh_dof_state_tensor(sim);gym.refresh_rigid_body_state_tensor(sim);gym.refresh_net_contact_force_tensor(sim);row=dict(time=t+1/240,q=dof[hand,0].numpy().copy(),arm_q=dof[arm,0].numpy().copy(),target=target.numpy().copy(),action=act.copy(),raw_base_action=policy.last_raw_action.copy() if taken else np.zeros(20,dtype=np.float32),object=rb[oid].numpy().copy(),wrist=rb[wrist].numpy().copy(),slider=float(dof[sid,0]),slider_velocity=float(dof[sid,1]),load=load,dissipative_load=run_load,passive_groove_load=start_load+groove_load,torque=force[:27].numpy().copy(),hand_contact=contact[:len(rbnames)].numpy().copy(),phase=0 if t<5 else 1 if t<8 else 2 if t<12 else 3 if t<16 else 4);rows.append(row)
    row.update(pair_diagnostics(t+1/240))
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
  report=dict(start='Knife resting on table; hand initially open at planned clearance (11.5cm for registered Cartesian path,16cm otherwise)',methods=('Motor-only scripted continuous-IK approach/close/lift' if a.cartesian_path or a.acquisition_path else 'Motor-only scripted joint-space approach/close/lift')+'; finite-torque gravity-compensated arm/hand; '+('pickup-only diagnostic' if a.grasp_only else ('offline-calibrated scheduled thumb IK with static joint preload' if thumb_script is not None else 'R800+bounded residual' if a.residual_checkpoint else 'R800')+' after16s with once-loaded relative-grip calibration estimate'),lifted_clear=bool((h[held]>a.table_height+.03).all()) if held.any() else False,operation_stays_clear=bool((h[opmask]>a.table_height+.03).all()) if opmask.any() else False,meaningful_extension=opened_ok,retraction_after31s=closed_ok,full_success=False,minimum_hold_height_m=float(h[held].min()) if held.any() else None,max_object_height_m=float(h.max()),wall_seconds=time.monotonic()-started,positive_load_power_max_W=max_positive_power,weight_sha256={str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth']+([R/a.residual_checkpoint] if a.residual_checkpoint else [])},scope='Continuous physics attempt, no stage state writes. Meaningful25mm extension and8mm return are predeclared demo diagnostics; inherited40mm command unchanged. No preciseS5claim.')
  if a.acquisition_path:report['start']='Knife at configured tabletop edge with COM on table; open hand outside edge, lateral acquisition then vertical lift'
  report.update(operation_evaluated=not a.grasp_only and a.seconds>=36,endpoints_mean_last03s_m=endpoints,diagnostic='Scheduled four5s stages; final0.3s mean >25mm extend and <8mm return on both cycles; no truth-triggered switching')
  if held.any() and opmask.any():
   handover_i=np.flatnonzero(held)[-1];op=trace['object'][opmask];origin=trace['object'][handover_i];drift=np.linalg.norm(op[:,:3]-origin[:3],axis=-1);rot=(Rotation.from_quat(origin[3:7]).inv()*Rotation.from_quat(op[:,3:7])).magnitude()
   report.update(operation_body_max_drift_m=float(drift.max()),operation_body_max_rotation_rad=float(rot.max()),operation_body_stable=bool((drift<.01).all() and (rot<.25).all()),slider_before_handover_m=float(trace['slider'][handover_i]-lower),slider_closed_at_handover=bool(abs(float(trace['slider'][handover_i]-lower))<.008))
  else:report.update(operation_body_stable=False,slider_closed_at_handover=False)
  report.update(residual_checkpoint=str(a.residual_checkpoint),thumb_script=str(a.thumb_script),thumb_script_scope='Known 40mm schedule+offline geometric trajectory and joint preload, not constant force or live state feedback' if thumb_script is not None else None,thumb_action_gain=a.thumb_action_gain,support_action_gain=a.support_action_gain,added_load_N=a.load,passive_startup_detent_amplitude_N=a.detent,variable_load=a.variable_load,load_scope='Engineering added load plus original passive friction/damping; no measured real total-resistance ceiling. Groove is finite passive potential; positive descent power is stored energy.')
  if opmask.any():
   report.update(operation_thumb_slider_contact_fraction=float((trace['finger_slider_contacts'][opmask,0]>0).mean()),operation_body_contact_fraction=(trace['finger_body_contacts'][opmask]>0).mean(0).tolist(),contact_scope='30Hz solver-contact diagnostics; current truth never fed to actor. Positive motor preload does not establish constant pressure.')
   report['operation_thumb_slider_contact_maintained']=report['operation_thumb_slider_contact_fraction']>=.90
  else:report['operation_thumb_slider_contact_maintained']=False
  report['extension_endpoint_condition_met']=opened_ok
  report['meaningful_extension']=opened_ok and report['operation_body_stable'] and report['operation_thumb_slider_contact_maintained']
  report['full_success']=report['operation_thumb_slider_contact_maintained'] and report['operation_body_stable'] and report['slider_closed_at_handover'] and report['operation_evaluated'] and report['lifted_clear'] and report['operation_stays_clear'] and opened_ok and closed_ok
  report['first_failure']='none' if report['full_success'] else 'pickup/lift' if not report['lifted_clear'] else 'operation not tested' if a.grasp_only else 'holding after handover' if not report['operation_stays_clear'] else 'body stability after handover' if not report['operation_body_stable'] else 'extension/retraction';(a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
 finally:
  pair_stream.close()
  if writer:writer.close();closewriter.close()
  gym.destroy_sim(sim)
if __name__=='__main__':main()
