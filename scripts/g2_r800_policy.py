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
        self.support_command_period=1;self.held_support_logits=None;self.support_takeover_frame=0
        self.residual=None;self.last_public_features=None;self.thumb_reference=None;self.history_features=False;self.support_estimator=None;self.action_parameterization='incremental';self.pressure_adapter=None;self.proprioceptive_pressure_spec=None
        if residual_checkpoint is not None:
            from scripts.wuji_robust_learning import ResidualActorCritic
            saved=torch.load(residual_checkpoint,map_location='cpu')
            self.support_command_period=saved.get('support_command_period',1)
            assert self.support_command_period in [1,5]
            self.proprioceptive_pressure_spec=saved.get('proprioceptive_pressure_spec')
            assert saved['format']=='wuji-r800-residual-ppo-v1'
            assert saved['student_sha256']==hashlib.sha256(Path(student).read_bytes()).hexdigest()
            assert saved['teacher_sha256']==hashlib.sha256(Path(teacher).read_bytes()).hexdigest()
            self.history_features=saved.get('history_features',False)
            if saved.get('support_estimator_spec'):
                from scripts.g2_legal_support_estimator import LegalSupportEstimator
                self.support_estimator=LegalSupportEstimator(saved['support_estimator_spec'],self.player.device)
            dim=(170 if self.history_features else 154)+(8 if self.support_estimator is not None else 0)
            self.residual=ResidualActorCritic(dim,dim+27).to(self.player.device)
            if saved.get('frozen_thumb_actor',False):self.residual.freeze_thumb_actor()
            self.residual.load_state_dict(saved['model']);self.residual.eval()
            self.residual_scale=torch.tensor(saved['action_scale'],device=self.player.device)
            self.action_parameterization=saved.get('action_parameterization','incremental')
            assert self.action_parameterization in ['incremental','bounded-motor-offset']
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
                self.last_public_features=public.detach().cpu().numpy()[0]
                base=action if self.action_base_mode=="r800" else torch.zeros_like(action)
                if self.thumb_reference is not None:base=self.thumb_reference.action(self.known.initial,self.known.issued,self.tensor([goal]),measured_q=self.tensor(q),clock_s=clock_s)
                mean=self.residual.actor_logits(public)
                if self.support_command_period>1:
                    assert clock_s is not None and self.action_parameterization=='bounded-motor-offset'
                    if self.held_support_logits is None or (round(clock_s*30)-self.support_takeover_frame)%self.support_command_period==0:
                        self.held_support_logits=mean[:,:16].clone()
                    mean=mean.clone();mean[:,:16]=self.held_support_logits
                if self.action_parameterization=='bounded-motor-offset':
                    assert self.thumb_reference is not None
                    from scripts.wuji_bounded_motor_residual import bounded_motor_residual_action
                    action=bounded_motor_residual_action(self.thumb_reference.last_target,self.known,mean,self.residual_scale)
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
        action=(desired-self.known.initial)/.04
        action[:,16:]=(desired[:,16:]-self.known.issued[:,16:])/.025
        action=action.clamp(-1,1)
        with torch.no_grad():issued=self.known.step(action)
        self.last_action=action[0].cpu().numpy()
        self.last_raw_action=np.zeros(20,dtype=np.float32)
        return issued[0].cpu().numpy(),self.last_action.copy()
