"""Paired fixed-data fit: distinguish output parameterization from physical loss weights.

Both networks start with identical tensors, identical zero physical predictions,
identical batches and physical SmoothL1 objectives. This diagnoses optimization
conditioning only; neither model is counted as a successful closed-loop student.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common  # IsaacGym before torch.
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder, SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--initial',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    assert not args.output.exists()
    args.output.mkdir(parents=True)
    torch.set_num_threads(4)
    device=torch.device('cuda:0')
    manifest=json.loads(args.dataset.with_name('dataset-manifest.json').read_text())
    assert manifest['status']=='passed'
    assert hashlib.sha256(args.dataset.read_bytes()).hexdigest()==manifest['dataset_sha256']
    meta=json.loads(args.initial.with_suffix('.json').read_text())
    assert hashlib.sha256(args.initial.read_bytes()).hexdigest()==meta['sha256']
    artifact=torch.load(args.initial,map_location='cpu')
    assert artifact['phase']=='warmup' and artifact['update']==0
    with np.load(args.dataset) as z:
        history=z['history'];labels=z['target'];active=z['active']
        training=active & z['train_rows'][None,:]
        validation=active & ~z['train_rows'][None,:]
        train_x=torch.from_numpy(history[training]).to(device)
        train_y=torch.from_numpy(labels[training]).to(device)
        val_x=torch.from_numpy(history[validation]).to(device)
        val_y=torch.from_numpy(labels[validation]).to(device)
        row_matrix=np.broadcast_to(z['initial_rows'][None,:],active.shape)
        val_groups=torch.from_numpy((row_matrix[validation]//100).copy()).to(device)
    assert len(train_x)>8000 and len(val_x)>4000
    first,spec=make_encoder(artifact['encoder_spec'])
    first.load_state_dict(artifact['state_encoder'])
    first.to(device).eval()
    networks={'precision_units':first,'motion_units':copy.deepcopy(first)}
    initial_hash=tensor_digest(first.state_dict())
    assert initial_hash==tensor_digest(networks['motion_units'].state_dict())
    assert all(torch.count_nonzero(net(train_x[:32]))==0 for net in networks.values())
    scales={'precision_units':torch.tensor(SCALES,device=device),
            'motion_units':torch.tensor([.01,.01,.01,.2,.2,.2,.05,.1],device=device)}
    loss_scales=torch.tensor(SCALES,device=device)
    optimizers={key:torch.optim.Adam(net.parameters(),lr=2e-4) for key,net in networks.items()}
    generator=torch.Generator(device='cpu').manual_seed(20261072)
    state=dict(status='running',started=now(),updates_completed=0,initial_tensor_sha256=initial_hash,
        training_samples=len(train_x),validation_samples=len(val_x),batch_size=512,updates_budget=1000,
        dataset_sha256=manifest['dataset_sha256'],initial_artifact_sha256=meta['sha256'],
        physical_loss_scales=SCALES,output_scales={k:s.cpu().tolist() for k,s in scales.items()},
        scope=__doc__)
    atomic_json(args.output/'status.json',state)
    rows=[]
    def evaluate(update):
        for key,net in networks.items():
            with torch.no_grad():
                predictions=torch.cat([net(val_x[i:i+512])*scales[key] for i in range(0,len(val_x),512)])
                error=predictions-val_y
                assert torch.isfinite(error).all()
                row=dict(update=update,arm=key,rmse=error.square().mean(0).sqrt().cpu().tolist(),
                    mae=error.abs().mean(0).cpu().tolist(),
                    per_grasp_rmse=[error[val_groups==i].square().mean(0).sqrt().cpu().tolist() for i in [0,1,2]])
            rows.append(row)
            print(json.dumps(row),flush=True)
        atomic_json(args.output/'validation.json',rows)
    try:
        evaluate(0)
        for update in range(1,1001):
            indices=torch.randint(len(train_x),(512,),generator=generator).to(device)
            x,y=train_x[indices],train_y[indices]
            metrics={}
            for key,net in networks.items():
                optimizer=optimizers[key]
                optimizer.zero_grad(set_to_none=True)
                prediction=net(x)*scales[key]
                loss=torch.nn.functional.smooth_l1_loss((prediction-y)/loss_scales,torch.zeros_like(y))
                assert torch.isfinite(loss)
                loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
                optimizer.step()
                metrics[key]=dict(loss=float(loss.detach()),grad_norm=float(norm))
            if update in [1,25,100,250,500,1000]:
                evaluate(update)
                for key,net in networks.items():
                    path=args.output/('%s-update%04d.pth'%(key,update))
                    torch.save(dict(state_encoder=net.state_dict(),encoder_spec=spec,output_scales=scales[key].cpu(),
                                    optimizer=optimizers[key].state_dict(),update=update,scope=__doc__),path)
            if update%10==0 or update==1:
                state.update(updates_completed=update,heartbeat=now(),latest=metrics)
                atomic_json(args.output/'status.json',state)
        state.update(status='completed',finished=now(),same_batches=True,same_initial_tensors=True,
                     no_closed_loop_success_claim=True)
        atomic_json(args.output/'status.json',state)
    except BaseException as error:
        state.update(status='failed',error=repr(error),finished=now())
        atomic_json(args.output/'status.json',state)
        raise


if __name__=='__main__':
    main()
