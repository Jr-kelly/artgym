"""Independently check temporal command labels and the completed optimizers."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--fit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists()
    meta=json.loads((args.fit/'status.json').read_text())
    assert meta['status']=='completed' and meta['updates_completed']==1000
    with np.load(args.fit/'data.npz') as z:
        x=z['features'];ids=z['rows'];train=z['training'];mean=z['mean'];scale=z['scale']
        labels={a:z[a] for a in ['absolute','incremental']}
    assert not np.intersect1d(ids[train],ids[~train]).size
    values=x[:,:,train].reshape(-1,116).astype(np.float64)
    assert np.array_equal(values.mean(0).astype(np.float32),mean)
    assert np.array_equal(np.maximum(values.std(0),.01).astype(np.float32),scale)
    states=np.load(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')[ids]
    report=[]
    for a in ['absolute','incremental']:
        initial=torch.load(args.fit/f'{a}-update0000.pth',map_location='cpu')
        final_path=args.fit/f'{a}-update1000.pth';final=torch.load(final_path,map_location='cpu')
        assert tensor_digest(initial['state_dict'])==meta['initial_tensor_sha256']
        assert torch.count_nonzero(initial['state_dict']['net.4.weight'])==0
        assert torch.count_nonzero(initial['state_dict']['net.4.bias'])==0
        counters=[int(v['step']) for v in final['optimizer']['state'].values()]
        assert counters and set(counters)=={1000}
        assert all(torch.isfinite(t).all() for t in final['state_dict'].values())
        assert tensor_digest(final['state_dict'])!=tensor_digest(initial['state_dict'])
        errors=[]
        for i,source in enumerate(meta['sources']):
            path=ROOT/source['trace']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==source['trace_sha256']
            with np.load(path) as z:
                actual=z['target'][:597,ids].astype(np.float64)
                incoming=np.concatenate([states[None,:,20:40],z['target'][:596,ids]],0).astype(np.float64)
                actions=z['action'][:597,ids]
                causal_q=np.concatenate([states[None,:,:20],z['q'][:596,ids]],0)
                goal=z['goal'][:597,ids]-states[None,:,54]
            assert np.array_equal(x[i,1:,:,20:40],actions[:-1])
            assert np.allclose(x[i,:,:,115],goal/.04,atol=1e-6)
            current_q=(x[i,:,:,:20]+1)/2*(final['upper']-final['lower'])+final['lower']
            assert np.max(np.abs(current_q-causal_q))<3e-7
            reconstructed=labels[a][i].astype(np.float64)*np.array([.04]*16+[.3]*4)+states[None,:,20:40]
            if a=='incremental':
                reconstructed[:,:,16:]=incoming[:,:,16:]+labels[a][i,:,:,16:]*.3
            error=float(np.max(np.abs(reconstructed-actual)));assert error<1e-6,error
            errors.append(error)
        report.append(dict(arm=a,optimizer_steps=counters,label_reconstruction_max_error_rad=errors,
            final_sha256=hashlib.sha256(final_path.read_bytes()).hexdigest()))
    atomic_json(args.output,dict(status='passed',created=now(),rows=report,normalizer_training_only=True,
        supervised_samples_each=512000,training_labels=71640,validation_labels=35820,
        zero_initial_heads_same_tensors=True,temporal_alignment='currentq=previousphysicalq,previousaction=trace[t-1],labels=issuedtarget[t]',
        no_new_physics=True,no_task_success_claim=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    print(json.dumps(report))


if __name__=='__main__':
    main()
