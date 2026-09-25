"""Three training grasps with the unchanged bridge2 observation convention."""
import hashlib
from pathlib import Path
import numpy as np
from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
from .wuji_bridge_hemisphere import WujiBridgeHemisphere


class WujiBridge3Hemisphere(WujiBridgeHemisphere):
    def __init__(self, cfg, *args, **kwargs):
        root = Path(__file__).resolve().parents[2]
        source = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
        assert hashlib.sha256(source.read_bytes()).hexdigest() == '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
        self.hemisphere_reference = np.load(source)[0, 43:47].copy()
        asset_root = cfg['object']['asset']['asset_root']
        assert asset_root == 'assets/objects/knife_wuji_bridge3_20260922'
        assert hashlib.sha256((root / asset_root / '000/mobility.urdf').read_bytes()).hexdigest() == '5229c66b183cc6da04190bf2d6cfbd035fadd227340dc8f26602b207171b461c'
        # Bypass only the bridge2 asset identity check. Observation transform,
        # rewards, physical dynamics and action mapping remain inherited.
        WujiVariableTimedAcquisition.__init__(self, cfg, *args, **kwargs)
