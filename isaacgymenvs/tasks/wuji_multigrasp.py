"""Controlled grasp-pool extension of the frozen original-axis bridge3 task."""
from pathlib import Path
import hashlib
import numpy as np
import torch
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere

class WujiMultigrasp(WujiBridge3Hemisphere):
    def __init__(self, cfg, *args, **kwargs):
        super().__init__(cfg, *args, **kwargs)
        path = Path(cfg['env']['trainingStates'])
        if not path.is_absolute(): path = Path(__file__).resolve().parents[2] / path
        states = np.load(path, allow_pickle=False)
        assert states.ndim == 2 and states.shape[1] == 75 and np.isfinite(states).all()
        assert len(self.instance_id_list) == 1
        self.all_valid_states = torch.as_tensor(states, device=self.device)
        self.instance2grasplen[:] = len(states)
        self.instance_offsets[:] = 0
        self.training_states_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
