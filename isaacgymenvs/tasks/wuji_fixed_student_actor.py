"""Wuji physics with a frozen student latent and an optional broad goal reward."""
import hashlib
from pathlib import Path
import numpy as np
import torch
from gym import spaces
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere


class WujiFixedStudentActor(WujiBridge3Hemisphere):
    def __init__(self, cfg, *args, **kwargs):
        self.fixed_student_ready = False
        cfg['env']['enableStudentEncoderObs'] = True
        super().__init__(cfg, *args, **kwargs)
        assert self.num_obs == 137 and self.student_obs_dim == 2055
        source = Path(cfg['env']['fixedStudentArtifact'])
        if not source.is_absolute():
            source = Path(__file__).resolve().parents[2] / source
        self.fixed_student_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        assert self.fixed_student_sha256 == cfg['env']['fixedStudentSha256']
        artifact = torch.load(source, map_location='cpu')
        meta = artifact['distill_meta']
        assert meta['task'] == 'wuji_acquisition_bridge3_hemisphere'
        assert meta['hand'] == 'wuji_paper_official_actuator'
        assert meta['teacher_checkpoint_sha256'] == cfg['env']['fixedTeacherSha256']
        from isaacgymenvs.distill import build_student_encoder_from_spec
        device = torch.device(self.device)
        devices = [device.index or 0] if device.type == 'cuda' else []
        with torch.random.fork_rng(devices=devices):
            encoder = build_student_encoder_from_spec(2055, 16, {}, 'elu', meta['student_encoder_spec'])
            encoder.load_state_dict(artifact['student_encoder_state_dict'])
        self.fixed_student_encoder = encoder.to(self.device).eval()
        for parameter in self.fixed_student_encoder.parameters():
            parameter.requires_grad_(False)
        self.legacy_obs_buf = self.obs_buf
        self.legacy_clip_obs = self.clip_obs
        self.clip_obs = float('inf')  # Legacy prefix is explicitly clipped below.
        self.num_observations = 153
        self.cfg['env']['numObservations'] = 153
        self.obs_space = spaces.Box(np.full(153, -np.inf), np.full(153, np.inf))
        self.obs_buf = torch.zeros((self.num_envs, 153), device=self.device)
        self.fixed_student_ready = True

    def compute_reward(self, actions):
        config = self.cfg['env'].get('broadGoalReward', {})
        coefficient = float(config.get('coefficient', 0.0))
        bonus = None
        if coefficient:
            width = float(config['width_m'])
            if coefficient < 0 or width <= 0:
                raise ValueError('Broad goal reward requires positive coefficient and width')
            # Capture the command that generated this transition, before the
            # inherited duration clock can switch it to the next command.
            error = torch.norm(self.obj_dof_pos - self.goal_obj_dof_pos, p=1, dim=-1)
            valid = ~self.truncated_envs & torch.isfinite(error)
            if self.eval_mode:
                valid &= self.eval_active_mask
            bonus = coefficient * torch.exp(-(error / width).square())
            bonus = torch.where(valid, bonus, torch.zeros_like(bonus))
        super().compute_reward(actions)
        if bonus is not None:
            self.rew_buf += bonus
            self.extras['BroadGoalReward'] = bonus.mean()

    def compute_observations(self):
        if not self.fixed_student_ready:
            return super().compute_observations()
        packed = self.obs_buf
        self.obs_buf = self.legacy_obs_buf
        try:
            super().compute_observations()
        finally:
            self.obs_buf = packed
        assert not self.fixed_student_encoder.training
        with torch.no_grad():
            latent = self.fixed_student_encoder(self.get_student_encoder_observations())
        assert latent.shape == (self.num_envs, 16) and latent.isfinite().all()
        packed[:, :137] = self.legacy_obs_buf.clamp(-self.legacy_clip_obs, self.legacy_clip_obs)
        packed[:, 137:] = latent


def register_task():
    from isaacgymenvs.tasks import isaacgym_task_map
    isaacgym_task_map['wuji_fixed_student_actor'] = WujiFixedStudentActor
