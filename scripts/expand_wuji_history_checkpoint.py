"""Expose the existing frozen legal SC history latent without changing initial behavior.

Zero columns extend actor/critic and corresponding Adam buffers; critic truth
columns move after the sixteen new public columns. No training or new sensor.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import torch


def expand(value,critic=False):
    out=value.new_zeros((value.shape[0],value.shape[1]+16))
    out[:,:154]=value[:,:154]
    if critic:out[:,170:]=value[:,154:]
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();saved=torch.load(a.checkpoint,map_location='cpu');out=copy.deepcopy(saved)
    assert not saved.get('history_features',False)
    assert saved['model']['actor.0.weight'].shape[1]==154 and saved['model']['critic.0.weight'].shape[1]==181
    keys=list(saved['model']);ids=saved['optimizer']['param_groups'][0]['params'];assert len(keys)==len(ids)
    for key,critic in [('actor.0.weight',False),('critic.0.weight',True)]:
        out['model'][key]=expand(saved['model'][key],critic)
        state=out['optimizer']['state'].get(ids[keys.index(key)],{})
        for name in ['exp_avg','exp_avg_sq','max_exp_avg_sq']:
            if name in state:state[name]=expand(state[name],critic)
    # First-layer calculations must preserve the old contribution for arbitrary
    # legal history values; the rest of each network and all RNG buffers are exact.
    generator=torch.Generator().manual_seed(2026100362)
    x=torch.randn((64,154),generator=generator);truth=torch.randn((64,27),generator=generator);latent=torch.randn((64,16),generator=generator)
    errors={}
    for key,old,new in [('actor.0.weight',x,torch.cat([x,latent],-1)),('critic.0.weight',torch.cat([x,truth],-1),torch.cat([x,latent,truth],-1))]:
        errors[key]=float((old@saved['model'][key].T-new@out['model'][key].T).abs().max());assert errors[key]<2e-6
    unchanged=[k for k in keys if k not in errors];assert all(torch.equal(saved['model'][k],out['model'][k]) for k in unchanged)
    for name in ['rng_cpu','rng_cuda']:
        if name=='rng_cuda':assert all(torch.equal(x,y) for x,y in zip(saved[name],out[name]))
        else:assert torch.equal(saved[name],out[name])
    out.update(history_features=True,public_dim=170,actor_inputs='Original154 measured/known features+frozen16D SC latent from the same legal2076 packet; no live truth',critic_inputs='170 public+21 truth+5 contact+1 load')
    metadata=dict(parent=str(a.checkpoint),parent_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),new_optimizer_updates=0,new_transitions=0,first_layer_max_errors=errors,unchanged_model_parameter_count=len(unchanged),history_feature_scope='Same frozen encoder and measured50x40 history, fixed initial estimate55, issued targets20, known goal1; no current object/slider/contact/loadID',optimizer='Existing Adam moments preserved and extended by zero columns',rng='All original states preserved; no random initialization consumed')
    out['history_feature_adaptation']=metadata;a.output.parent.mkdir(parents=True,exist_ok=True);torch.save(out,a.output)
    metadata['sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest();a.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2));a.output.with_suffix('.sha256').write_text(metadata['sha256']+'\n');print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
