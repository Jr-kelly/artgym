"""Matched full-sequence residual observer fit: persistent GRU vs per-step zero state."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_state_memory import StateMemoryResidual
from scripts.wuji_physical_state_encoder import SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--updates',type=int,default=1000)
    args=p.parse_args();assert not args.output.exists() and args.updates>0;args.output.mkdir(parents=True)
    torch.set_num_threads(4);torch.manual_seed(20261075);device=torch.device('cuda:0')
    manifest=json.loads(args.dataset.with_name('manifest.json').read_text())
    assert digest(args.dataset)==manifest['dataset_sha256'] and manifest['status']=='completed'
    assert digest(args.initial)==manifest['initial_sha256']
    artifact=torch.load(args.initial,map_location='cpu')
    with np.load(args.dataset) as z:
        features=torch.from_numpy(z['features']).to(device)
        base=torch.from_numpy(z['base_prediction']).to(device)
        target=torch.from_numpy(z['target']).to(device)/torch.tensor(SCALES,device=device)
        mean=torch.from_numpy(z['feature_mean']).to(device);scale=torch.from_numpy(z['feature_scale']).to(device)
        train_rows=z['train_rows'];rows=z['initial_rows'];label_steps=z['label_steps']
        assert z['active'].all()
    assert features.shape==(4,597,90,103) and base.shape==(4,597,90,8) and target.shape==(4,150,90,8)
    assert np.array_equal(train_rows,rows%100<20) and np.array_equal(label_steps,np.arange(0,597,4))
    training=torch.from_numpy(np.flatnonzero(train_rows)).to(device)
    validation=torch.from_numpy(np.flatnonzero(~train_rows)).to(device)
    assert training.numel()==60 and validation.numel()==30
    # cuDNN requires training mode to retain the reserve space for backward.
    # This single-layer GRU has no dropout; validation explicitly uses eval.
    first=StateMemoryResidual(mean,scale,64).to(device).train()
    nets={'persistent':first,'reset_each_step':copy.deepcopy(first)}
    initial_tensor=tensor_digest(first.state_dict())
    assert tensor_digest(nets['reset_each_step'].state_dict())==initial_tensor
    optimizers={k:torch.optim.Adam(n.parameters(),lr=2e-4) for k,n in nets.items()}
    rng=torch.Generator(device='cpu').manual_seed(20261075)
    status=dict(status='running',started=now(),scope=__doc__,initial_sha256=digest(args.initial),
        dataset_sha256=digest(args.dataset),initial_residual_sha256=initial_tensor,updates_budget=args.updates,
        updates_completed=0,lr=2e-4,batch_sequences=16,sequence_steps=597,label_steps=150,
        supervised_samples_each=0,causal_sensor_frames_each=0,same_initial_tensors=True,
        training_rows=rows[train_rows].tolist(),validation_rows=rows[~train_rows].tolist(),
        validation_excluded=True,normalizer_training_only=True,no_physics_during_fit=True)
    atomic_json(args.output/'status.json',status);validations=[]
    def save(update):
        for arm,net in nets.items():
            path=args.output/f'{arm}-update{update:04d}.pth';assert not path.exists()
            payload=dict(artifact)
            payload.update(memory_encoder=net.state_dict(),feature_mean=mean.cpu(),feature_scale=scale.cpu(),
                hidden_size=64,memory_arm=arm,phase='offline_state_memory',update=update,
                memory_optimizer=optimizers[arm].state_dict(),memory_provenance=dict(scope=__doc__,
                base_sha256=digest(args.initial),dataset_sha256=digest(args.dataset),updates=update,
                supervised_samples=update*2400,causal_sensor_frames=update*9552,
                same_batches=True,training_rows=rows[train_rows].tolist(),validation_excluded=True))
            torch.save(payload,path)
            atomic_json(path.with_suffix('.json'),dict(sha256=digest(path),created=now(),arm=arm,update=update))
    def evaluate(update):
        with torch.no_grad():
            for arm,net in nets.items():
                net.eval()
                for source,key in enumerate(['teacher2','teacher5','student2','student5']):
                    x=features[source,:,validation];b=base[source,::4,validation];y=target[source,:,validation]
                    residual,_=net(x,reset_each_step=arm=='reset_each_step')
                    e=(b+residual[::4]-y)*torch.tensor(SCALES,device=device)
                    validations.append(dict(arm=arm,update=update,source=key,rmse=e.square().mean((0,1)).sqrt().cpu().tolist()))
                net.train()
        atomic_json(args.output/'validation.json',validations)
    def recurrent_equivalence():
        with torch.no_grad():
            x=features[0,:17,:3]
            for arm,net in nets.items():
                net.eval()
                batched,_=net(x,reset_each_step=arm=='reset_each_step')
                state=None;steps=[]
                for frame in x:
                    value,state=net(frame[None],state,arm=='reset_each_step');steps.append(value)
                error=float((torch.cat(steps)-batched).abs().max())
                assert error<2e-5,error
                status.setdefault('sequential_batch_errors',[]).append(dict(arm=arm,error=error))
                net.train()
    try:
        for net in nets.values():
            assert torch.count_nonzero(net(features[0,:16,:3])[0])==0
        save(0);evaluate(0);recurrent_equivalence()
        for update in range(1,args.updates+1):
            # Four same-source sequences per source; replacement; all597 causal
            # frames unrolled from zero, only150 recorded labels supervised.
            choices=torch.randint(60,(4,4),generator=rng).to(device)
            x=torch.cat([features[i,:,training[choices[i]]] for i in range(4)],dim=1)
            b=torch.cat([base[i,::4,training[choices[i]]] for i in range(4)],dim=1)
            y=torch.cat([target[i,:,training[choices[i]]] for i in range(4)],dim=1)
            assert x.shape==(597,16,103) and y.shape==b.shape==(150,16,8)
            metrics={}
            for arm,net in nets.items():
                optimizer=optimizers[arm];optimizer.zero_grad(set_to_none=True)
                residual,_=net(x,reset_each_step=arm=='reset_each_step')
                loss=torch.nn.functional.smooth_l1_loss(b+residual[::4],y)
                assert torch.isfinite(loss);loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
                optimizer.step();assert all(torch.isfinite(v).all() for v in net.state_dict().values())
                metrics[arm]=dict(loss=float(loss.detach()),grad_norm=float(norm))
            if update in [1,100,250,500,args.updates]:
                save(update);evaluate(update)
            if update%10==0 or update==1:
                status.update(updates_completed=update,supervised_samples_each=update*2400,
                    causal_sensor_frames_each=update*9552,heartbeat=now(),latest=metrics)
                atomic_json(args.output/'status.json',status);print(json.dumps(dict(update=update,metrics=metrics)),flush=True)
        recurrent_equivalence()
        assert all(tensor_digest(net.state_dict())!=initial_tensor for net in nets.values())
        assert all({int(v['step']) for v in opt.state_dict()['state'].values()}=={args.updates} for opt in optimizers.values())
        status.update(status='completed',finished=now(),updates_completed=args.updates,
            supervised_samples_each=args.updates*2400,causal_sensor_frames_each=args.updates*9552,
            no_task_success_claim=True,optimizer_counters_verified=True)
        atomic_json(args.output/'status.json',status)
    except BaseException as e:
        status.update(status='failed',error=repr(e),finished=now());atomic_json(args.output/'status.json',status);raise


if __name__=='__main__':main()
