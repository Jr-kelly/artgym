"""Wuji two-grasp curriculum teacher with the pretrained knife observation convention.

Only the encoded body frames and quaternion hemisphere change. Actual geometry,
world poses, actions, contact dynamics and reward equations stay inherited.
This task is teacher adaptation; no student deployment compatibility is claimed.
"""
import hashlib
from pathlib import Path

import numpy as np

from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
from scripts.wuji_knife_frame import original_to_acquisition_observations
from scripts.wuji_quaternion_hemisphere import align_quaternion_hemisphere


class WujiBridgeHemisphere(WujiVariableTimedAcquisition):
    def __init__(self, cfg, *args, **kwargs):
        root = Path(__file__).resolve().parents[2]
        source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
        if hashlib.sha256(source.read_bytes()).hexdigest() != '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5':
            raise ValueError('Source training quaternion identity changed')
        self.hemisphere_reference = np.load(source)[0, 43:47].copy()
        asset_root = cfg['object']['asset']['asset_root']
        if asset_root != 'assets/objects/knife_wuji_bridge2_20260922':
            raise ValueError('This task requires the frozen bridge2 original-axis asset')
        if hashlib.sha256((root / asset_root / '000/mobility.urdf').read_bytes()).hexdigest() != '5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c':
            raise ValueError('Original-axis knife identity changed')
        super().__init__(cfg, *args, **kwargs)

    def _compute_sapg_priv_observations(self):
        policy, privileged = super()._compute_sapg_priv_observations()
        policy, privileged = original_to_acquisition_observations(policy, privileged)
        return align_quaternion_hemisphere(policy, privileged, self.hemisphere_reference)
