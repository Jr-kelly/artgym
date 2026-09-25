"""Original-hand latent distillation with explicit runtime and checkpoint audits.

Uses the existing student-only online latent-MSE algorithm. This is a bounded
intermediate-teacher reference, not the paper's final model or hardware result.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
from scripts import wuji_goal_common  # Isaac Gym before torch.
import numpy as np
import torch
from scripts import audit_distillation_runtime as audit_module
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now

ACTIVE={}


class SharpaAudit(audit_module.DistillationRuntimeAudit):
    def __init__(self,directory,cfg,args,env,model,teacher_encoder):
        super().__init__(directory,cfg,args,env,model,teacher_encoder)
        assert args.hand=='sharpa' and env.num_hand_dofs==22
        assert args.task=='sharpa_student_upstream' and args.object=='knife_sharpa_official'
        assert env.student_obs_dim==2257 and env.proprio_obs_dim==44
        assert args.cosine_coef==0 and args.lr==.0002 and args.deterministic
        assert args.teacher_rollout_updates==0 and args.teacher_latent_mix_initial==0 and args.action_loss_coef==0
        assert not args.student_rollout_eval_mode and not env.eval_mode
        assert args.grasp_split=='valid' and env.runtime_grasp_split=='valid'
        assert list(cfg.object.asset.instance_id_list)==['%03d'%i for i in range(30)]
        assert cfg.task.env.rewardProtocol=='upstream'
        # Isaac Gym exposes SimParams.dt as float32 (1/120 rounds upward).
        assert env.control_freq_inv==4 and abs(env.dt-1/120)<1e-8 and env.max_episode_length==1200, (
            env.control_freq_inv,env.dt,env.max_episode_length)
        props=env.gym.get_actor_dof_properties(env.envs[0],env.gym.find_actor_handle(env.envs[0],'hand'))
        for name in ['stiffness','damping','armature']:
            assert np.allclose(props[name],cfg.hand.dof_props[name],rtol=1e-6,atol=1e-7),name
        self.env=env;self.student=model.a2c_network.priv_encoder
        initial={n:v.detach().cpu().clone() for n,v in self.student.state_dict().items()}
        self.record.update(sharpa_student=True,student_initial_tensor_sha256=tensor_digest(initial),
            actual_actions=0,restricted_history_checks=0,current_privileged_invariance=0,
            instance_env_counts=torch.bincount(env.env2instance,minlength=30).cpu().tolist(),
            actual_control_dt=env.dt*env.control_freq_inv,actual_episode_steps=env.max_episode_length,
            actual_actuators={k:props[k].tolist() for k in ['stiffness','damping','armature']},
            student_dropout=[m.p for m in self.student.modules() if isinstance(m,torch.nn.Dropout)],
            expected_student_input='50x44 measured joint angles and past actions +57 initial fields; current object/contact values critic-only',
            checkpoint_protocol='Atomic periodic every25 plus initial, first and final; best-loss/reward may atomically replace their own files. Optimizer not serialized by upstream distillation; not exact-resumable.')
        self.write()
        assert min(self.record['instance_env_counts'])>0,self.record['instance_env_counts']
        self.initial=initial;ACTIVE.update(audit=self,initial=initial,output=Path(args.output_checkpoint))
        self.write()

    def observe_player_actions(self,player,teacher_encoder,student_encoder):
        reference_action=player.get_action
        super().observe_player_actions(player,teacher_encoder,student_encoder)
        original_action=player.get_action;env=self.env;expected=[]
        original_pre=env.pre_physics_step
        def pre_step(action):
            original_pre(action)
            assert len(expected)==1 and torch.equal(env.actions,expected[0])
            self.record['actual_actions']+=env.num_envs
        env.pre_physics_step=pre_step
        def observed(obs,*args,**kwargs):
            history=player.model.a2c_network.actor_encoder_obs_override
            direct=torch.cat([env.proprioception_buf.reshape(env.num_envs,-1),env._get_init_obs()],-1)
            assert history.shape==(env.num_envs,2257) and torch.equal(history,direct)
            self.record['restricted_history_checks']+=env.num_envs
            incoming=[v.clone() for v in player.states]
            cpu_rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state(player.device)
            action=original_action(obs,*args,**kwargs)
            outgoing=[v.clone() for v in player.states]
            step=self.record['actual_actions']//env.num_envs
            if step<3 or step%1200==0:
                # Reuse the identical dropout stream for a counterfactual
                # current-privileged/contact input change; no physics occurs.
                with torch.random.fork_rng(devices=[torch.device(player.device).index or 0]):
                    torch.set_rng_state(cpu_rng);torch.cuda.set_rng_state(cuda_rng,player.device)
                    changed=obs.clone();changed[:,117:143]=123.
                    player.states=[v.clone() for v in incoming]
                    wrong=reference_action(changed,*args,**kwargs)
                    assert torch.equal(wrong,action)
                    assert all(torch.equal(a,b) for a,b in zip(player.states[:2],outgoing[:2]))
                    player.states=outgoing
                self.record['current_privileged_invariance']+=env.num_envs
            expected[:]=[action.detach().clone()]
            if step%16==0:
                self.record['heartbeat']=now();self.write()
            return action
        player.get_action=observed

    def finish(self,model,teacher_encoder,student,updates):
        count=updates*self.record['arguments']['rollout_steps']*self.env.num_envs
        assert self.record['actual_actions']==self.record['restricted_history_checks']==count
        assert self.record['rollout_action_transitions']==dict(teacher=0,student=count)
        assert self.record['current_privileged_invariance']>=self.env.num_envs*3
        changed=[n for n,v in student.state_dict().items() if not torch.equal(v.detach().cpu(),self.initial[n])]
        assert changed and any(n.startswith('temporal_model.') for n in changed)
        self.record.update(changed_student_tensors=changed,student_final_tensor_sha256=tensor_digest(student.state_dict()))
        super().finish(model,teacher_encoder,student,updates)


def main():
    from isaacgymenvs import distill
    old_audit=audit_module.DistillationRuntimeAudit
    old_save=distill.save_distilled_checkpoint
    audit_module.DistillationRuntimeAudit=SharpaAudit

    def save(output_path,checkpoint_path,player_model,student_encoder,distill_meta,include_full_model):
        assert not include_full_model
        a=ACTIVE['audit'];args=a.record['arguments']
        update=a.record['actual_actions']//(a.env.num_envs*args['rollout_steps'])
        meta=copy.deepcopy(distill_meta);meta['completed_updates']=update
        meta['sharpa_reference']='Intermediate frozen upstreamCP2100; paperAdam2e-4 latentMSE, originalhand/assets/control, upstreamTCN5percentdropout. Not finalpaper/hardware reproduction.'
        payload=distill.build_output_payload(checkpoint_path,player_model,student_encoder,meta,False)
        target=Path(output_path);target.parent.mkdir(parents=True,exist_ok=True)
        def atomic(path,value,immutable=False):
            if immutable:assert not path.exists(),path
            tmp=path.with_suffix('.tmp');torch.save(value,tmp);os.replace(tmp,path)
            atomic_json(path.with_suffix('.json'),dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),completed_updates=value['distill_meta']['completed_updates'],committed=now()))
        initial=target.parent/'student_update0000.pth'
        if not initial.exists():
            initial_meta=copy.deepcopy(meta);initial_meta.update(updates=0,completed_updates=0,best_loss=None,best_reward=None)
            atomic(initial,dict(student_encoder_state_dict=ACTIVE['initial'],distill_meta=initial_meta),True)
        atomic(target,payload,'_update' in target.stem)
        if update in (1,args['updates']):
            special=target.parent/('student_update%04d.pth'%update)
            if not special.exists():atomic(special,payload,True)
        print(json.dumps(dict(checkpoint=str(target),update=update)),flush=True)

    distill.save_distilled_checkpoint=save
    try:distill.main()
    finally:
        audit_module.DistillationRuntimeAudit=old_audit
        distill.save_distilled_checkpoint=old_save


if __name__=='__main__':main()
