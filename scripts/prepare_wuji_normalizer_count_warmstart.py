"""Reset only the normalization pseudo-count for multi-grasp fine tuning.

Retain all learned weights, observation means and variances. Frozen inference
must be exactly unchanged. During training, new observations will update the
normalizer with count one rather than 39 million. This is an explicit training
intervention, not a claim that normalization alone solves different grasps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from rl_games.algos_torch.running_mean_std import RunningMeanStd


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'teacher.pth').exists()
    import numpy as np
    original=torch.load(args.source,map_location='cpu')
    source=(original[0] if 0 in original else original)['model']
    model={k:v.clone() for k,v in source.items()}
    name='running_mean_std.count';old=float(model[name]);assert old==39321601.
    model[name].fill_(1.)
    differences={k:int(torch.count_nonzero(model[k]!=source[k])) for k in model}
    assert {k:v for k,v in differences.items() if v}=={name:1}
    modules=[]
    for state in [source,model]:
        module=RunningMeanStd(137)
        module.load_state_dict({k[len('running_mean_std.'):]:v
                               for k,v in state.items() if k.startswith('running_mean_std.')})
        module.eval();modules.append(module)
    data=torch.from_numpy(np.load(args.observations)['observations'][:256])
    assert data.shape==(256,137)
    with torch.no_grad():
        a,b=[module(data) for module in modules]
        assert torch.equal(a,b),'Frozen normalization changed'
        for module in modules:module.train();module(data)
    fractions=[len(data)/(old+len(data)),len(data)/(1+len(data))]
    assert float(modules[0].count)==old+256 and float(modules[1].count)==257
    for module,source_count in zip(modules,[old,1.]):
        expected=source['running_mean_std.running_mean']+(data.mean(0)-source['running_mean_std.running_mean'])*256/(source_count+256)
        assert torch.allclose(module.running_mean,expected,rtol=1e-12,atol=1e-12)
    torch.save({0:dict(model=model,epoch=0,frame=0)},args.output/'teacher.pth')
    saved=torch.load(args.output/'teacher.pth',map_location='cpu')[0]['model']
    assert all(torch.equal(model[k],v) for k,v in saved.items())
    report=dict(status='prepared',scope=__doc__,source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
        policy_sha256=hashlib.sha256((args.output/'teacher.pth').read_bytes()).hexdigest(),
        changed_key=name,old_count=old,new_count=1.,learned_weights_unchanged=True,
        frozen_normalization_bitwise_equal=True,first256_update_new_data_fraction=fractions,
        observation_source_sha256=hashlib.sha256(args.observations.read_bytes()).hexdigest(),
        source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        optimizer='Not included; fresh Adam and counters required for both comparison arms')
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
