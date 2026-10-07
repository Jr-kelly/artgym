"""Short reference-guided, contact-changing in-hand training (sim_oracle).

All 27 motor targets and reference timing are controllable. Actual carried
recording initializes training episodes only, with the missing solver cache
and estimated velocities disclosed. Fresh native execution is the final test.
"""
import json
from pathlib import Path
import numpy as np
from scripts.g2_continuous_scene import G2ContinuousScene
from isaacgym import gymtorch
import torch
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul,quat_conjugate
from scipy.spatial.transform import Rotation
from scripts.wuji_regrasp_contract import phase_increment, entry_progress_reward


class RegraspLearning(G2ContinuousScene):
    def __init__(self,n,source,reference,seed=20261008717):
        self.ready=False;self.recorded=np.load(Path(source)/'takeover.npz')
        self.recipe=json.loads(Path(reference).read_text())
        scene=json.loads(Path('runs/flat-table-20261006/learning/real-prefix-v76/scene.json').read_text())
        scene=dict(scene,nominal_hand_friction=.8,nominal_knife_friction=1.8,
                   newknife_resistance=json.loads(Path('research/newknife-20261005/resistance-constant.json').read_text()),
                   compact_isolated_layout=True)
        super().__init__(n=n,seed=seed,randomization_scale=0.,instances=['newknife']*n,load_max=0.,detent_max=0.,
                         scene_spec=scene,reference_spec=json.loads(Path('runs/newknife-20261005/preparation/center-tail-support-v2/reference.json').read_text()),
                         asset_registry={'newknife':'assets/objects/knife_wuji_newknife_20261005/nominal-v5'},
                         resistance_integration='solver-brake',compact_isolated_layout=True)
        assert self.newknife_resistance['kind']=='constant'
        for i,props in enumerate(self.slider_drive_properties):
            props['effort'][:]=float(self.newknife_resistance['reference_N'])
            self.gym.set_actor_dof_properties(self.envs[i],self.knives[i],props)
        self.motor_reference=self.tensor([r['arm_q']+r['hand_q'] for r in self.recipe['rows']])
        L=np.asarray(self.recipe['target_object_in_wrist']);self.goal_relative=self.tensor(np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_quat()])
        self.goal_q=self.tensor(self.recipe['target_hand_q'])
        self.offset=torch.zeros((n,27),device=self.device);self.last=self.offset.clone()
        self.span=self.tensor([.20]*7+[.60]*20);self.slew=self.tensor([.006]*7+[.025]*20)
        self.phase=torch.zeros(n,device=self.device);self.steps=240
        self.ready=True;self.reset(torch.arange(n,device=self.device),perturb=False)

    def reset(self,ids,perturb=True):
        if not self.ready:return super().reset(ids)
        assert len(ids)==self.n
        z=self.recorded;k=len(ids)
        self.target[ids]=self.tensor(z['issued_target'][:27]);self.command_target[ids]=self.target[ids]
        self.dof[ids,:27,0]=self.tensor(z['robot_q']);self.dof[ids,:27,1]=self.tensor(z['estimated_robot_velocity'])
        self.dof[ids,27,0]=float(z['slider_q']);self.dof[ids,27,1]=float(z['slider_velocity'])
        self.root[ids,0,:]=0.;self.root[ids,0,6]=1.;self.root[ids,2,:]=self.tensor(z['object_state'])
        if perturb:
            # Mild physical pose variation, never a changed contact asset.
            self.root[ids,2,:3]+=(torch.rand((k,3),device=self.device)-.5)*.0006
            self.dof[ids,:27,0]+=(torch.rand((k,27),device=self.device)-.5)*.002
        actor_ids=torch.stack([ids*3,ids*3+2],-1).flatten().to(torch.int32)
        self.gym.set_actor_root_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.root.view(-1,13)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids))
        self.gym.set_dof_state_tensor_indexed(self.sim,gymtorch.unwrap_tensor(self.dof.view(-1,2)),gymtorch.unwrap_tensor(actor_ids),len(actor_ids))
        self.age[ids]=0;self.phase[ids]=0;self.offset[ids]=0;self.last[ids]=0
        self.failed=torch.zeros(self.n,device=self.device,dtype=torch.bool);self.entry_frames=torch.zeros(self.n,device=self.device)
        self.best_entry_error=torch.full((self.n,),float('inf'),device=self.device);self.refresh()
        # One real held-target frame updates native FK/contact tensors after
        # the new-episode setter. Refresh alone does not recompute body poses.
        self.servo(self.target)
        self.previous_potential=torch.zeros(self.n,device=self.device)
        self.best_entry_dwell=torch.zeros(self.n,device=self.device)
        self.entry_awarded=torch.zeros(self.n,device=self.device,dtype=torch.bool)
        self.held_frames=torch.zeros(self.n,device=self.device)
        self.max_held_frames=torch.zeros(self.n,device=self.device)
        self.pause_steps=torch.zeros(self.n,device=self.device)
        self.previous_potential=self.entry_metrics()['potential']
        return self.observation()

    def relative(self):
        w=self.rb[:,self.wrist_index];o=self.rb[:,self.object_index];inv=quat_conjugate(w[:,3:7])
        return torch.cat([quat_apply(inv,o[:,:3]-w[:,:3]),quat_mul(inv,o[:,3:7])],-1)

    def guide_targets(self):
        ix=self.phase.clamp(max=len(self.motor_reference)-1.0001);a=ix.long();f=(ix-a)[:,None]
        return self.motor_reference[a]*(1-f)+self.motor_reference[a+1]*f

    def contact_features(self):
        ids=[[i for i,n in enumerate(self.rb_names) if '_'+f+'_' in n] for f in ['thumb','index','middle','ring','pinky']]
        return torch.stack([self.contact[:,ix].norm(dim=-1).sum(-1) for ix in ids],-1).clamp(max=3.)/3.

    def observation(self):
        rel=self.relative();goal=self.goal_relative.expand(self.n,-1).clone()
        goal[:,3:]*=torch.where((goal[:,3:]*rel[:,3:]).sum(-1,keepdim=True)<0,-1.,1.)
        q=self.dof[:,:27,0]
        return torch.cat([q,self.dof[:,:27,1]*.05,self.command_target-q,self.offset,rel[:,:3]*10,rel[:,3:],
                          goal[:,:3]*10,goal[:,3:],self.goal_q.expand(self.n,-1),
                          (self.phase/(len(self.motor_reference)-1))[:,None],self.age[:,None]/self.steps,self.contact_features()],-1)

    def servo(self,motor):
        self.target=torch.minimum(torch.maximum(motor,self.limitlow),self.limithi);self.command_target=self.target.clone()
        for _ in range(8):
            self.refresh();gravity=(self.jac[:,:,2,:]*self.masses[None,:,None]*9.81).sum(1)
            torque=self.kp*(self.target-self.dof[:,:27,0])-self.kd*self.dof[:,:27,1]+gravity
            self.forces[:,:27]=torch.maximum(torch.minimum(torque,self.effort),-self.effort);self.forces[:,27]=0.
            self.gym.set_dof_actuation_force_tensor(self.sim,gymtorch.unwrap_tensor(self.forces.flatten()))
            self.gym.simulate(self.sim);self.gym.fetch_results(self.sim,True)
        self.refresh()

    def entry_metrics(self):
        rel=self.relative();pos=(rel[:,:3]-self.goal_relative[:3]).norm(dim=-1)
        dot=(rel[:,3:]*self.goal_relative[3:]).sum(-1).abs().clamp(max=1.)
        rot=2*torch.acos(dot);qerr=(self.dof[:,self.hand_ids,0]-self.goal_q).square().mean(-1).sqrt()
        obj=self.rb[:,self.object_index];R=quat_apply(obj[:,3:7],self.tensor([0,0,1]).expand(self.n,-1))
        Y=quat_apply(obj[:,3:7],self.tensor([0,1,0]).expand(self.n,-1));X=quat_apply(obj[:,3:7],self.tensor([1,0,0]).expand(self.n,-1))
        clear=obj[:,2]-.75-R[:,2].abs()*.072-Y[:,2].abs()*.004-X[:,2].abs()*.0095
        held=(clear>.025)&(obj[:,7:10].norm(dim=-1)<.3)
        finite=torch.isfinite(self.dof).all(-1).all(-1)&torch.isfinite(rel).all(-1)
        held=held&finite&~self.failed
        error=pos/.025+rot/.6+qerr/.5
        potential=torch.where(held,torch.exp(-error),torch.zeros_like(error))
        return dict(position_m=pos,rotation_rad=rot,q_rms_rad=qerr,clearance_m=clear,
                    held=held,finite=finite,error=error,potential=potential)

    def step(self,action):
        action=action.detach().clamp(-1,1)
        self.offset+=(action[:,:27]*self.span-self.offset).clamp(-self.slew,self.slew)
        advance=phase_increment(action[:,27])
        self.pause_steps+=(advance==0).float()
        self.phase=(self.phase+advance).clamp(max=len(self.motor_reference)-1.0001)
        self.servo(self.guide_targets()+self.offset);self.age+=1
        m=self.entry_metrics();held=m['held']
        self.failed|=(m['clearance_m']<.01)|~m['finite']
        held=held&~self.failed
        entry=held&(m['position_m']<.012)&(m['rotation_rad']<.25)&(m['q_rms_rad']<.20)
        self.entry_frames=torch.where(entry,self.entry_frames+1,torch.zeros_like(self.entry_frames))
        dwell=self.entry_frames.clamp(max=30)
        new_dwell=(dwell-self.best_entry_dwell).clamp(min=0)
        self.best_entry_dwell=torch.maximum(self.best_entry_dwell,dwell)
        first_entry=(self.entry_frames>=30)&~self.entry_awarded
        self.entry_awarded|=first_entry
        self.held_frames=torch.where(held,self.held_frames+1,torch.zeros_like(self.held_frames))
        self.max_held_frames=torch.maximum(self.max_held_frames,self.held_frames)
        self.best_entry_error=torch.minimum(self.best_entry_error,torch.where(held,m['error'],torch.full_like(m['error'],float('inf'))))
        potential=torch.where(held,m['potential'],torch.zeros_like(m['potential']))
        reward=entry_progress_reward(self.previous_potential,potential,new_dwell,first_entry.float(),held.float())
        self.previous_potential=potential
        reward-=.08*action[:,:27].square().mean(-1)+.03*(action[:,:27]-self.last).square().mean(-1)
        reward=torch.where(self.failed,torch.full_like(reward,-12),reward);self.last=action[:,:27].clone()
        return self.observation(),reward,self.age>=self.steps,dict(m,entry_frames=self.entry_frames,failed=self.failed,
            phase_increment=advance,max_held_frames=self.max_held_frames,best_entry_dwell=self.best_entry_dwell,
            scope='Entry proximity and stable carrying proxies; load transfer and retained-skill takeover unverified')
