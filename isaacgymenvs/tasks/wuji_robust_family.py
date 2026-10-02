"""Near-real family physics, continuing original legal-input observation/control.

All perturbation bounds are engineering assumptions, not measured hardware.
Training begins in proxy functional grasps; no claim of continuous acquisition.
"""
import json, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import torch
from isaacgym import gymapi,gymtorch
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere
from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
from isaacgymenvs.utils.torch_jit_utils import quat_mul,quat_apply,quat_conjugate
ROOT=Path(__file__).resolve().parents[2]

class WujiRobustFamily(WujiBridge3Hemisphere):
    def __init__(self,cfg,*args,**kwargs):
        self.robust_ready=False
        self.hemisphere_reference=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy')[0,43:47].copy()
        WujiVariableTimedAcquisition.__init__(self,cfg,*args,**kwargs)
        n=self.num_envs;device=self.device
        self.load_amplitude=torch.zeros(n,device=device);self.load_phase=torch.zeros(n,device=device)
        self.detent_amplitude=torch.zeros(n,device=device);self.detent_center=torch.zeros(n,device=device)
        self.observation_bias=torch.zeros((n,20),device=device);self.calibration_translation=torch.zeros((n,3),device=device)
        self.calibration_angle=torch.zeros((n,4),device=device);self.delay=torch.zeros(n,device=device,dtype=torch.bool)
        self.delayed_action=torch.zeros((n,20),device=device);self.delay_probability=float(cfg['env'].get('robustDelayProbability',.15))
        self.load_max=float(cfg['env'].get('robustLoadMaxN',.10));self.detent_max=float(cfg['env'].get('robustDetentMaxN',.10))
        self.load_profile=cfg['env'].get('robustLoadProfile','sinusoidal');self.load_frequency=float(cfg['env'].get('robustLoadFrequency',1.7))
        assert self.load_profile in ['sinusoidal','triangular','pulse','constant','mixed'] and self.load_frequency>0
        self.load_profile_index=torch.zeros(n,device=device,dtype=torch.long)
        self.randomization_scale=float(cfg['env'].get('robustRandomizationScale',1.))
        self.wrist_nominal=torch.tensor(cfg['env'].get('robustWristNominalQuaternion',[0.,0.,0.,1.]),device=device)
        self.wrist_nominal=self.wrist_nominal/self.wrist_nominal.norm()
        self.wrist_nominal_probability=float(cfg['env'].get('robustWristNominalProbability',0.))
        self.load_work=torch.zeros(n,device=device);self.load_force=torch.zeros(n,device=device)
        self.detent_potential=torch.zeros(n,device=device);self.reset_counts=torch.zeros(n,device=device,dtype=torch.long)
        self.gravity_vector=torch.zeros((n,3),device=device)
        profile_file=cfg['env'].get('robustHandoverProfileFile')
        self.handover_profiles=None
        self.handover_profile_index=torch.full((n,),-1,device=device,dtype=torch.long)
        self.handover_velocity_scale=torch.zeros(n,device=device)
        if profile_file:
            profiles=json.loads((ROOT/profile_file).read_text())['profiles']
            self.handover_profiles=torch.tensor([p['wrist_quaternion_xyzw']+p['object_relative_linear_velocity_m_s']+p['object_relative_angular_velocity_rad_s'] for p in profiles],device=device,dtype=torch.float32)
        self.measurement_noise=torch.zeros((n,20),device=device);self.measurement_step=-1
        self.hand_jac=gymtorch.wrap_tensor(self.gym.acquire_jacobian_tensor(self.sim,'hand'))
        props=self.gym.get_actor_rigid_body_properties(self.envs[0],self.hand_handles[0]) if hasattr(self,'hand_handles') else self.gym.get_actor_rigid_body_properties(self.envs[0],self.gym.find_actor_handle(self.envs[0],'hand'))
        self.hand_body_masses=torch.tensor([p.mass for p in props][1:],device=device)
        for env in self.envs:
            handle=self.gym.find_actor_handle(env,'hand');ps=self.gym.get_actor_rigid_body_properties(env,handle)
            for p in ps:p.flags=0
            self.gym.set_actor_rigid_body_properties(env,handle,ps,False)
        self.robust_ready=True;self.press_physics_substep=self._passive_substep
        self.reset_idx(torch.arange(n,device=device))

    def _select_instance_index(self,env_id):
        return env_id%len(self.instance_id_list)

    def _create_envs(self,*args,**kwargs):
        super()._create_envs(*args,**kwargs)
        for i,(env,handle) in enumerate(zip(self.envs,self.object_handles)):
            instance=self.instance_id_list[i%len(self.instance_id_list)]
            xml=ET.parse(ROOT/self.object_cfg['asset']['asset_root']/instance/'mobility.urdf')
            props=self.gym.get_actor_rigid_body_properties(env,handle)
            for body,name in zip(props,['link_0','link_1']):
                node=xml.find(f"./link[@name='{name}']/inertial");body.mass=float(node.find('mass').get('value'))
                inertia=node.find('inertia')
                for row,key in zip(['x','y','z'],['ixx','iyy','izz']):setattr(getattr(body.inertia,row),row,float(inertia.get(key)))
            self.gym.set_actor_rigid_body_properties(env,handle,props,False)

    def sample_grasps(self,ids):
        result=super().sample_grasps(ids)
        if not self.robust_ready:return result
        result=result.clone();s=self.randomization_scale
        delta=(torch.rand_like(result[:,:20])-.5)*.03*s
        result[:,:20]=torch.maximum(torch.minimum(result[:,:20]+delta,self.hand_dof_upper_limits),self.hand_dof_lower_limits)
        result[:,20:40]=torch.maximum(torch.minimum(result[:,20:40]+delta,self.hand_dof_upper_limits),self.hand_dof_lower_limits)
        translation=(torch.rand((len(ids),3),device=self.device)-.5)*.002*s
        result[:,40:43]+=translation;result[:,47:50]+=translation
        return result

    def reset_idx(self,ids,goal_env_ids=None):
        if self.robust_ready:
            n=len(ids);d=self.device;s=self.randomization_scale
            self.load_amplitude[ids]=torch.rand(n,device=d)*self.load_max*s
            self.load_phase[ids]=torch.rand(n,device=d)*6.283185
            if self.load_profile=='mixed':self.load_profile_index[ids]=torch.randint(4,(n,),device=d)
            self.detent_amplitude[ids]=torch.rand(n,device=d)*self.detent_max*s
            self.detent_center[ids]=torch.rand(n,device=d)*.025+.006
            self.measurement_noise[ids]=torch.randn((n,20),device=d)*(.002*s)
            self.observation_bias[ids]=(torch.rand((n,20),device=d)-.5)*.012*s
            self.calibration_translation[ids]=(torch.rand((n,3),device=d)-.5)*.002*s
            angle=(torch.rand((n,3),device=d)-.5)*np.deg2rad(3)*s
            norm=angle.norm(dim=-1,keepdim=True);self.calibration_angle[ids]=torch.cat([angle/(norm+1e-9)*torch.sin(norm/2),torch.cos(norm/2)],-1)
            self.delay[ids]=torch.rand(n,device=d)<self.delay_probability;self.delayed_action[ids]=0
            self.load_work[ids]=0;self.reset_counts[ids]+=1
            # Rotate fixed wrist at episode reset; actual object is transformed by inherited local-cache reset.
            rot=(torch.rand((n,3),device=d)-.5)*np.deg2rad(30)*s
            norm=rot.norm(dim=-1,keepdim=True);q=torch.cat([rot/(norm+1e-9)*torch.sin(norm/2),torch.cos(norm/2)],-1)
            if self.wrist_nominal_probability>0:
                use_acquired=torch.rand(n,device=d)<self.wrist_nominal_probability
                nominal=self.wrist_nominal.expand(n,-1)
                q=torch.where(use_acquired[:,None],quat_mul(nominal,q),q)
            if self.handover_profiles is not None:
                profile_ids=torch.randint(len(self.handover_profiles),(n,),device=d)
                self.handover_profile_index[ids]=profile_ids
                q=quat_mul(self.handover_profiles[profile_ids,:4],torch.cat([rot/(norm+1e-9)*torch.sin(norm/2),torch.cos(norm/2)],-1))
            self.root_state_tensor[self.hand_indices[ids],3:7]=q
            indices=self.hand_indices[ids].to(torch.int32)
            self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root_state_tensor),gymtorch.unwrap_tensor(indices),len(indices))
            self.gravity_vector[ids]=quat_apply(quat_conjugate(q),torch.tensor([0.,0.,-1.],device=d).expand(n,-1))
            # PhysX combines the two materials; both authored coefficients are saved.
            self.actual_material_coefficients=getattr(self,'actual_material_coefficients',{})
            for index in ids.tolist():
                env=self.envs[index];obj=self.object_handles[index];hand=self.gym.find_actor_handle(env,'hand')
                mu_hand=float(torch.empty((),device=d).uniform_(.7,1.3));mu_obj=float(torch.empty((),device=d).uniform_(1.5,3.0))
                for actor,mu in [(hand,mu_hand),(obj,mu_obj)]:
                    ps=self.gym.get_actor_rigid_shape_properties(env,actor)
                    for p in ps:p.friction=mu
                    self.gym.set_actor_rigid_shape_properties(env,actor,ps)
                self.actual_material_coefficients[index]=[mu_hand,mu_obj]
        super().reset_idx(ids,goal_env_ids)
        if self.robust_ready and self.handover_profiles is not None:
            profile=self.handover_profiles[self.handover_profile_index[ids]]
            scale=torch.where(torch.rand(len(ids),device=self.device)<.25,torch.zeros(len(ids),device=self.device),.5+.5*torch.rand(len(ids),device=self.device))
            self.handover_velocity_scale[ids]=scale
            wrist=self.root_state_tensor[self.hand_indices[ids],3:7]
            self.root_state_tensor[self.object_indices[ids],7:10]=quat_apply(wrist,profile[:,4:7]*scale[:,None])
            self.root_state_tensor[self.object_indices[ids],10:13]=quat_apply(wrist,profile[:,7:10]*scale[:,None])
            indices=self.object_indices[ids].to(torch.int32)
            self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root_state_tensor),gymtorch.unwrap_tensor(indices),len(indices))

    def _get_hand_proprio_obs(self,env_ids=None):
        if not self.robust_ready:return super()._get_hand_proprio_obs(env_ids)
        if self.measurement_step!=self.control_steps:
            self.measurement_noise=torch.randn_like(self.hand_dof_pos)*(.002*self.randomization_scale);self.measurement_step=self.control_steps
        q=self.hand_dof_pos+self.observation_bias+self.measurement_noise
        normalized=2*(q-self.hand_dof_lower_limits)/(self.hand_dof_upper_limits-self.hand_dof_lower_limits)-1
        return normalized if env_ids is None else normalized[env_ids]

    def _compute_sapg_priv_observations(self):
        pol,pri=super()._compute_sapg_priv_observations()
        if not self.robust_ready:return pol,pri
        pol=pol.clone();pol[:,20:23]+=self.calibration_translation;pol[:,27:30]+=self.calibration_translation
        # Already in the actor's acquisition frame; rotate estimate in wrist coordinates.
        for start in [23,30]:pol[:,start:start+4]=quat_mul(self.calibration_angle,pol[:,start:start+4])
        pol[:,55:75]=self._get_hand_proprio_obs()
        return pol,pri

    def pre_physics_step(self,action):
        # Delay changes the actual issued action; history and known-controller memory use that action.
        super().pre_physics_step(action)

    def delayed(self,action):
        answer=torch.where(self.delay[:,None],self.delayed_action,action)
        self.delayed_action=action.clone();return answer

    def _passive_substep(self,substep):
        self.gym.refresh_dof_state_tensor(self.sim);self.gym.refresh_jacobian_tensors(self.sim)
        v=self.obj_dof_state_vel[:,0];q=self.obj_dof_state[:,0,0]-self.init_obj_dof_pos[:,0]
        t=self.progress_buf.float()*self.dt*self.control_freq_inv+substep*self.dt
        phase=self.load_frequency*t+self.load_phase
        sine=.25+.75*torch.sin(phase).square()
        triangular=.25+.75*(2*torch.remainder(phase/(2*np.pi),1)-1).abs()
        pulse=torch.where(torch.sin(phase)>.5,torch.ones_like(phase),torch.full_like(phase,.25))
        if self.load_profile=='mixed':factor=torch.where(self.load_profile_index==0,sine,torch.where(self.load_profile_index==1,triangular,torch.where(self.load_profile_index==2,pulse,torch.ones_like(phase))))
        else:factor={'sinusoidal':sine,'triangular':triangular,'pulse':pulse,'constant':torch.ones_like(phase)}[self.load_profile]
        amplitude=self.load_amplitude*factor
        run_force=-amplitude*torch.tanh(v/.002)
        # Smooth finite potential wells: nonzero breakaway force near a groove shoulder.
        # Independent passive potential stores energy, so instantaneous positive power on descent is physical.
        width=.0015;x=(q-self.detent_center)/width
        potential=self.detent_amplitude*width*.5*(1-torch.cos(3.14159265*x.clamp(-1,1)))
        detent=-self.detent_amplitude*3.14159265*.5*torch.sin(3.14159265*x)*((x.abs()<1).float())
        start=-self.detent_amplitude*torch.sin((q/.004).clamp(0,1)*3.14159265)*((q>=0)&(q<=.004)).float()
        self.load_force=run_force+detent+start;self.detent_potential=potential
        self.load_work+=run_force*v*self.dt
        self.dof_actuation_forces.zero_()
        # Generalized robot weight compensation; finite PD still enforces original motor gains/effort limits.
        gravity=(self.hand_jac[:,:,2,:]*self.hand_body_masses[None,:,None]*9.81).sum(1)
        self.dof_actuation_forces[:,:20]=gravity
        self.dof_actuation_forces[:,20]=self.load_force
        self.gym.set_dof_actuation_force_tensor(self.sim,gymtorch.unwrap_tensor(self.dof_actuation_forces))
