"""One policy over immutable geometry slots and source-stratified fresh pools."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from .wuji_geometry import WujiGeometry
from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
from scripts.wuji_width_contract import ROUND, sha, slots, real_size_slots


class WujiWidthStudent(WujiGeometry):
    def __init__(self, cfg, *args, **kwargs):
        root = Path(__file__).resolve().parents[2]
        self.width_slots = (real_size_slots if cfg['env'].get('realSizeAdaptation',False) else slots)(cfg['env']['widthArm'])
        assert int(cfg['env']['numEnvs']) == 256
        manifest_path = root / cfg['env']['widthTrainingManifest']
        self.width_manifest = json.loads(manifest_path.read_text())
        assert self.width_manifest['round'] == ('real-size-student-adaptation-20261002' if cfg['env'].get('realSizeAdaptation',False) else ROUND)
        assert self.width_manifest['statically_validated'] is True
        assert self.width_manifest['arm'] == cfg['env']['widthArm']
        assert self.width_manifest['slots'] == self.width_slots
        self.width_manifest_sha256 = sha(manifest_path)
        reference = root / 'caches/initial_grasp/wuji/knife_wuji_demo_aligned/000/train/valid_grasps.npy'
        assert sha(reference) == '056fd45a2c7cb454a9c8c3f4a9811e384e49d4b07e6b240edc8268d975c487c5'
        self.hemisphere_reference = np.load(reference)[0, 43:47].copy()
        assets = self.width_manifest['asset_files']
        for path, digest in assets.items():
            assert sha(root / path) == digest, path
        # Bypass only single-asset identity/pool checks. Reuse the original
        # bridge frame, acquisition/reset/controller and measured inertia path.
        WujiVariableTimedAcquisition.__init__(self, cfg, *args, **kwargs)
        assert self.instance_id_list == ['000', '001', '002']
        assert bool(self.instance_grasp_state_pose_is_local.all())
        expected = torch.tensor([s['instance'] for s in self.width_slots], device=self.device)
        assert torch.equal(self.env2instance, expected)
        self.width_source = torch.tensor([s['source'] for s in self.width_slots], device=self.device)
        self.width_group = torch.tensor([s['group'] for s in self.width_slots], device=self.device)
        self.width_reset_counts = torch.zeros((3, 4), dtype=torch.long, device=self.device)
        self.width_transition_counts = torch.zeros((3, 4), dtype=torch.long, device=self.device)
        self.width_pools = {}
        for entry in self.width_manifest['pools']:
            path = root / entry['states']
            assert sha(path) == entry['sha256']
            states = np.load(path, allow_pickle=False)
            assert states.ndim == 2 and states.shape[1] == 75 and np.isfinite(states).all()
            assert len(states) == entry['n'] and len(states) > 0
            self.width_pools[(entry['group'], entry['source'])] = torch.as_tensor(states, device=self.device)
        for s in self.width_slots:
            assert (s['group'], s['source']) in self.width_pools

    def _select_instance_index(self, env_id):
        return self.width_slots[env_id]['instance']

    def sample_grasps(self, env_ids):
        if not hasattr(self, 'width_pools') or self.eval_mode:
            return super().sample_grasps(env_ids)
        result = torch.empty((len(env_ids), 75), device=self.device)
        for (group, source), pool in self.width_pools.items():
            mask = (self.width_group[env_ids] == group) & (self.width_source[env_ids] == source)
            count = int(mask.sum())
            if count:
                rows = torch.randint(len(pool), (count,), device=self.device)
                result[mask] = pool[rows]
                self.width_reset_counts[group, source] += count
        return result

    def record_width_transitions(self):
        # Every slot executes one transition, including a transition ending in
        # reset. Counts by fixed logical group/source preserve the matched budget.
        ids = self.width_group * 4 + self.width_source
        self.width_transition_counts += torch.bincount(ids, minlength=12).reshape(3, 4)

    def width_receipt(self):
        return dict(manifest_sha256=self.width_manifest_sha256, slots=self.width_slots,
                    reset_counts=self.width_reset_counts.tolist(),
                    transition_counts=self.width_transition_counts.tolist(),
                    metadata_in_policy=False, sampler_state='fixed slot strata; sampling uses saved torch RNG')
