"""Fixed-knife Wuji port: upstream incremental control, arrival goals and SAPG.

The Wuji hand/contact/knife physical profile is retained. This is not a
category-level reproduction or a one-factor comparison with mixed control.
"""
from pathlib import Path
import hashlib
import numpy as np
import torch
from .artmanip import ArtManip
from .wuji_demo_aligned import WujiDemoAligned

class WujiArtManipReference(WujiDemoAligned):
    def __init__(self, cfg, *args, **kwargs):
        self.reference_ready = False
        super().__init__(cfg, *args, **kwargs)
        path = Path(cfg['env']['trainingStates'])
        if not path.is_absolute(): path = Path(__file__).resolve().parents[2] / path
        states = np.load(path, allow_pickle=False)
        assert states.ndim == 2 and states.shape[1] == 75 and len(states) % 4 == 0
        assert np.isfinite(states).all() and len(self.instance_id_list) == 1
        self.all_valid_states = torch.as_tensor(states, device=self.device)
        self.instance2grasplen[:] = len(states)
        self.instance_offsets[:] = 0
        self.training_states_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        self.source_ids = torch.zeros(self.num_envs, device=self.device, dtype=torch.long)
        self.source_visits = torch.zeros(4, device=self.device, dtype=torch.long)
        self.reference_ready = True

    def sample_grasps(self, env_ids):
        if not self.reference_ready or self.eval_mode:
            return super().sample_grasps(env_ids)
        # Source sampled independently for every reset; no source enters policy.
        sources = torch.randint(4, (len(env_ids),), device=self.device)
        forced = int(self.cfg['env'].get('singleSource', -1))
        if forced >= 0: sources[:] = forced
        width = len(self.all_valid_states) // 4
        rows = sources * width + torch.randint(width, (len(env_ids),), device=self.device)
        self.source_ids[env_ids] = sources
        self.source_visits += torch.bincount(sources, minlength=4)
        return self.all_valid_states[rows].clone()

    def pre_physics_step(self, actions):
        # Bypass WujiDemoAligned's absolute-target conversion.
        ArtManip.pre_physics_step(self, actions)

    def actions_to_targets(self, actions):
        raw = self.prev_targets[:, :20] + self.hand_dof_speed_scale * self.dt * actions
        return torch.maximum(torch.minimum(raw, self.hand_dof_upper_limits), self.hand_dof_lower_limits)

    def compute_reward(self, actions):
        ArtManip.compute_reward(self, actions)
        if self.reference_ready and not self.eval_mode:
            error = (self.obj_dof_pos - self.goal_obj_dof_pos).abs().squeeze(-1)
            for source in range(4):
                mask = self.source_ids == source
                self.extras[f'source{source}/visits'] = self.source_visits[source].float()
                if mask.any():
                    self.extras[f'source{source}/goal_error'] = error[mask].mean()
                    self.extras[f'source{source}/arrival'] = (error[mask] < self.object_cfg['task']['success_threshold']).float().mean()
                    self.extras[f'source{source}/counted'] = self.goal_achieved_step[mask].mean()
                    self.extras[f'source{source}/drop'] = self.truncated_envs[mask].float().mean()
