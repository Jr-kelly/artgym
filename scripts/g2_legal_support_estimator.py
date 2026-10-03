"""Frozen bounded support estimates from the audited measured/known features.

The artifact embeds the supervised head; no runtime truth, material or asset ID.
"""
import hashlib
from pathlib import Path
import torch
from scripts.train_g2_support_estimator import SupportEstimator


def specification(path):
    saved=torch.load(path,map_location='cpu')
    assert saved['format']=='g2-legal-support-estimator-v1'
    return {**{k:saved[k] for k in ['format','model','input_mean','input_std','input_dim','label_scales','data_sha256']},'source_checkpoint_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'source_checkpoint':str(path),'runtime_scope':'Original134 measured/known channels; optionalfrozenSC16 fromsamelegal2076 packet. Estimated8 outputs, no truth/asset/material inputs.'}


class LegalSupportEstimator:
    def __init__(self,spec,device):
        self.spec=spec;self.dimension=spec['input_dim'];assert self.dimension in [134,150]
        # Creating a frozen auxiliary head must not change physics/learner RNG.
        with torch.random.fork_rng(devices=[]):self.model=SupportEstimator(self.dimension).to(device)
        self.model.load_state_dict(spec['model']);self.model.eval();self.model.requires_grad_(False)
        self.mean=spec['input_mean'].to(device);self.std=spec['input_std'].to(device)

    @torch.no_grad()
    def __call__(self,public,encoder,packet):
        legal=torch.cat([public[:,:131],public[:,151:154]],-1)
        if self.dimension==150:
            from scripts.wuji_student_interface import legal_history_latent
            legal=torch.cat([legal,legal_history_latent(encoder,packet)],-1)
        previous=torch.backends.cuda.matmul.allow_tf32
        try:
            torch.backends.cuda.matmul.allow_tf32=False
            result=self.model(((legal-self.mean)/self.std).clamp(-20,20))
        finally:torch.backends.cuda.matmul.allow_tf32=previous
        return torch.cat([result[:,:1].clamp(-.25,1.5),result[:,1:7].clamp(-4,4),result[:,7:8]],-1).detach()
