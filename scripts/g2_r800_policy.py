"""R800 bridge using measured hand joints and issued commands in G2 wrist frame.

No live object pose, contact, resistance identifier or slider state is accepted.
Initial poses are calibration estimates supplied once; history is measured.
"""
import hashlib
from pathlib import Path
import numpy as np
import torch
from scripts.g2_frozen_policy import FrozenPolicy, pose
from scripts.wuji_student_interface import build_encoder, install_student_player
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere
from isaacgymenvs.deploy.student_policy_runtime import reset_player_rnn_state

class G2R800Policy(FrozenPolicy):
    def __init__(self, cfg, teacher, student, geometry=None,thumb_action_gain=1.,support_action_gain=1.,residual_checkpoint=None,thumb_reference_override=None,support_residual_scale_override=None):
        super().__init__(cfg, teacher, None, geometry=geometry or [.016,.012,.135,.01,.003,.03])
        artifact = torch.load(student, map_location='cpu')
        assert artifact['format'] == 'wuji-unified-student-v1'
        assert artifact['kind'] == 'SC' and artifact['controller_mode'] == 'real'
        assert artifact['teacher_sha256'] == hashlib.sha256(Path(teacher).read_bytes()).hexdigest()
        encoder = build_encoder('SC').to(self.player.device)
        encoder.load_state_dict(artifact['student_encoder']); encoder.eval()
        self.player.model.a2c_network.priv_encoder = encoder
        self.player.model.eval(); install_student_player(self.player); self.student = True
        lower = torch.tensor(self.fk.lower, dtype=torch.float32, device=self.player.device)
        upper = torch.tensor(self.fk.upper, dtype=torch.float32, device=self.player.device)
        self.known = KnownWujiController(lower, upper, 1)
        self.last_encoder_input = None; self.last_observation = None
        assert 0<=thumb_action_gain<=1 and 0<=support_action_gain<=1
        self.thumb_action_gain=thumb_action_gain;self.support_action_gain=support_action_gain
        self.support_load_features=None;self.support_load_feature_spec=None;self.support_delta_coordinates=None
        self.support_latch_after_preparation=False;self.support_command_period=1;self.held_support_logits=None;self.support_takeover_frame=0
        self.residual=None;self.last_public_features=None;self.thumb_reference=None;self.history_features=False;self.support_estimator=None;self.action_parameterization='incremental';self.pressure_adapter=None;self.proprioceptive_pressure_spec=None
        if residual_checkpoint is not None:
            from scripts.wuji_robust_learning import ResidualActorCritic
            saved=torch.load(residual_checkpoint,map_location='cpu')
            self.support_command_period=saved.get('support_command_period',1)
            self.support_latch_after_preparation=saved.get('support_latch_after_preparation',False)
            assert self.support_command_period in [1,5]
            if saved.get('support_delta_spec') is not None:
                from scripts.wuji_support_delta_coordinates import SupportDeltaCoordinates
                self.support_delta_coordinates=SupportDeltaCoordinates(saved['support_delta_spec'],1,self.player.device)
            self.proprioceptive_pressure_spec=saved.get('proprioceptive_pressure_spec')
            assert saved['format']=='wuji-r800-residual-ppo-v1'
            assert saved['student_sha256']==hashlib.sha256(Path(student).read_bytes()).hexdigest()
            assert saved['teacher_sha256']==hashlib.sha256(Path(teacher).read_bytes()).hexdigest()
            self.support_load_feature_spec=saved.get('support_load_feature_spec')
            if self.support_load_feature_spec:
                from scripts.wuji_support_load_features import SupportLoadFeatures
                self.support_load_features=SupportLoadFeatures(1,self.player.device,np.asarray(cfg.hand.dof_props.stiffness),np.asarray(cfg.hand.dof_props.damping))
            self.history_features=saved.get('history_features',False)
            if saved.get('support_estimator_spec'):
                from scripts.g2_legal_support_estimator import LegalSupportEstimator
                self.support_estimator=LegalSupportEstimator(saved['support_estimator_spec'],self.player.device)
            dim=(170 if self.history_features else 154)+(8 if self.support_estimator is not None else 0)
            dim+=9 if self.support_load_features is not None else 0
            assert saved.get('public_dim',dim)==dim
            self.residual=ResidualActorCritic(dim,dim+27).to(self.player.device)
            if saved.get('frozen_thumb_actor',False):self.residual.freeze_thumb_actor()
            self.residual.load_state_dict(saved['model']);self.residual.eval()
            self.residual_scale=torch.tensor(saved['action_scale'],device=self.player.device)
            self.action_parameterization=saved.get('action_parameterization','incremental')
            assert self.action_parameterization in ['incremental','bounded-motor-offset']
            controller=saved.get('known_controller_spec',{})
            self.known.configure_support(controller.get('support_span_rad',.04),controller.get('support_step_rad'))
            if self.known.support_span>.04:
                assert self.action_parameterization=='bounded-motor-offset' and saved.get('action_base_mode')=='geometric'
                assert self.pressure_adapter is None and self.proprioceptive_pressure_spec is None
                assert self.support_delta_coordinates is None or self.support_delta_coordinates.spec.get('controller_span_rad',.04)==self.known.support_span
                cfg.task.env.supportActionSpan=self.known.support_span
            if support_residual_scale_override is not None:
                assert self.action_parameterization=='bounded-motor-offset'
                assert 0<support_residual_scale_override<=float(cfg.task.env.supportActionSpan)
                self.residual_scale[:16]=float(support_residual_scale_override)
            self.action_base_mode=saved.get('action_base_mode','r800')
            if self.action_base_mode=='geometric':
                from scripts.wuji_scheduled_thumb_reference import ScheduledThumbReference
                reference_spec=saved['thumb_reference']
                if thumb_reference_override is not None:
                    import json
                    reference_spec=json.loads(Path(thumb_reference_override).read_text())
                self.thumb_reference=ScheduledThumbReference(reference_spec,1,self.player.device)

    def takeover_estimate(self, q, target, object_local_estimate, slider_local_estimate,clock_s=0.):
        self.held_support_logits=None;self.support_takeover_frame=round(clock_s*30)
        assert len(self.history) == 50, 'Collect 50 measured control frames before handover'
        self.init = np.r_[self.normalized(q), pose(object_local_estimate),
                          pose(slider_local_estimate), self.tips(q), self.geometry].astype(np.float32)
        self.last_action = np.zeros(20, dtype=np.float32)
        self.known.reset(torch.tensor([0], device=self.player.device), self.tensor(target))
        if self.support_delta_coordinates is not None:self.support_delta_coordinates.reset(torch.tensor([0],device=self.player.device),self.tensor(target),self.tensor(pose(object_local_estimate)[3:7]))
        if self.pressure_adapter is not None:self.pressure_adapter.handover_anchor()
        if self.thumb_reference is not None and self.thumb_reference.measured_hold_reference:
            from scripts.wuji_measured_hold_reference import measured_hold_path
            mean=np.asarray(self.history)[:,:20].mean(0)
            measured=(mean+1)*.5*(self.fk.upper-self.fk.lower)+self.fk.lower
            path,self.measured_hold_reference_audit=measured_hold_path(measured,
                object_local_estimate[:3,1],object_local_estimate[:3,2],self.thumb_reference.shifts.cpu().numpy())
            self.thumb_reference.q=torch.as_tensor(path,dtype=torch.float32,device=self.player.device)
        reset_player_rnn_state(self.player)
        if self.thumb_reference is not None:self.thumb_reference.reset(torch.tensor([0],device=self.player.device),clock_s=clock_s)

    def tensor(self, value):
        return torch.as_tensor(value, dtype=torch.float32, device=self.player.device).reshape(1,-1)

    def inputs(self, q, goal):
        pol = self.tensor(np.r_[self.init, self.normalized(q), self.last_action, [goal], self.tips(q)])
        pri = torch.zeros((1,21), device=self.player.device)
        pol, pri = original_to_acquisition_observations(pol, pri)
        pol, pri = align_quaternion_hemisphere(pol, pri, self.reference)
        context = torch.cat([self.known.observed_targets(), pol[:,95:96]/.04], dim=1)
        encoder_input = torch.cat([self.tensor(np.asarray(self.history).ravel()), pol[:,:55], context], dim=1)
        assert encoder_input.shape == (1,2076)
        obs = torch.cat([pol, pri, torch.zeros((1,5), device=self.player.device),
                         self.player.intr_reward_coef_embd[:1]], dim=1)
        return obs, encoder_input

    def prewarm(self, q, goal, wrist_gravity, iterations=8, clock_s=16.):
        """Warm full inference on isolated control state after real history.

        Computed warmup targets are discarded; RNN, reference, known targets,
        action memory and real measured history are restored before takeover.
        Covers the adopted154-dimensional bridge, not unused observer heads.
        """
        from isaacgymenvs.deploy.student_policy_runtime import clone_states
        import copy,time
        assert self.init is not None and len(self.history)==50 and iterations>=1
        assert not self.history_features and self.support_estimator is None and self.support_load_features is None
        assert self.pressure_adapter is None and self.support_delta_coordinates is None
        states=clone_states(self.player.states);network=self.player.model.a2c_network
        old_override=getattr(network,'actor_encoder_obs_override',None)
        issued=self.known.issued.clone();initial=self.known.initial.clone()
        executed=self.known.last_executed_action.clone()
        history=np.asarray(self.history).copy();reference=copy.deepcopy(self.thumb_reference)
        fields=['last_action','last_raw_action','last_encoder_input','last_observation','last_public_features','held_support_logits']
        saved={name:copy.deepcopy(getattr(self,name)) for name in fields}
        def restore():
            self.player.states=clone_states(states)
            self.known.issued=issued.clone();self.known.initial=initial.clone()
            self.known.last_executed_action=executed.clone()
            self.thumb_reference=copy.deepcopy(reference)
            for name,value in saved.items():setattr(self,name,copy.deepcopy(value))
            network.actor_encoder_obs_override=old_override
        if torch.cuda.is_available():torch.cuda.synchronize()
        begin=time.perf_counter()
        try:
            with torch.no_grad():
                for _ in range(iterations):
                    restore();self.command(q,goal,wrist_gravity=wrist_gravity,clock_s=clock_s)
            if torch.cuda.is_available():torch.cuda.synchronize()
        finally:restore()
        assert torch.equal(issued,self.known.issued) and torch.equal(initial,self.known.initial)
        assert torch.equal(executed,self.known.last_executed_action)
        assert np.array_equal(history,np.asarray(self.history)) and np.array_equal(saved['last_action'],self.last_action)
        return dict(iterations=iterations,wall_ms=(time.perf_counter()-begin)*1000,
                    measured_history_frames=50,commands_issued=0,discarded_computed_targets=iterations,
                    rnn_state_restored=True,reference_and_command_state_restored=True,
                    scope='Full model/control warmup with isolated state; no synthetic measured history or issued motor command, not hardware latency verification')

    def command(self, q, goal,wrist_gravity=None,clock_s=None,diagnostic_motor_offset=None):
        obs, encoder_input = self.inputs(q, goal)
        self.last_encoder_input = encoder_input.detach().cpu().numpy()[0]
        self.last_observation = obs.detach().cpu().numpy()[0]
        self.player.model.a2c_network.actor_encoder_obs_override = encoder_input
        with torch.no_grad():
            action = self.player.get_action(obs, is_deterministic=True)
            raw_action=action.clone()
            if self.residual is not None:
                assert wrist_gravity is not None, 'Residual gravity comes from measured G2 arm FK'
                public=torch.cat([obs[:,:111],self.known.observed_targets(),action,self.tensor(wrist_gravity)],-1)
                if self.history_features:
                    from scripts.wuji_student_interface import legal_history_latent
                    latent=legal_history_latent(self.player.model.a2c_network.priv_encoder,encoder_input)
                    assert latent.shape==(1,16)
                    public=torch.cat([public,latent],-1)
                if self.support_estimator is not None:
                    public=torch.cat([public,self.support_estimator(public,self.player.model.a2c_network.priv_encoder,encoder_input)],-1)
                if self.support_load_features is not None:public=torch.cat([public,self.support_load_features.features()],-1)
                self.last_public_features=public.detach().cpu().numpy()[0]
                base=action if self.action_base_mode=="r800" else torch.zeros_like(action)
                if self.thumb_reference is not None:base=self.thumb_reference.action(self.known.initial,self.known.issued,self.tensor([goal]),measured_q=self.tensor(q),clock_s=clock_s)
                mean=self.residual.actor_logits(public)
                if self.support_command_period>1 or self.support_latch_after_preparation:
                    assert clock_s is not None and self.action_parameterization=='bounded-motor-offset'
                    if self.held_support_logits is None or ((round(clock_s*30)-self.support_takeover_frame)%self.support_command_period==0 and (not self.support_latch_after_preparation or round(clock_s*30)<=480)):
                        self.held_support_logits=mean[:,:16].clone()
                    mean=mean.clone();mean[:,:16]=self.held_support_logits
                if self.action_parameterization=='bounded-motor-offset':
                    assert self.thumb_reference is not None
                    from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action
                    action=self.support_delta_coordinates.action(self.thumb_reference.last_target,self.known,mean,self.residual_scale,public) if self.support_delta_coordinates is not None else bounded_motor_residual_action(self.thumb_reference.last_target,self.known,mean,self.residual_scale)
                else:action=(base+self.residual_scale*torch.tanh(mean)).clamp(-1,1)
            action=action.clone();action[:,:16]*=self.support_action_gain;action[:,16:]*=self.thumb_action_gain
            if self.pressure_adapter is not None:
                proposed=self.known.initial+.04*action;proposed[:,16:]=self.known.issued[:,16:]+.025*action[:,16:]
                desired=self.pressure_adapter.command(q,self.known.issued[0].cpu().numpy(),proposed[0].cpu().numpy(),clock_s)
                action=(self.tensor(desired)-self.known.initial)/.04;action[:,16:]=(self.tensor(desired)[:,16:]-self.known.issued[:,16:])/.025;action=action.clamp(-1,1)
            if diagnostic_motor_offset is not None:
                # Explicit single native truth diagnostic, never actor inputs.
                # Preserve original support span and one issued-memory update.
                offset=np.asarray(diagnostic_motor_offset,dtype=float)
                assert offset.shape==(20,) and np.isfinite(offset).all()
                assert np.max(np.abs(offset))<=.040001 and np.all(offset[12:]==0)
                action=action.clone();action[:,:16]+=self.tensor(offset)[:,:16]/.04
                action=action.clamp(-1,1)
            target = self.known.step(action)
            if self.known.support_step is not None:action=self.known.last_executed_action.clone()
            if self.pressure_adapter is not None and hasattr(self.pressure_adapter,'commit_issued'):
                self.pressure_adapter.commit_issued(target[0].cpu().numpy(),proposed[0].cpu().numpy())
        self.last_action = action[0].cpu().numpy()
        self.last_raw_action = raw_action[0].cpu().numpy()
        return target[0].cpu().numpy(), self.last_action.copy()

    def scripted_target(self, target):
        """Issue calibrated script targets through the same legal action memory.

        Offline geometry and scheduled command only; no force/slider feedback.
        """
        desired=self.tensor(target)
        action=(desired-self.known.initial)/self.known.support_span
        action[:,16:]=(desired[:,16:]-self.known.issued[:,16:])/.025
        action=action.clamp(-1,1)
        with torch.no_grad():issued=self.known.step(action)
        if self.known.support_step is not None:action=self.known.last_executed_action.clone()
        self.last_action=action[0].cpu().numpy()
        self.last_raw_action=np.zeros(20,dtype=np.float32)
        return issued[0].cpu().numpy(),self.last_action.copy()
