"""Zero-column policy adaptation for a frozen measured-input estimator."""
import argparse,copy,hashlib,json
from pathlib import Path
import torch
from scripts.g2_legal_support_estimator import specification


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--estimator',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();saved=torch.load(a.checkpoint,map_location='cpu');assert not saved.get('support_estimator_spec');dim=170 if saved.get('history_features') else 154;out=copy.deepcopy(saved);keys=list(saved['model']);ids=saved['optimizer']['param_groups'][0]['params'];assert len(keys)==len(ids)
    def expand(value,critic):
        result=value.new_zeros((value.shape[0],value.shape[1]+8));result[:,:dim]=value[:,:dim]
        if critic:result[:,dim+8:]=value[:,dim:]
        return result
    for key,critic in [('actor.0.weight',False),('critic.0.weight',True)]:
        out['model'][key]=expand(saved['model'][key],critic);state=out['optimizer']['state'].get(ids[keys.index(key)],{})
        for name in ['exp_avg','exp_avg_sq','max_exp_avg_sq']:
            if name in state:state[name]=expand(state[name],critic)
    generator=torch.Generator().manual_seed(2026100374);public=torch.randn((64,dim),generator=generator);truth=torch.randn((64,27),generator=generator);estimate=torch.randn((64,8),generator=generator);errors={}
    for key,old,new in [('actor.0.weight',public,torch.cat([public,estimate],-1)),('critic.0.weight',torch.cat([public,truth],-1),torch.cat([public,estimate,truth],-1))]:
        errors[key]=float(abs(old@saved['model'][key].T-new@out['model'][key].T).max());assert errors[key]<2e-6
    assert all(torch.equal(saved['model'][k],out['model'][k]) for k in keys if k not in errors)
    assert torch.equal(saved['rng_cpu'],out['rng_cpu']) and all(torch.equal(x,y) for x,y in zip(saved['rng_cuda'],out['rng_cuda']))
    spec=specification(a.estimator);out.update(support_estimator_spec=spec,public_dim=dim+8,actor_inputs=saved['actor_inputs']+';8 frozen bounded estimates from legal measured/known inputs; no live truth')
    metadata=dict(parent=str(a.checkpoint),parent_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),estimator=str(a.estimator),estimator_sha256=spec['source_checkpoint_sha256'],first_layer_max_errors=errors,new_policy_updates=0,new_policy_transitions=0,optimizer='Original Adam moments retained; new actor/critic observation columns zero',rng='Original CPU/CUDA/Numpy states retained',scope='Input adaptation only; auxiliary head trained separately and embedded frozen. No behavioral gain or new sensor claim')
    out['support_feature_adaptation']=metadata;a.output.parent.mkdir(parents=True,exist_ok=True);torch.save(out,a.output);metadata['sha256']=hashlib.sha256(a.output.read_bytes()).hexdigest();a.output.with_suffix('.json').write_text(json.dumps(metadata,indent=2));a.output.with_suffix('.sha256').write_text(metadata['sha256']+'\n');print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
