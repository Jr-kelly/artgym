"""Same-network fixed-budget comparison of provided versus masked command state."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_command_slider import CommandSliderResidual
from scripts.wuji_physical_state_encoder import SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--updates',type=int,default=1000)
    args=p.parse_args();assert not args.output.exists() and args.updates>0;args.output.mkdir(parents=True)
    torch.set_num_threads(4);torch.manual_seed(20261077);device=torch.device('cuda:0')
    manifest=json.loads(args.dataset.with_name('manifest.json').read_text())
    assert digest(args.dataset)==manifest['dataset_sha256'] and digest(args.initial)==manifest['initial_sha256']
    artifact=torch.load(args.initial,map_location='cpu');base_digest=tensor_digest(artifact['state_encoder'])
    with np.load(args.dataset) as z:
        x=torch.from_numpy(z['features']).to(device);base=torch.from_numpy(z['base_prediction'][...,6]).to(device)
        target=torch.from_numpy(z['target'][...,6]).to(device)/SCALES[6]
        rows=z['initial_rows'];training=z['train_rows'];mean=z['feature_mean'];scale=z['feature_scale']
    assert x.shape==(4,150,90,148) and np.array_equal(training,rows%100<20)
    tr=torch.tensor(np.flatnonzero(training),device=device);va=torch.tensor(np.flatnonzero(~training),device=device)
    first=CommandSliderResidual(mean,scale).to(device).train();nets=dict(provided=first,masked=copy.deepcopy(first))
    initial=tensor_digest(first.state_dict());assert tensor_digest(nets['masked'].state_dict())==initial
    optimizers={k:torch.optim.Adam(v.parameters(),lr=2e-4) for k,v in nets.items()}
    rng=torch.Generator(device='cpu').manual_seed(20261077)
    state=dict(status='running',started=now(),initial_sha256=digest(args.initial),dataset_sha256=digest(args.dataset),
        initial_residual_tensor_sha256=initial,updates_budget=args.updates,updates_completed=0,
        samples_each=0,lr=2e-4,batch=512,architecture=[148,128,64,1],same_initial_tensors=True,
        training_rows=rows[training].tolist(),validation_rows=rows[~training].tolist(),validation_excluded=True,
        no_physics=True,changed_output='slider position index6 only',source_sha256=digest(Path(__file__)))
    atomic_json(args.output/'status.json',state);validation=[]
    def evaluate(update):
        with torch.no_grad():
            for arm,net in nets.items():
                for i,key in enumerate(['teacher2','teacher5','student2','student5']):
                    prediction=base[i,:,va]+net(x[i,:,va],arm)
                    e=(prediction-target[i,:,va])*SCALES[6]
                    validation.append(dict(arm=arm,update=update,source=key,rmse_mm=float(e.square().mean().sqrt()*1000),bias_mm=float(e.mean()*1000)))
        atomic_json(args.output/'validation.json',validation)
    def save(update):
        for arm,net in nets.items():
            payload=dict(artifact);payload.update(phase='offline_command_slider',update=update,command_arm=arm,
                command_encoder=net.state_dict(),command_mean=mean,command_scale=scale,
                command_optimizer=optimizers[arm].state_dict(),fitting_provenance=dict(state,updates_completed=update,samples_each=update*512))
            assert tensor_digest(payload['state_encoder'])==base_digest
            path=args.output/f'{arm}-update{update:04d}.pth';assert not path.exists();torch.save(payload,path)
            atomic_json(path.with_suffix('.json'),dict(sha256=digest(path),arm=arm,update=update,created=now()))
    try:
        with torch.no_grad():
            assert all(torch.count_nonzero(net(x[0,:2,:3],arm))==0 for arm,net in nets.items())
        save(0);evaluate(0)
        for update in range(1,args.updates+1):
            indices=torch.randint(9000,(4,128),generator=rng).to(device)
            batch=torch.cat([x[i,:,tr].reshape(9000,148)[indices[i]] for i in range(4)])
            b=torch.cat([base[i,:,tr].reshape(9000)[indices[i]] for i in range(4)])
            y=torch.cat([target[i,:,tr].reshape(9000)[indices[i]] for i in range(4)])
            losses={}
            for arm,net in nets.items():
                opt=optimizers[arm];opt.zero_grad(set_to_none=True)
                loss=torch.nn.functional.smooth_l1_loss(b+net(batch,arm),y)
                assert torch.isfinite(loss);loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True);opt.step()
                losses[arm]=dict(loss=float(loss.detach()),grad_norm=float(norm))
            if update in [1,100,250,500,args.updates]:save(update);evaluate(update)
            if update%20==0 or update==args.updates:
                state.update(updates_completed=update,samples_each=update*512,heartbeat=now(),latest=losses)
                atomic_json(args.output/'status.json',state)
        for arm,net in nets.items():
            assert tensor_digest(net.state_dict())!=initial
            assert all(torch.isfinite(v).all() for v in net.state_dict().values())
            for v in optimizers[arm].state.values():assert int(v['step'])==args.updates
        state.update(status='completed',finished=now(),optimizer_counters_verified=True,base_unchanged=True)
        atomic_json(args.output/'status.json',state);print(json.dumps(state))
    except BaseException as e:
        state.update(status='failed',error=repr(e),finished=now());atomic_json(args.output/'status.json',state);raise


if __name__=='__main__':main()
