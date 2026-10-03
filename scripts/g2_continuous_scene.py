"""Actual G2+Wuji parallel scenes, reusing the successful continuous runner.

Physics resets occur only at training episode boundaries. Acquisition, hold
and operation share continuous states, velocities, gravity and collisions.
"""
import json, xml.etree.ElementTree as ET
from pathlib import Path
from isaacgym import gymapi,gymtorch
import torch
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform,G2Kinematics
from scripts.g2_batched_r800 import BatchedG2R800
from scripts.wuji_robust_learning import TEACHER,R800
from scripts.wuji_goal_common import configuration
from scripts.wuji_scheduled_thumb_reference import ScheduledThumbReference
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul,quat_conjugate

R=Path(__file__).resolve().parents[1]
D=R/'research/robust-knife-family-20261003'


def smooth(u):
    u=u.clamp(0.,1.)
    return u*u*u*(10.-15.*u+6.*u*u)


def gym_transform(position,quaternion=(0,0,0,1)):
    result=gymapi.Transform();result.p=gymapi.Vec3(*position);result.r=gymapi.Quat(*quaternion)
    return result


class G2ContinuousScene:
    def __init__(self,n=8,seed=2026100356,randomization_scale=0.,instances=None,
                 load_max=.1,detent_max=.1,contact_progress_reward=0.,reference_spec=None,
                 support_scale=.25,thumb_scale=.25,takeover_seconds=16.,load_profile='sinusoidal',load_frequency=1.7,history_features=False,support_estimator_spec=None,functional_thumb_reward=False,scene_spec=None,absorbing_failure_penalty=False,strong_slider_contact_reward=False,graphics=False,disabled_perturbations=(),action_parameterization='incremental',resistance_integration='legacy-explicit',load_min=0.,detent_min=0.,asset_registry=None,proprioceptive_pressure_spec=None,resample_initial_estimates=False,stable_progress_reward=False,support_load_feature_spec=None):
        self.n=n;self.device='cuda:0';self.seed=seed
        self.disabled_perturbations=set(disabled_perturbations)
        assert self.disabled_perturbations <= {'calibration','placement','sensor','latency','material'}
        self.history_features=history_features;self.public_dim=(170 if history_features else 154)+(8 if support_estimator_spec else 0)
        self.support_load_feature_spec=support_load_feature_spec;self.support_load_features=None
        self.public_dim+=9 if support_load_feature_spec else 0
        self.support_estimator_spec=support_estimator_spec;self.support_estimator=None
        if support_estimator_spec:
            from scripts.g2_legal_support_estimator import LegalSupportEstimator
            self.support_estimator=LegalSupportEstimator(support_estimator_spec,self.device)
        # Use float32 convolution rather than TF32 for deployment/batch parity.
        torch.backends.cudnn.allow_tf32=False
        torch.manual_seed(seed);self.rng=np.random.default_rng(seed)
        self.randomization_scale=randomization_scale;self.load_max=load_max;self.detent_max=detent_max
        assert resistance_integration in ['legacy-explicit','solver-brake']
        assert 0<=load_min<=load_max and 0<=detent_min<=detent_max
        self.resistance_integration=resistance_integration;self.load_min=load_min;self.detent_min=detent_min
        self.slider_drive_properties=[]
        assert 8<=takeover_seconds<=16 and abs(takeover_seconds*30-round(takeover_seconds*30))<1e-6
        self.takeover_frame=round(takeover_seconds*30)
        self.load_profile=load_profile;self.load_frequency=load_frequency
        assert load_profile in ['constant','sinusoidal','triangular','pulse','mixed'] and load_frequency>0
        self.scale=self.tensor([support_scale]*16+[thumb_scale]*4);self.base_mode='geometric';self.env=self
        assert action_parameterization in ['incremental','bounded-motor-offset']
        self.action_parameterization=action_parameterization
        self.contact_progress_reward=contact_progress_reward
        self.functional_thumb_reward=functional_thumb_reward
        self.stable_progress_reward=stable_progress_reward
        self.absorbing_failure_penalty=absorbing_failure_penalty
        self.strong_slider_contact_reward=strong_slider_contact_reward
        self.cfg=configuration('wuji_geometry',n,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=seed)
        self.bridge=BatchedG2R800(self.cfg,TEACHER,R800,n)
        self.player=self.bridge.player
        self.scene_spec=scene_spec
        self.plan=scene_spec['plan'] if scene_spec else json.loads((D/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text())
        self.acquisition=scene_spec['acquisition'] if scene_spec else json.loads((D/'functional-side-edge-under-support-lateral-v3/acquisition-path.json').read_text())
        self.calibration=scene_spec['calibration'] if scene_spec else json.loads((D/'handover-from-v25-v1.json').read_text())
        if scene_spec:
            assert scene_spec['scope'] in ['Fixed nominal scene shared across all physical assets; no asset-specific actor input','Initial noisy estimate guided common motor planning; no runtime object/contact truth or assetID actor input']
            assert len(self.plan['close_q'])==20 and len(self.plan['open_q'])==20
        self.reference_spec=reference_spec or json.loads((D/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text())
        self.reference=ScheduledThumbReference(self.reference_spec,n,self.device)
        self.closed=self.tensor(self.plan['close_q']);self.opened=self.tensor(self.plan['open_q'])
        self.estimated_plans=scene_spec.get('initial_estimated_plans') if scene_spec else None
        if self.estimated_plans:
            assert len(self.estimated_plans)==n
            for row in self.estimated_plans:assert row['estimate']['source'] and row['estimate']['uncertainty_m']>0
            self.closed=self.tensor([row['motor_plan']['close_q'] for row in self.estimated_plans])
            self.opened=self.tensor([row['motor_plan']['open_q'] for row in self.estimated_plans])
            self.reference.q=self.tensor([[r['q_thumb'] for r in row['thumb_reference']['rows']] for row in self.estimated_plans])
            self.reference.preload_schedule={'seconds':[12,14]}
            self.reference.preload_delta=self.tensor([np.asarray(row['support_target_q'])-np.asarray(row['motor_plan']['close_q']) for row in self.estimated_plans])
            self.bridge.geometry=self.tensor([row['estimate']['handle_size_WTL_m']+[.01,.003,.03] for row in self.estimated_plans])
        self.opened_batch=self.opened.expand(n,-1);self.closed_batch=self.closed.expand(n,-1)
        self.close_waypoint_tensors=[self.tensor([row['motor_plan']['close_waypoints'][i]['q'] for row in self.estimated_plans]) if self.estimated_plans else self.tensor(way['q']).expand(n,-1) for i,way in enumerate(self.plan['close_waypoints'])]
        self.support_waypoint_q=None
        if self.estimated_plans and any(row.get('support_motor_waypoints') for row in self.estimated_plans):
            recipe=next(row['support_motor_waypoints'] for row in self.estimated_plans if row.get('support_motor_waypoints'))
            self.support_waypoint_times=[r['time_s'] for r in recipe]
            assert self.support_waypoint_times[-1]<=14.2 and self.takeover_frame==480
            self.support_waypoint_enabled=torch.tensor([bool(row.get('support_motor_waypoints')) for row in self.estimated_plans],device=self.device)
            self.support_waypoint_q=self.tensor([[r['q'] for r in row['support_motor_waypoints']] if row.get('support_motor_waypoints') else [row['motor_plan']['close_q']]*len(recipe) for row in self.estimated_plans])
            for row in self.estimated_plans:
                if row.get('support_motor_waypoints'):assert [r['time_s'] for r in row['support_motor_waypoints']]==self.support_waypoint_times
        self.cal_prior={}
        for key in ['object_in_wrist','slider_in_wrist']:
            mat=np.asarray(self.calibration[key]);positions=np.tile(mat[:3,3],(n,1));rotations=np.tile(Rotation.from_matrix(mat[:3,:3]).as_quat(),(n,1))
            if self.estimated_plans:
                object_rotation=np.asarray(self.calibration['object_in_wrist'])[:3,:3]
                for i,row in enumerate(self.estimated_plans):
                    estimate=row['estimate'];shift=np.asarray(estimate.get('initial_object_center_shift_knife_m',[0,0,0]))
                    if key=='slider_in_wrist':shift=shift+np.asarray(estimate['slider_contact_shift_m'])+np.array([0,(estimate['handle_size_WTL_m'][1]-.012)/2,0])
                    positions[i]+=object_rotation@shift
            self.cal_prior[key]=(self.tensor(positions),self.tensor(rotations))
        self.estimate_bank=None
        self.initial_observation_indices=torch.arange(n,device=self.device)
        self.resample_initial_estimates=resample_initial_estimates or bool(scene_spec and scene_spec.get('resample_initial_estimates'))
        if self.resample_initial_estimates:
            assert self.estimated_plans and instances and len(instances)==n
            # The simulator groups synthetic sensor samples for the same
            # physical geometry. The planner has already consumed only each
            # noisy observation; this grouping never enters actor/controller.
            groups={name:[i for i,value in enumerate(instances) if value==name] for name in set(instances)}
            counts={len(values) for values in groups.values()};assert len(counts)==1 and min(counts)>1
            self.estimate_choices=torch.tensor([groups[name] for name in instances],device=self.device,dtype=torch.long)
            self.estimate_bank=dict(closed=self.closed.clone(),opened=self.opened.clone(),
                thumb_q=self.reference.q.clone(),preload=self.reference.preload_delta.clone(),geometry=self.bridge.geometry.clone(),
                waypoints=[value.clone() for value in self.close_waypoint_tensors],
                calibration={key:(p.clone(),q.clone()) for key,(p,q) in self.cal_prior.items()})
            if self.support_waypoint_q is not None:
                self.estimate_bank.update(support_waypoint_q=self.support_waypoint_q.clone(),support_waypoint_enabled=self.support_waypoint_enabled.clone())
            self.scene_spec=dict(self.scene_spec,resample_initial_estimates=True,
                initial_estimate_sampling_scope='At newphysicalepisode only, resample one of four labelled noisy initial observations for that geometry; common IK outputs, no physicalID/currenttruth actor input. Finite observation bank, not connected realvision.')
        self.middle_support=None
        if scene_spec and scene_spec.get('middle_deflection_support'):
            assert not self.estimated_plans
            from scripts.g2_middle_deflection_support import BatchedMiddleDeflectionSupport
            assert self.takeover_frame==480,'Finite postliftsearch needs50constanttargetframes before16s takeover'
            support_spec=scene_spec['middle_deflection_support']
            assert abs(float(self.closed[7])-support_spec['motor_upper_rad'])<1e-6
            self.middle_support=BatchedMiddleDeflectionSupport(support_spec,n,self.device)
        self.approach=self.tensor(self.acquisition['approach_q']);self.lift=self.tensor(self.acquisition['lift_q'])
        self.age=torch.zeros(n,device=self.device,dtype=torch.long)
        self.last_action=torch.zeros((n,20),device=self.device)
        self.observation_bias=torch.zeros_like(self.last_action)
        self.delay=torch.zeros(n,device=self.device,dtype=torch.bool)
        self.delayed_action=torch.zeros_like(self.last_action)
        self.load_amplitude=torch.zeros(n,device=self.device);self.load_phase=torch.zeros_like(self.load_amplitude)
        self.load_profile_ids=torch.full((n,),['constant','sinusoidal','triangular','pulse','mixed'].index(load_profile),device=self.device,dtype=torch.long)
        self.load_frequencies=torch.full((n,),float(load_frequency),device=self.device)
        self.detent_amplitude=torch.zeros_like(self.load_amplitude)
        self.load_force=torch.zeros_like(self.load_amplitude)
        self.cal_object=torch.zeros((n,7),device=self.device);self.cal_slider=self.cal_object.clone()
        self.proprioceptive_pressure_spec=proprioceptive_pressure_spec or (scene_spec.get('proprioceptive_pressure_spec') if scene_spec else None)
        if support_load_feature_spec:
            assert not history_features and support_estimator_spec is None and takeover_seconds==16
            from scripts.wuji_support_load_features import SupportLoadFeatures
            self.support_load_features=SupportLoadFeatures(n,self.device,np.asarray(self.cfg.hand.dof_props.stiffness),np.asarray(self.cfg.hand.dof_props.damping))
        self.pressure_adapter=None
        if self.proprioceptive_pressure_spec:
            assert self.takeover_frame==480 and self.resistance_integration=='solver-brake'
            from scripts.wuji_joint_deflection_pressure import BatchedJointDeflectionPressure
            self.pressure_adapter=BatchedJointDeflectionPressure(self.proprioceptive_pressure_spec,n,self.device,np.asarray(self.cfg.hand.dof_props.stiffness))
            if self.scene_spec:self.scene_spec=dict(self.scene_spec,proprioceptive_pressure_spec=self.proprioceptive_pressure_spec)
        self.actual_materials={};self.transitions=0;self.episodes=0;self.stats=[]
        self._features=None;self._measurement=None
        self.gym=gymapi.acquire_gym();sp=gymapi.SimParams();sp.dt=1/240;sp.substeps=1
        sp.up_axis=gymapi.UP_AXIS_Z;sp.gravity=gymapi.Vec3(0,0,-9.81)
        sp.use_gpu_pipeline=True;sp.physx.use_gpu=True;sp.physx.solver_type=1
        sp.physx.num_position_iterations=8;sp.physx.num_velocity_iterations=2
        sp.physx.contact_offset=.001;sp.physx.rest_offset=0;sp.physx.max_depenetration_velocity=1.
        sp.physx.num_threads=4
        self.sim=self.gym.create_sim(0,0 if graphics else -1,gymapi.SIM_PHYSX,sp);assert self.sim
        plane=gymapi.PlaneParams();plane.normal=gymapi.Vec3(0,0,1);self.gym.add_ground(self.sim,plane)
        opt=gymapi.AssetOptions();opt.fix_base_link=True;opt.disable_gravity=False
        opt.collapse_fixed_joints=False;opt.thickness=.001;opt.use_physx_armature=True
        robot_asset=self.gym.load_asset(self.sim,str(R),'assets/robots/g2_wuji/g2_wuji.urdf',opt)
        opt=gymapi.AssetOptions();opt.fix_base_link=True
        table_asset=self.gym.create_box(self.sim,.60,.80,.05,opt)
        self.instances=instances or [f't{i:04d}' for i in range(min(n,512))]
        self.envs=[];self.robots=[];self.knives=[];self.origins=[];self.asset_records=[];self.layout=[]
        assets={};self.lower=[]
        for i in range(n):
            env=self.gym.create_env(self.sim,gymapi.Vec3(-1.5,-1.5,0),gymapi.Vec3(1.5,1.5,2),int(np.ceil(np.sqrt(n))))
            robot=self.gym.create_actor(env,robot_asset,gymapi.Transform(),'robot',i,0)
            names=self.gym.get_actor_dof_names(env,robot)
            if i==0:
                self.hand=np.array([names.index(name) for name in self.bridge.single.fk.names]);self.arm=np.array([names.index(name) for name in G2Kinematics().names])
                assert len(names)==27 and len(set(self.hand))==20 and not set(self.hand)&set(self.arm)
                self.rb_names=self.gym.get_actor_rigid_body_names(env,robot);self.robot_body_count=len(self.rb_names)
                self.pad_indices=[self.rb_names.index('hand_r_'+f+'_pad_link') for f in ['thumb','index','middle','ring','pinky']]
                self.wrist_index=self.rb_names.index('hand_r_base_link')
                props=self.gym.get_actor_dof_properties(env,robot);kp=np.zeros(27);kd=np.zeros(27)
                arm_meta=json.loads((R/'assets/robots/g2_wuji/audit.json').read_text())['active_arm']
                kp[self.arm]=[x['stiffness'] for x in arm_meta];kd[self.arm]=[x['damping'] for x in arm_meta]
                kp[self.hand]=np.array(self.cfg.hand.dof_props.stiffness);kd[self.hand]=np.array(self.cfg.hand.dof_props.damping)
                for key in ['armature','friction']:props[key][self.hand]=np.array(self.cfg.hand.dof_props[key])
                props['armature'][self.arm]=.01;props['driveMode'][:]=gymapi.DOF_MODE_EFFORT
                props['stiffness'][:]=0;props['damping'][:]=0
                self.kp=self.tensor(kp);self.kd=self.tensor(kd);self.effort=self.tensor(props['effort'].copy())
                self.limitlow=self.tensor(props['lower'].copy());self.limithi=self.tensor(props['upper'].copy())
                self.robot_props=props.copy()
            self.gym.set_actor_dof_properties(env,robot,self.robot_props)
            shapes=self.gym.get_actor_rigid_shape_properties(env,robot)
            indices=self.gym.get_actor_rigid_body_shape_indices(env,robot)
            digits=['thumb','index','middle','ring','pinky'];allbits=sum(1<<(8+j) for j in range(5))+sum(1<<(16+j) for j in range(5))
            for name,index in zip(self.rb_names,indices):
                if not name.startswith('hand_r_'):mask=(1<<7)|allbits
                elif name=='hand_r_base_link':mask=sum(1<<(16+j) for j in range(5))
                else:
                    digit=next(j for j,d in enumerate(digits) if '_'+d+'_' in name);mask=1<<(8+digit)
                    if name.endswith(('link1','link2')):mask|=1<<(16+digit)
                for k in range(index.start,index.start+index.count):shapes[k].filter=mask;shapes[k].friction=1.
            self.gym.set_actor_rigid_shape_properties(env,robot,shapes)
            self.gym.create_actor(env,table_asset,gym_transform([.60,-.25,.725]),'table',i,0)
            sid=self.instances[i%len(self.instances)]
            directory=R/asset_registry[sid] if asset_registry is not None else R/'assets/objects'/('knife_wuji_real_size_20261002' if sid=='000' else 'knife_wuji_dense_under_20261003')/sid
            parameters=json.loads((directory/'parameters.json').read_text())
            if sid not in assets:
                opt=gymapi.AssetOptions();opt.fix_base_link=False;opt.disable_gravity=False
                opt.override_com=False;opt.override_inertia=False;opt.thickness=.001;opt.density=1000
                assets[sid]=self.gym.load_asset(self.sim,str(R),str((directory/'mobility.urdf').relative_to(R)),opt)
            knife=self.gym.create_actor(env,assets[sid],gym_transform([.3015,-.25,.75+parameters['handle_size'][1]/2+.0001],Rotation.from_euler('x',90,degrees=True).as_quat()),'knife',i,0)
            bodies=self.gym.get_actor_rigid_body_properties(env,knife);xml=ET.parse(directory/'mobility.urdf')
            for body,name in zip(bodies,['link_0','link_1']):
                node=xml.find(f"./link[@name='{name}']/inertial");body.mass=float(node.find('mass').get('value'));v=node.find('inertia')
                body.inertia.x.x=float(v.get('ixx'));body.inertia.y.y=float(v.get('iyy'));body.inertia.z.z=float(v.get('izz'))
            self.gym.set_actor_rigid_body_properties(env,knife,bodies,False)
            shapes=self.gym.get_actor_rigid_shape_properties(env,knife)
            for shape in shapes:shape.friction=3.;shape.filter=1
            self.gym.set_actor_rigid_shape_properties(env,knife,shapes)
            op=self.gym.get_actor_dof_properties(env,knife);self.lower.append(float(op['lower'][0]))
            op['driveMode'][:]=gymapi.DOF_MODE_EFFORT;op['stiffness'][:]=0;op['damping'][:]=.3;op['friction'][:]=.001;op['armature'][:]=.001
            if self.resistance_integration=='solver-brake':
                op['driveMode'][:]=gymapi.DOF_MODE_VEL;op['damping'][:]=250.;op['effort'][:]=max(load_max,1e-8)
            self.gym.set_actor_dof_properties(env,knife,op)
            if self.resistance_integration=='solver-brake':self.gym.set_actor_dof_velocity_targets(env,knife,np.zeros(1,dtype=np.float32))
            self.slider_drive_properties.append(op.copy())
            initial_state=np.zeros(27,dtype=gymapi.DofState.dtype)
            initial_state['pos'][self.arm]=np.asarray(self.acquisition['approach_q'][0])
            initial_state['pos'][self.hand]=self.opened_batch[i].cpu().numpy()
            self.gym.set_actor_dof_states(env,robot,initial_state,gymapi.STATE_ALL)
            slider_state=np.zeros(1,dtype=gymapi.DofState.dtype);slider_state['pos'][0]=self.lower[-1]
            self.gym.set_actor_dof_states(env,knife,slider_state,gymapi.STATE_ALL)
            origin=self.gym.get_env_origin(env);self.origins.append([origin.x,origin.y,origin.z])
            self.layout.append(dict(env=i,origin=[origin.x,origin.y,origin.z],robot_actor=self.gym.get_actor_index(env,robot,gymapi.DOMAIN_SIM),knife_actor=self.gym.get_actor_index(env,knife,gymapi.DOMAIN_SIM),robot_dof_start=self.gym.get_actor_dof_index(env,robot,0,gymapi.DOMAIN_SIM),knife_dof=self.gym.get_actor_dof_index(env,knife,0,gymapi.DOMAIN_SIM),robot_rb_start=self.gym.get_actor_rigid_body_index(env,robot,0,gymapi.DOMAIN_SIM),knife_rb_start=self.gym.get_actor_rigid_body_index(env,knife,0,gymapi.DOMAIN_SIM)))
            self.envs.append(env);self.robots.append(robot);self.knives.append(knife);self.asset_records.append(parameters)
        print(json.dumps(dict(scene_layout=self.layout[:8],robot_body_count=self.robot_body_count)),flush=True)
        for i,row in enumerate(self.layout):
            assert row['robot_actor']==i*3 and row['knife_actor']==i*3+2,('actor layout',row)
            assert row['robot_dof_start']==i*28 and row['knife_dof']==i*28+27,('DOF layout',row)
            assert row['robot_rb_start']==i*(self.robot_body_count+3) and row['knife_rb_start']==i*(self.robot_body_count+3)+self.robot_body_count+1,('RB layout',row)
        self.gym.prepare_sim(self.sim)
        self.dof=gymtorch.wrap_tensor(self.gym.acquire_dof_state_tensor(self.sim)).view(n,28,2)
        self.root=gymtorch.wrap_tensor(self.gym.acquire_actor_root_state_tensor(self.sim)).view(n,3,13)
        self.gym.refresh_actor_root_state_tensor(self.sim)
        print(json.dumps(dict(initial_actor_roots=self.root[:min(2,n),:,:7].cpu().tolist(),origins=self.origins[:2])),flush=True)
        self.rb=gymtorch.wrap_tensor(self.gym.acquire_rigid_body_state_tensor(self.sim)).view(n,self.robot_body_count+3,13)
        self.contact=gymtorch.wrap_tensor(self.gym.acquire_net_contact_force_tensor(self.sim)).view(n,self.robot_body_count+3,3)
        self.jac=gymtorch.wrap_tensor(self.gym.acquire_jacobian_tensor(self.sim,'robot'))
        masses=self.gym.get_actor_rigid_body_properties(self.envs[0],self.robots[0])
        self.masses=self.tensor([b.mass for b in masses][1:]);assert self.jac.shape[1]==len(self.masses)
        self.origins=self.tensor(self.origins);self.lower=self.tensor(self.lower)
        self.target=torch.zeros((n,27),device=self.device);self.forces=torch.zeros((n,28),device=self.device)
        self.command_target=self.target.clone();self.delayed_target=self.target.clone()
        self.hand_ids=torch.tensor(self.hand,device=self.device);self.arm_ids=torch.tensor(self.arm,device=self.device)
        self.object_index=self.robot_body_count+1;self.slider_index=self.robot_body_count+2
        self.reference_pose=torch.zeros((n,7),device=self.device)
        self.pickup_reference_in_wrist=self.reference_pose.clone()
        self.peak=torch.zeros(n,device=self.device);self.max_drift=self.peak.clone();self.max_rotation=self.peak.clone()
        self.min_hold_height=torch.full((n,),float('inf'),device=self.device)
        self.endpoints=torch.zeros((n,4),device=self.device);self.contact_steps=self.peak.clone();self.operation_steps=self.peak.clone()
        self.closed_at_handover=torch.zeros(n,device=self.device,dtype=torch.bool)
        self.fell=torch.zeros(n,device=self.device,dtype=torch.bool)
        self.last_held_pose=self.reference_pose.clone()
        self.material_tensor=torch.tensor([[1.,3.] for _ in range(n)],device=self.device)
        self.mass_tensor=self.tensor([p['masses'] for p in self.asset_records])
        self.slider_half=self.tensor([p['slider_size'] for p in self.asset_records])/2
        from scripts.g2_contact_geometry import DigitGeometry
        vertices=np.concatenate([v for v,_ in DigitGeometry().meshes['hand_r_thumb_pad_link']])
        self.thumb_vertices=self.tensor(vertices)
        self.reset(torch.arange(n,device=self.device))

    def tensor(self,value):return torch.tensor(value,device=self.device,dtype=torch.float32)

    def refresh(self):
        self.gym.refresh_dof_state_tensor(self.sim);self.gym.refresh_rigid_body_state_tensor(self.sim)
        self.gym.refresh_net_contact_force_tensor(self.sim);self.gym.refresh_jacobian_tensors(self.sim)

    def reset(self,ids):
        if not len(ids):return
        k=len(ids);s=self.randomization_scale
        if self.estimate_bank is not None:
            choices=torch.randint(self.estimate_choices.shape[1],(k,),device=self.device)
            selected=self.estimate_choices[ids,choices];self.initial_observation_indices[ids]=selected
            self.closed[ids]=self.estimate_bank['closed'][selected];self.opened[ids]=self.estimate_bank['opened'][selected]
            self.reference.q[ids]=self.estimate_bank['thumb_q'][selected]
            self.reference.preload_delta[ids]=self.estimate_bank['preload'][selected]
            self.bridge.geometry[ids]=self.estimate_bank['geometry'][selected]
            if self.support_waypoint_q is not None:
                self.support_waypoint_q[ids]=self.estimate_bank['support_waypoint_q'][selected]
                self.support_waypoint_enabled[ids]=self.estimate_bank['support_waypoint_enabled'][selected]
            for current,bank in zip(self.close_waypoint_tensors,self.estimate_bank['waypoints']):current[ids]=bank[selected]
            for key,(position,rotation) in self.cal_prior.items():
                bank_position,bank_rotation=self.estimate_bank['calibration'][key]
                position[ids]=bank_position[selected];rotation[ids]=bank_rotation[selected]
        self.age[ids]=0;self.last_action[ids]=0;self.delayed_action[ids]=0
        self.reference.reset(ids)
        if self.middle_support is not None:self.middle_support.reset(ids)
        self.observation_bias[ids]=(torch.rand((k,20),device=self.device)-.5)*.012*s
        self.delay[ids]=torch.rand(k,device=self.device)<.15*s
        if 'sensor' in self.disabled_perturbations:self.observation_bias[ids]=0
        if 'latency' in self.disabled_perturbations:self.delay[ids]=False
        self.load_amplitude[ids]=torch.rand(k,device=self.device)*self.load_max*s if s else .05
        self.detent_amplitude[ids]=torch.rand(k,device=self.device)*self.detent_max*s if s else .05
        if self.resistance_integration=='solver-brake':
            # Load ranges are independent of the geometric/noise curriculum.
            self.load_amplitude[ids]=self.load_min+torch.rand(k,device=self.device)*(self.load_max-self.load_min)
            self.detent_amplitude[ids]=self.detent_min+torch.rand(k,device=self.device)*(self.detent_max-self.detent_min)
        self.load_phase[ids]=torch.rand(k,device=self.device)*2*np.pi if s else .4
        translation=(torch.rand((k,3),device=self.device)-.5)*.002*s
        angle=(torch.rand((k,3),device=self.device)-.5)*np.deg2rad(3)*s
        if 'calibration' in self.disabled_perturbations:translation.zero_();angle.zero_()
        norm=angle.norm(dim=-1,keepdim=True)
        delta=torch.cat([angle*.5*torch.sinc(norm/(2*np.pi)),torch.cos(norm*.5)],-1)
        for key,dest in [('object_in_wrist',self.cal_object),('slider_in_wrist',self.cal_slider)]:
            position,rotation=self.cal_prior[key]
            dest[ids]=torch.cat([position[ids]+translation,quat_mul(delta,rotation[ids])],-1)
        if self.support_load_features is not None:
            normal=quat_apply(self.cal_object[ids,3:7],self.tensor([0,1,0])[None].expand(k,-1))
            self.support_load_features.reset(ids,normal)
        if self.pressure_adapter is not None:
            normal=quat_apply(self.cal_object[ids,3:7],self.tensor([0,1,0])[None].expand(k,-1))
            self.pressure_adapter.reset(ids,normal)
        self.target[ids,:]=0.;self.target[ids[:,None],self.arm_ids]=self.approach[0]
        self.target[ids[:,None],self.hand_ids]=self.opened_batch[ids]
        self.command_target[ids]=self.target[ids];self.delayed_target[ids]=self.target[ids]
        self.dof[ids,:,:]=0.;self.dof[ids,:27,0]=self.target[ids];self.dof[ids,27,0]=self.lower[ids]
        # Installed Preview4 tensors use environment-local coordinates, verified
        # against refreshed native roots. Adding env origins double-translates.
        self.root[ids,0,:]=0.;self.root[ids,0,6]=1.
        shift=(torch.rand((k,2),device=self.device)-.5)*.002*s
        yaw=(torch.rand(k,device=self.device)-.5)*np.deg2rad(3)*s
        if 'placement' in self.disabled_perturbations:shift.zero_();yaw.zero_()
        quaternion=quat_mul(torch.stack([torch.zeros_like(yaw),torch.zeros_like(yaw),torch.sin(yaw/2),torch.cos(yaw/2)],-1),self.tensor([np.sqrt(.5),0.,0.,np.sqrt(.5)])[None].expand(k,-1))
        thickness=self.tensor([self.asset_records[i]['handle_size'][1] for i in ids.tolist()])
        self.root[ids,2,:]=0.;self.root[ids,2,:3]=torch.stack([.3015+shift[:,0],-.25+shift[:,1],.75+thickness/2+.0001],-1)
        self.root[ids,2,3:7]=quaternion
        actor_ids=torch.stack([ids*3,ids*3+2],-1).flatten().to(torch.int32)
        self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root.view(-1,13)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids))
        self.gym.set_dof_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.dof.view(-1,2)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids))
        if s:
            for i in ids.tolist():
                hand_friction=float(self.rng.uniform(.65,1.15));knife_friction=float(self.rng.uniform(1.8,3.4))
                if 'material' in self.disabled_perturbations:hand_friction=1.;knife_friction=3.
                for actor,value in [(self.robots[i],hand_friction),(self.knives[i],knife_friction)]:
                    shapes=self.gym.get_actor_rigid_shape_properties(self.envs[i],actor)
                    for shape in shapes:shape.friction=value
                    self.gym.set_actor_rigid_shape_properties(self.envs[i],actor,shapes)
                self.material_tensor[i]=self.tensor([hand_friction,knife_friction])
                self.actual_materials[str(i)]={'hand':hand_friction,'knife':knife_friction}
        if self.load_profile=='mixed':
            self.load_profile_ids[ids]=torch.randint(0,4,(k,),device=self.device)
            self.load_frequencies[ids]=1.3+torch.rand(k,device=self.device)
        self.bridge.reset(ids,self.opened_batch[ids],self.opened_batch[ids],self.cal_object[ids],self.cal_slider[ids])
        self.peak[ids]=0.;self.max_drift[ids]=0.;self.max_rotation[ids]=0.;self.min_hold_height[ids]=float('inf')
        self.endpoints[ids]=0.;self.contact_steps[ids]=0.;self.operation_steps[ids]=0.;self.closed_at_handover[ids]=False
        self.fell[ids]=False
        self._features=None;self._measurement=None

    def path_targets(self,path,u):
        f=u.clamp(0.,1.)*(len(path)-1);index=f.long().clamp(0,len(path)-2);alpha=(f-index).unsqueeze(-1)
        return path[index]*(1.-alpha)+path[index+1]*alpha

    def prefix_targets(self):
        t=self.age.float()/30;aq=self.approach[0].expand(self.n,-1).clone()
        approach=(t>=2)&(t<5);aq[approach]=self.path_targets(self.approach,smooth((t[approach]-2)/3))
        aq[t>=5]=self.approach[-1]
        lift=(t>=8)&(t<12);aq[lift]=self.path_targets(self.lift,smooth((t[lift]-8)/4));aq[t>=12]=self.lift[-1]
        hq=self.opened.expand(self.n,-1).clone();closing=(t>=5)&(t<8);u=(t[closing]-5)/3
        way=self.plan['close_waypoints'];closed_values=hq[closing].clone()
        for waypoint_index,(first,last) in enumerate(zip(way[:-1],way[1:])):
            selected=(u>=first['fraction'])&(u<=last['fraction'])
            alpha=smooth((u[selected]-first['fraction'])/(last['fraction']-first['fraction'])).unsqueeze(-1)
            first_q=self.close_waypoint_tensors[waypoint_index][closing][selected];last_q=self.close_waypoint_tensors[waypoint_index+1][closing][selected]
            closed_values[selected]=first_q*(1-alpha)+last_q*alpha
        hq[closing]=closed_values;hq[t>=8]=self.closed_batch[t>=8]
        if self.reference.preload_schedule:hq[t>=8]+=self.reference.preload(t)[t>=8]
        if self.support_waypoint_q is not None:
            selected=(t>=self.support_waypoint_times[0])&self.support_waypoint_enabled
            for i,(first,last) in enumerate(zip(self.support_waypoint_times[:-1],self.support_waypoint_times[1:])):
                ids=selected&(t>=first)&(t<last)
                alpha=smooth((t[ids]-first)/(last-first)).unsqueeze(-1)
                hq[ids]=self.support_waypoint_q[ids,i]*(1-alpha)+self.support_waypoint_q[ids,i+1]*alpha
            ids=selected&(t>=self.support_waypoint_times[-1]);hq[ids]=self.support_waypoint_q[ids,-1]
        if self.middle_support is not None:hq=self.middle_support.command(t,self._measurement,hq)
        return aq,hq

    def features(self):
        if self._features is not None:return self._features
        self.refresh();q=self.dof[:,self.hand_ids,0].clone()
        if self.randomization_scale:
            noise=torch.randn_like(q)*(.002*self.randomization_scale)
            if 'sensor' in self.disabled_perturbations:noise.zero_()
            q=q+self.observation_bias+noise
        self._measurement=q;self.bridge.record(q,self.last_action)
        if self.support_load_features is not None:
            self.support_load_features.observe(q,self.command_target[:,self.hand_ids],self.age)
        ready=(self.age==self.takeover_frame).nonzero(as_tuple=False).flatten()
        if len(ready):
            initial_targets=self.command_target if self.resistance_integration=='solver-brake' else self.target
            self.bridge.takeover(ready,q[ready],initial_targets[ready][:,self.hand_ids],self.cal_object[ready],self.cal_slider[ready])
            if self.pressure_adapter is not None:self.pressure_adapter.handover_anchor(ready)
            self.reference.reset(ready,clock_s=self.takeover_frame/30)
            self.reference_pose[ready]=self.rb[ready,self.object_index,:7]
            wrist=self.rb[ready,self.wrist_index]; obj=self.rb[ready,self.object_index]
            inverse=quat_conjugate(wrist[:,3:7])
            self.pickup_reference_in_wrist[ready]=torch.cat([quat_apply(inverse,obj[:,:3]-wrist[:,:3]),quat_mul(inverse,obj[:,3:7])],-1)
        # Reward-only reference transition after an early learned lift. The
        # intended arm lift must not be penalized against the original table
        # pose during 12--16s hold. No actor state or physical state is reset.
        if self.takeover_frame < 360:
            hold_ready=(self.age==360).nonzero(as_tuple=False).flatten()
            self.reference_pose[hold_ready]=self.rb[hold_ready,self.object_index,:7]
        operation_ready=(self.age==480).nonzero(as_tuple=False).flatten()
        if len(operation_ready):
            self.reference_pose[operation_ready]=self.last_held_pose[operation_ready]
            self.closed_at_handover[operation_ready]=(self.dof[operation_ready,27,0]-self.lower[operation_ready]).abs()<.008
        self.policy_active=self.age>=self.takeover_frame
        phase=((self.age-480).clamp_min(0)//150)%2
        self.goal=torch.where((self.age>=480)&(phase==0),torch.full_like(self.load_amplitude,.04),torch.zeros_like(self.load_amplitude))
        public=self.bridge.features(q,self.goal,self.dof[:,self.arm_ids,0],self.policy_active)
        if self.history_features:
            latent=q.new_zeros((self.n,16));ids=self.policy_active.nonzero(as_tuple=False).flatten()
            if len(ids):
                from scripts.wuji_student_interface import legal_history_latent
                latent[ids]=legal_history_latent(self.player.model.a2c_network.priv_encoder,self.bridge.last_encoder_input[ids])
            public=torch.cat([public,latent],-1)
        if self.support_estimator is not None:
            estimate=q.new_zeros((self.n,8));ids=self.policy_active.nonzero(as_tuple=False).flatten()
            if len(ids):estimate[ids]=self.support_estimator(public[ids],self.player.model.a2c_network.priv_encoder,self.bridge.last_encoder_input[ids])
            public=torch.cat([public,estimate],-1)
        wrist=self.rb[:,self.wrist_index];inverse=quat_conjugate(wrist[:,3:7]);obj=self.rb[:,self.object_index];slider=self.rb[:,self.slider_index]
        if self.support_load_features is not None:public=torch.cat([public,self.support_load_features.features()],-1)
        relative_object=torch.cat([quat_apply(inverse,obj[:,:3]-wrist[:,:3]),quat_mul(inverse,obj[:,3:7])],-1)
        relative_slider=torch.cat([quat_apply(inverse,slider[:,:3]-wrist[:,:3]),quat_mul(inverse,slider[:,3:7])],-1)
        travel=self.dof[:,27,0]-self.lower
        passive=self.tensor([.3,.001])[None].expand(self.n,-1)
        truth=torch.cat([relative_object,relative_slider,self.mass_tensor,self.material_tensor[:,1:2],passive,travel[:,None],self.dof[:,27,1:2]],-1)
        assert truth.shape==(self.n,21)
        contact=(self.contact[:,self.pad_indices].norm(dim=-1)>.01).float()
        critic=torch.cat([public,truth,contact,self.load_force[:,None]],-1)
        assert public.shape==(self.n,self.public_dim) and critic.shape==(self.n,self.public_dim+27)
        self._features=(public.detach(),critic.detach())
        return self._features

    def thumb_proximity(self):
        count=len(self.thumb_vertices);pad=self.rb[:,self.pad_indices[0]];slider=self.rb[:,self.slider_index]
        vertices=quat_apply(pad[:,None,3:7].expand(-1,count,-1).reshape(-1,4),self.thumb_vertices[None].expand(self.n,-1,-1).reshape(-1,3)).reshape(self.n,count,3)+pad[:,None,:3]
        inverse=quat_conjugate(slider[:,3:7])
        local=quat_apply(inverse[:,None].expand(-1,count,-1).reshape(-1,4),(vertices-slider[:,None,:3]).reshape(-1,3)).reshape(self.n,count,3)
        distance=(local.abs()-self.slider_half[:,None]).clamp_min(0).norm(dim=-1).amin(-1)
        contact=(self.contact[:,self.pad_indices[0]].norm(dim=-1)>.01).float()
        return torch.exp(-(distance/.003).square())*contact

    def step(self,residual,action_scale=None,reset_failed=True,reset_finished=True):
        self.features()
        if action_scale is None:action_scale=self.scale
        active=self.policy_active.clone();oldage=self.age.clone();operation_active=oldage>=480
        base=self.reference.action(self.bridge.known.initial,self.bridge.known.issued,self.goal,measured_q=self._measurement,clock_s=self.age.float()/30)
        if self.action_parameterization=='bounded-motor-offset':
            from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action
            proposed=bounded_motor_residual_action(self.reference.last_target,self.bridge.known,residual,action_scale)
        else:proposed=(base+action_scale*torch.tanh(residual)).clamp(-1,1)
        proposed=torch.where(active[:,None],proposed,torch.zeros_like(proposed))
        executed=torch.where(self.delay[:,None],self.delayed_action,proposed)
        self.delayed_action=proposed.detach().clone();executed=torch.where(active[:,None],executed,torch.zeros_like(executed))
        if self.resistance_integration=='solver-brake':executed=proposed
        aq,hq=self.prefix_targets()
        ids=active.nonzero(as_tuple=False).flatten()
        pressure_desired=None
        if self.pressure_adapter is not None:
            pressure_desired=hq.clone()
            proposed_targets=self.bridge.known.initial+.04*executed
            proposed_targets[:,16:]=self.bridge.known.issued[:,16:]+.025*executed[:,16:]
            pressure_desired[ids]=proposed_targets[ids]
            adjusted=self.pressure_adapter.command(self._measurement,self.command_target[:,self.hand_ids],pressure_desired,self.age.float()/30)
            hq[~active]=adjusted[~active]
            converted=(adjusted-self.bridge.known.initial)/.04
            converted[:,16:]=(adjusted[:,16:]-self.bridge.known.issued[:,16:])/.025
            executed=torch.where(active[:,None],converted.clamp(-1,1),torch.zeros_like(executed))
        if len(ids):
            # Update the same independent issued-target memory used by deployment.
            predicted=self.bridge.known.step(executed)
            hq[ids]=predicted[ids]
            if self.pressure_adapter is not None:
                self.pressure_adapter.offset[ids]=predicted[ids,16:]-pressure_desired[ids,16:]+self.pressure_adapter.anchor[ids]
        self.target[:,self.arm_ids]=aq;self.target[:,self.hand_ids]=hq
        self.target=torch.minimum(torch.maximum(self.target,self.limitlow),self.limithi)
        self.bridge.known.issued[~active]=self.target[~active][:,self.hand_ids]
        if self.resistance_integration=='solver-brake':
            # Record commands when issued. Unknown physical latency delays
            # their application, never improves the actor's command memory.
            self.command_target=self.target.clone()
            self.target=torch.where(self.delay[:,None],self.delayed_target,self.command_target)
            self.delayed_target=self.command_target.clone()
        self.last_action=executed.detach().clone();self.bridge.last_action=self.last_action.clone()
        previous_error=(self.dof[:,27,0]-self.lower-self.goal).abs()
        for substep in range(8):
            self.refresh()
            gravity=(self.jac[:,:,2,:]*self.masses[None,:,None]*9.81).sum(1)
            torque=self.kp*(self.target-self.dof[:,:27,0])-self.kd*self.dof[:,:27,1]+gravity
            self.forces[:,:27]=torch.maximum(torch.minimum(torque,self.effort),-self.effort)
            v=self.dof[:,27,1];q=self.dof[:,27,0]-self.lower;t=oldage.float()/30+substep/240
            angle=self.load_frequencies*t+self.load_phase
            factor=.25+.75*torch.sin(angle).square()
            factor=torch.where(self.load_profile_ids==0,torch.ones_like(factor),factor)
            triangle=.25+.75*(2*torch.remainder(angle/(2*np.pi),1)-1).abs()
            factor=torch.where(self.load_profile_ids==2,triangle,factor)
            pulse=torch.where(torch.sin(angle)>.5,torch.ones_like(factor),torch.full_like(factor,.25))
            factor=torch.where(self.load_profile_ids==3,pulse,factor)
            amplitude=self.load_amplitude*factor
            run=-amplitude*torch.tanh(v/.002)
            start=-self.detent_amplitude*torch.sin((q/.004).clamp(0,1)*np.pi)*((q>=0)&(q<=.004)).float()
            x=(q-.021)/.0015
            groove=-self.detent_amplitude*np.pi*.5*torch.sin(np.pi*x)*(x.abs()<1).float()
            self.load_force=run+start+groove;self.forces[:,27]=self.load_force
            if self.resistance_integration=='solver-brake':
                from scripts.wuji_passive_solver_brake import brake_capacity_numpy
                capacity=brake_capacity_numpy(q.detach().cpu().numpy(),t.detach().cpu().numpy(),self.load_amplitude.cpu().numpy(),self.detent_amplitude.cpu().numpy(),self.load_frequencies.cpu().numpy(),self.load_phase.cpu().numpy(),self.load_profile_ids.cpu().numpy())
                for i,value in enumerate(capacity):
                    properties=self.slider_drive_properties[i];properties['effort'][:]=max(float(value),1e-8);self.gym.set_actor_dof_properties(self.envs[i],self.knives[i],properties)
                self.load_force=q.new_tensor(capacity);self.forces[:,27]=0.
            self.gym.set_dof_actuation_force_tensor(self.sim,gymtorch.unwrap_tensor(self.forces.flatten()))
            self.gym.simulate(self.sim);self.gym.fetch_results(self.sim,True)
        self.refresh();obj=self.rb[:,self.object_index];height=obj[:,2]-self.origins[:,2]
        time_after=(oldage.float()+1)/30;held=(time_after>=12)&(time_after<16)
        self.min_hold_height[held]=torch.minimum(self.min_hold_height[held],height[held])
        self.last_held_pose[held]=obj[held,:7]
        travel=self.dof[:,27,0]-self.lower;error=(travel-self.goal).abs()
        drift=(obj[:,:3]-self.reference_pose[:,:3]).norm(dim=-1)
        rotation=2*torch.asin(quat_mul(obj[:,3:7],quat_conjugate(self.reference_pose[:,3:7]))[:,:3].norm(dim=-1).clamp(0,1))
        contact=(self.contact[:,self.pad_indices].norm(dim=-1)>.01).float();proximity=self.thumb_proximity()
        reward_proximity=proximity*(self.contact[:,self.slider_index].norm(dim=-1)>.01).float() if self.strong_slider_contact_reward else proximity
        thumb_reward=reward_proximity if self.functional_thumb_reward or self.strong_slider_contact_reward else contact[:,0]
        progress_reward=2*torch.exp(-(error/.012).square())
        if self.stable_progress_reward:
            # The original demo rejects >10mm drift or >.25rad rotation.
            # Do not pay the primary reach bonus while operation violates
            # those same instantaneous conditions. Truth is reward-only;
            # leave physics, actor inputs, termination and full criteria alone.
            unstable_operation=operation_active&((drift>=.01)|(rotation>=.25))
            progress_reward=torch.where(unstable_operation,torch.zeros_like(progress_reward),progress_reward)
        reward=progress_reward+.25*thumb_reward+.1*contact[:,1:].sum(-1)-40*drift.clamp(0,.10)-4*rotation.clamp(0,1.5)-.02*executed.square().mean(-1)
        if self.contact_progress_reward:
            gate=torch.exp(-(drift/.01).square()-(rotation/.25).square())
            reward+=self.contact_progress_reward*reward_proximity*gate*((previous_error-error)/.002).clamp(-1,1)
        # During the actual 8--12s lift, reward physical object retention
        # relative to the wrist. These simulator states are critic/reward only;
        # actor still sees exactly measured/known public features.
        pickup_active=active&(oldage<360)
        if bool(pickup_active.any()):
            wrist=self.rb[:,self.wrist_index]; inverse=quat_conjugate(wrist[:,3:7])
            relative=torch.cat([quat_apply(inverse,obj[:,:3]-wrist[:,:3]),quat_mul(inverse,obj[:,3:7])],-1)
            pd=(relative[:,:3]-self.pickup_reference_in_wrist[:,:3]).norm(dim=-1)
            pr=2*torch.asin(quat_mul(relative[:,3:7],quat_conjugate(self.pickup_reference_in_wrist[:,3:7]))[:,:3].norm(dim=-1).clamp(0,1))
            pickup_reward=2*torch.exp(-(pd/.012).square())+.1*contact[:,1:].sum(-1)-40*pd.clamp(0,.1)-4*pr.clamp(0,1.5)-.02*executed.square().mean(-1)
            reward=torch.where(pickup_active,pickup_reward,reward)
        reward=torch.where(active,reward,torch.zeros_like(reward))
        self.peak[operation_active]=torch.maximum(self.peak[operation_active],travel[operation_active])
        self.max_drift[operation_active]=torch.maximum(self.max_drift[operation_active],drift[operation_active])
        self.max_rotation[operation_active]=torch.maximum(self.max_rotation[operation_active],rotation[operation_active])
        self.contact_steps[operation_active]+=(proximity[operation_active]>.5).float();self.operation_steps[operation_active]+=1
        dropped=active&(oldage>=360)&(height<.78)
        self.fell|=dropped
        failure_reward=torch.full_like(reward,-8.)
        if self.absorbing_failure_penalty:
            # Equivalent discounted future reward -1 per remaining control
            # frame in an absorbing failed state, without simulating dead time.
            remaining=(1080-oldage-1).clamp_min(0).float()
            failure_reward-=.995*(1.-torch.pow(.995,remaining))/.005
        reward=torch.where(dropped,failure_reward,reward)
        phase=((oldage-480).clamp_min(0)//150).clamp(0,3)
        sample=operation_active&(((oldage-480)%150)>=141)&(oldage<1080)
        sampled=sample.nonzero(as_tuple=False).flatten()
        if len(sampled):self.endpoints[sampled,phase[sampled]]+=travel[sampled]/9
        self.age+=1;self.transitions+=self.n
        finished=self.age>=1080
        done=finished|(dropped if reset_failed else torch.zeros_like(dropped))
        complete_ids=done.nonzero(as_tuple=False).flatten()
        for i in complete_ids.tolist():
            ends=self.endpoints[i].detach().cpu().tolist();fraction=float(self.contact_steps[i]/self.operation_steps[i].clamp_min(1))
            pickup=bool(self.min_hold_height[i]>.78) and bool(self.closed_at_handover[i])
            stable=not bool(self.fell[i]) and float(self.max_drift[i])<.01 and float(self.max_rotation[i])<.25
            extend=all(x>.025 for x in [ends[0],ends[2]]);retract=all(x<.008 for x in [ends[1],ends[3]])
            success=bool(finished[i]) and pickup and stable and extend and retract and fraction>=.9
            self.stats.append(dict(episode=self.episodes,env=i,instance=self.instances[i%len(self.instances)],control_steps=int(self.age[i]),pickup_valid=pickup,fall=bool(self.fell[i]),operation_complete=success,endpoints_m=ends,peak_extension_m=float(self.peak[i]),max_body_drift_m=float(self.max_drift[i]),max_body_rotation_rad=float(self.max_rotation[i]),thumb_contact_fraction=fraction,scope='Actual G2 continuous training episode; proximity/net-contact proxy, not exact contact pair or independent validation',failure=None if success else 'pickup/hold' if not pickup else 'body unstable/drop' if not stable else 'extension' if not extend else 'retraction' if not retract else 'thumb-contact'))
            self.episodes+=1
        self.last_diagnostics=dict(slider=travel.detach().clone(),height=height.detach().clone(),rotation=rotation.detach().clone(),drift=drift.detach().clone(),proximity=proximity.detach().clone(),action=executed.detach().clone(),q=self.dof[:,self.hand_ids,0].detach().clone(),arm_q=self.dof[:,self.arm_ids,0].detach().clone(),target=self.target.detach().clone(),issued_target=self.command_target.detach().clone() if self.resistance_integration=='solver-brake' else self.target.detach().clone(),object=obj.detach().clone(),wrist=self.rb[:,self.wrist_index].detach().clone(),load=self.load_force.detach().clone(),age=oldage.detach().clone())
        self._features=None;self._measurement=None
        reset_ids=(done if reset_finished else done&~finished).nonzero(as_tuple=False).flatten()
        if len(reset_ids):self.reset(reset_ids)
        return reward.detach(),done

    def close(self):self.gym.destroy_sim(self.sim)
