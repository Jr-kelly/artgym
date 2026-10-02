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
    def __init__(self, cfg, teacher, student, geometry=None,thumb_action_gain=1.,support_action_gain=1.,residual_checkpoint=None):
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
        self.residual=None;self.last_public_features=None
        if residual_checkpoint is not None:
            from scripts.wuji_robust_learning import ResidualActorCritic
            saved=torch.load(residual_checkpoint,map_location='cpu')
            assert saved['format']=='wuji-r800-residual-ppo-v1'
            assert saved['student_sha256']==hashlib.sha256(Path(student).read_bytes()).hexdigest()
            assert saved['teacher_sha256']==hashlib.sha256(Path(teacher).read_bytes()).hexdigest()
            self.residual=ResidualActorCritic().to(self.player.device);self.residual.load_state_dict(saved['model']);self.residual.eval()
            self.residual_scale=torch.tensor(saved['action_scale'],device=self.player.device)

    def takeover_estimate(self, q, target, object_local_estimate, slider_local_estimate):
        assert len(self.history) == 50, 'Collect 50 measured control frames before handover'
        self.init = np.r_[self.normalized(q), pose(object_local_estimate),
                          pose(slider_local_estimate), self.tips(q), self.geometry].astype(np.float32)
        self.last_action = np.zeros(20, dtype=np.float32)
        self.known.reset(torch.tensor([0], device=self.player.device), self.tensor(target))
        reset_player_rnn_state(self.player)

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

    def command(self, q, goal,wrist_gravity=None):
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
                self.last_public_features=public.detach().cpu().numpy()[0]
                action=(action+self.residual_scale*torch.tanh(self.residual.actor(public))).clamp(-1,1)
            action=action.clone();action[:,:16]*=self.support_action_gain;action[:,16:]*=self.thumb_action_gain
            target = self.known.step(action)
        self.last_action = action[0].cpu().numpy()
        self.last_raw_action = raw_action[0].cpu().numpy()
        return target[0].cpu().numpy(), self.last_action.copy()
