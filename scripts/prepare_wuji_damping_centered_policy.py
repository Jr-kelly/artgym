"""Create an explicit normalizer-only warm start for known simulated damping.

All learned weights, variances, counts and other observation statistics are
unchanged. The single damping mean is translated from nominal 0.3 to nominal 3.
This changes the policy and must use a new artifact identity. It does not alter
physics or report a false damping observation, and is not hardware calibration.
The resulting policy has not yet learned under the new dynamics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import torch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    destination=args.output/'teacher.pth'
    assert not destination.exists()
    original=torch.load(args.source,map_location='cpu')
    s=original[0] if 0 in original else original
    model={k:v.clone() for k,v in s['model'].items()}
    key='running_mean_std.running_mean'
    index=128
    old=model[key][index].clone()
    assert model[key].shape==(137,) and abs(float(old)-.3)<1e-6
    model[key][index]+=2.7
    differences=[]
    for name,tensor in model.items():
        count=int(torch.count_nonzero(tensor!=s['model'][name]))
        if count:differences.append(dict(name=name,changed_elements=count))
    assert differences==[dict(name=key,changed_elements=1)]
    changed_indices=(model[key]!=s['model'][key]).nonzero().flatten().tolist()
    assert changed_indices==[index]
    # This artifact intentionally contains no stale optimizer/environment state.
    # Any later training must start a fresh optimizer and counters.
    torch.save({0:dict(model=model,epoch=0,frame=0)},destination)
    loaded=torch.load(destination,map_location='cpu')[0]['model']
    assert all(torch.equal(value,loaded[name]) for name,value in model.items())
    report=dict(status='prepared_for_independent_evaluation',scope=__doc__,
                source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
                policy_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                changes=differences,index=index,old_mean=float(old),new_mean=float(model[key][index]),
                old_nominal_damping=.3,new_nominal_damping=3.,optimizer='Not included; fresh optimizer required',
                source_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
