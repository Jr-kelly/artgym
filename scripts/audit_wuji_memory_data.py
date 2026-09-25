"""Independently verify causal sensor indices, train-only scaling and cached predictions."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder,SCALES


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--device',choices=['cpu','cuda:0'],default='cpu')
    args=p.parse_args();assert not args.output.exists()
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((args.folder/'manifest.json').read_text())
    dataset=args.folder/'memory-features.npz';assert digest(dataset)==manifest['dataset_sha256']
    initial=root/'runs/wuji-goal/diagnostics/state-scale-2036-v1/artifacts/precision_units.pth'
    assert digest(initial)==manifest['initial_sha256']
    artifact=torch.load(initial,map_location='cpu');net,_=make_encoder(artifact['encoder_spec'])
    net.load_state_dict(artifact['state_encoder']);net.to(args.device).eval();torch.set_num_threads(4)
    ratio=(torch.as_tensor(artifact['output_scales'])/torch.tensor(SCALES)).to(args.device)
    with np.load(dataset) as z:
        feat=z['features'];base=z['base_prediction'];labels=z['target'];train=z['train_rows'];rows=z['initial_rows']
        mean=z['feature_mean'];scale=z['feature_scale']
    assert np.array_equal(train,rows%100<20)
    assert feat.shape==(4,597,90,103) and np.array_equal(feat[...,-8:],base)
    comparisons=[]
    for source,item in enumerate(manifest['sources']):
        remote=Path(item['path']);path=root/'runs'/str(remote).split('/runs/',1)[1]
        assert digest(path)==item['sha256']
        with np.load(path) as z:hist=z['history'];target=z['target']
        assert np.array_equal(target,labels[source])
        sensors=hist[...,:2000].reshape(150,90,50,40)
        assert np.array_equal(sensors[1:,:,:46],sensors[:-1,:,4:])
        # Use the next saved window as a container, selecting only the sensor
        # value whose absolute time equals the queried control step.
        current=[]
        for t in range(597):
            saved=(t+3)//4;index=49+t-4*saved
            assert 0<=index<50 and 4*saved-49+index==t
            current.append(sensors[saved,:,index])
        current=np.stack(current)
        assert np.array_equal(current,feat[source,:,:,:40])
        assert np.array_equal(feat[source,:, :,40:95],np.broadcast_to(hist[0,:,2000:][None],(597,90,55)))
        checked=[];x=[];expected=[]
        for t in [0,1,2,3,4,49,149,300,596]:
            # Original step0 padding covers negative times. Every positive
            # frame in this history is from current[t-49:t], never aftert.
            history=np.stack([sensors[0,:,49+k] if k<0 else current[k] for k in range(t-49,t+1)],axis=1)
            flat=np.concatenate([history.reshape(90,2000),hist[0,:,2000:]],axis=-1)
            assert max(range(t-49,t+1))==t
            if t%4==0:assert np.array_equal(flat,hist[t//4])
            x.append(flat[[0,20,40,80]]);expected.append(base[source,t,[0,20,40,80]])
            checked.append(t)
        with torch.no_grad():prediction=(net(torch.from_numpy(np.concatenate(x)).to(args.device))*ratio).cpu().numpy()
        differences=np.abs(prediction-np.concatenate(expected))
        error=float(differences.max())
        physical_error=(differences*np.array(SCALES)).max(0)
        # CPU and GPU/TF32 kernels are not bitwise equal. The sensor histories,
        # index causality and normalizer checks above/below remain exact.
        bounds=np.array([5e-5,5e-5,5e-5,1e-3,1e-3,1e-3,5e-5,1e-3])
        assert (physical_error<bounds).all(),physical_error
        comparisons.append(dict(source=item['key'],current_values_exact=True,initial_fields_exact=True,
            truth_labels_unchanged=True,checked_steps=checked,checked_rows=[0,20,40,80],prediction_max_normalized=error,
            prediction_max_SI=physical_error.tolist(),prediction_bound_SI=bounds.tolist()))
    values=feat[:,:,train].reshape(-1,103).astype(np.float64)
    recomputed_mean=values.mean(0).astype(np.float32);recomputed_scale=np.maximum(values.std(0),1e-3).astype(np.float32)
    assert np.array_equal(recomputed_mean,mean) and np.array_equal(recomputed_scale,scale)
    result=dict(status='passed',dataset_sha256=digest(dataset),initial_sha256=digest(initial),
        device=args.device,causal_indexing_verified=True,feature_normalizer_recomputed_exact=True,
        normalizer_training_rows=rows[train].tolist(),validation_rows_excluded=rows[~train].tolist(),
        comparisons=comparisons,scope='Cached data audit on existing development trajectories.597causal30Hzframes,150physicallabels;last3unrecordedcontrolsteps are not reconstructed. No task success claim.')
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
