"""Frozen bounded estimates from audited measured/known inputs and history.

Artifacts embed their supervised head; truth, material and asset ID stay out.
"""
import hashlib
from pathlib import Path
import torch
from scripts.train_g2_support_estimator import SupportEstimator


def specification(path):
    saved=torch.load(path,map_location='cpu')
    assert saved['format'] in ['g2-legal-support-estimator-v1','g2-legal-temporal-support-estimator-v1']
    keys=['format','model','input_mean','input_std','input_dim','label_scales','data_sha256']
    if saved['format']=='g2-legal-temporal-support-estimator-v1':keys+=['history_mean','history_std']
    return {**{k:saved[k] for k in keys},'source_checkpoint_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'source_checkpoint':str(path),'runtime_scope':'Original134 measured/knownchannels; optionalfrozenSC16 orsamelegal50x40history. Estimated8 outputs, no truth/asset/material inputs.'}


class LegalSupportEstimator:
    def __init__(self,spec,device):
        self.spec=spec;self.dimension=spec['input_dim'];assert self.dimension in [134,150]
        self.temporal=spec['format']=='g2-legal-temporal-support-estimator-v1'
        with torch.random.fork_rng(devices=[]):
            if self.temporal:
                from scripts.train_g2_temporal_support_estimator import TemporalSupportEstimator
                assert self.dimension==134;self.model=TemporalSupportEstimator().to(device)
            else:self.model=SupportEstimator(self.dimension).to(device)
        self.model.load_state_dict(spec['model']);self.model.eval();self.model.requires_grad_(False)
        self.mean=spec['input_mean'].to(device);self.std=spec['input_std'].to(device)
        if self.temporal:self.history_mean=spec['history_mean'].to(device);self.history_std=spec['history_std'].to(device)

    @torch.no_grad()
    def __call__(self,public,encoder,packet):
        legal=torch.cat([public[:,:131],public[:,151:154]],-1)
        if self.dimension==150:
            from scripts.wuji_student_interface import legal_history_latent
            legal=torch.cat([legal,legal_history_latent(encoder,packet)],-1)
        previous=torch.backends.cuda.matmul.allow_tf32;previous_conv=torch.backends.cudnn.allow_tf32
        try:
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            normalized=((legal-self.mean)/self.std).clamp(-20,20)
            if self.temporal:
                history=packet[:,:2000].reshape(-1,50,40)
                history=((history-self.history_mean)/self.history_std).clamp(-20,20)
                result=self.model(normalized,history)
            else:result=self.model(normalized)
        finally:
            torch.backends.cuda.matmul.allow_tf32=previous;torch.backends.cudnn.allow_tf32=previous_conv
        return torch.cat([result[:,:1].clamp(-.25,1.5),result[:,1:7].clamp(-4,4),result[:,7:8]],-1).detach()
