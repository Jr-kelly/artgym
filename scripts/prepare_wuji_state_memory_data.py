"""Reconstruct causal30Hz sensor sequences from overlapping50-frame recordings.

Object-state labels remain at their recorded7.5Hz frequency. No future sensor
value enters a reconstructed current history. Every46-frame overlap must match
exactly, and the original150 input histories are recovered exactly.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder,SCALES
from scripts.wuji_state_memory import sensor_features
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def reconstruct(history):
    assert history.shape==(150,90,2055)
    frames=history[...,:2000].reshape(150,90,50,40)
    assert np.array_equal(frames[1:,:,:46],frames[:-1,:,4:])
    initial=history[:,:,2000:]
    assert np.array_equal(initial,np.broadcast_to(initial[:1],initial.shape))
    # Index0 corresponds to actual time-49; index49 is actual control step0.
    full=np.concatenate([frames[0].transpose(1,0,2),
        frames[1:,:,-4:,:].transpose(0,2,1,3).reshape(149*4,90,40)],axis=0)
    assert full.shape==(646,90,40)
    restored=np.stack([full[t:t+50].transpose(1,0,2).reshape(90,2000) for t in range(0,597,4)])
    assert np.array_equal(restored,history[...,:2000])
    return full,initial[0]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,required=True)
    p.add_argument('--datasets',type=Path,nargs=4,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    torch.set_num_threads(4);device=torch.device('cuda:0')
    artifact=torch.load(args.initial,map_location='cpu')
    assert digest(args.initial)==json.loads(args.initial.with_suffix('.json').read_text())['sha256']
    assert artifact['phase']=='offline_teacher_fit'
    base,spec=make_encoder(artifact['encoder_spec']);base.load_state_dict(artifact['state_encoder']);base.to(device).eval()
    before=tensor_digest(base.state_dict())
    ratio=torch.tensor(artifact['output_scales'],device=device)/torch.tensor(SCALES,device=device)
    sources=[];all_features=[];all_base=[];all_targets=[];all_active=[]
    initial_rows=None;train_rows=None
    for key,path in zip(['teacher2','teacher5','student2','student5'],args.datasets):
        manifest=json.loads(path.with_name('dataset-manifest.json').read_text())
        assert digest(path)==manifest['dataset_sha256'] and manifest['status']=='passed'
        assert manifest['source_teacher_sha256']==artifact['teacher_sha256']
        with np.load(path) as z:
            history=z['history'];targets=z['target'];active=z['active'];rows=z['initial_rows'];training=z['train_rows']
            assert np.array_equal(z['step'],np.arange(0,600,4))
        assert active.all() and np.array_equal(training,rows%100<20)
        if initial_rows is not None:assert np.array_equal(initial_rows,rows) and np.array_equal(train_rows,training)
        initial_rows,train_rows=rows,training
        full,initial=reconstruct(history)
        features=[];predictions=[]
        with torch.no_grad():
            for start in range(0,597,4):
                end=min(597,start+4)
                inp=np.stack([np.concatenate([full[t:t+50].transpose(1,0,2).reshape(90,2000),initial],axis=-1) for t in range(start,end)])
                x=torch.from_numpy(inp.reshape(-1,2055)).to(device)
                prediction=base(x)*ratio
                assert torch.isfinite(prediction).all()
                features.append(sensor_features(x,prediction).cpu().numpy().reshape(end-start,90,103))
                predictions.append(prediction.cpu().numpy().reshape(end-start,90,8))
        feature=np.concatenate(features);prediction=np.concatenate(predictions)
        assert feature.shape==(597,90,103) and prediction.shape==(597,90,8)
        assert np.array_equal(feature[:,:,0:40],full[49:])
        assert np.array_equal(feature[:,:,40:95],np.broadcast_to(initial[None],(597,90,55)))
        all_features.append(feature);all_base.append(prediction);all_targets.append(targets);all_active.append(active)
        sources.append(dict(key=key,path=str(path),sha256=digest(path),overlaps_exact=True,
            original_histories_restored_exact=True,physics_collection_policy=manifest.get('collection_policy','teacher')))
        atomic_json(args.output/'status.json',dict(status='preparing',last=key,heartbeat=now(),sources=sources))
    assert tensor_digest(base.state_dict())==before
    features=np.stack(all_features)
    values=features[:,:,train_rows].reshape(-1,103).astype(np.float64)
    mean=values.mean(0).astype(np.float32);scale=np.maximum(values.std(0),1e-3).astype(np.float32)
    dataset=args.output/'memory-features.npz'
    np.savez_compressed(dataset,features=features,base_prediction=np.stack(all_base),target=np.stack(all_targets),
        active=np.stack(all_active),initial_rows=initial_rows,train_rows=train_rows,label_steps=np.arange(0,597,4),
        feature_mean=mean,feature_scale=scale)
    result=dict(status='completed',completed=now(),sources=sources,dataset_sha256=digest(dataset),
        initial_sha256=digest(args.initial),teacher_sha256=artifact['teacher_sha256'],base_unchanged=True,
        feature_shape=list(features.shape),observed_labels_shape=[4,150,90,8],normalizer_rows=initial_rows[train_rows].tolist(),
        scope=__doc__,no_physics_generated=True,no_future_sensor_features=True,source_sha256=digest(Path(__file__)))
    atomic_json(args.output/'manifest.json',result);atomic_json(args.output/'status.json',result);print(json.dumps(result))


if __name__=='__main__':main()
