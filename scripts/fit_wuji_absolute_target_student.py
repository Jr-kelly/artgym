"""Matched absolute/incremental action imitation on fixed teacher trajectories."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from torch.nn import functional as F
from scripts.wuji_kinematics import WujiKinematics
from scripts.wuji_absolute_target_student import TargetStudent, SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now

ROOT=Path(__file__).resolve().parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--updates',type=int,default=1000)
    p.add_argument('--device',default='cuda:0')
    p.add_argument('--seed',type=int,default=20261078)
    args=p.parse_args()
    assert not args.output.exists() and args.updates>0
    args.output.mkdir(parents=True)
    source=ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data'
    manifest=json.loads((source/'manifest.json').read_text())
    dataset=source/'memory-features.npz'
    assert sha(dataset)==manifest['dataset_sha256']
    with np.load(dataset) as z:
        sensor=z['features'][:2,:,:,:95].copy()
        rows=z['initial_rows']; training=z['train_rows']
    assert sensor.shape==(2,597,90,95)
    assert np.array_equal(training,rows%100<20)
    states_path=ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy'
    states=np.load(states_path)[rows]
    initial=states[:,20:40]
    kin=WujiKinematics()
    lower,upper=kin.lower.astype(np.float32),kin.upper.astype(np.float32)
    initial_normalized=2*(initial-lower)/(upper-lower)-1
    xs=[]; ys={a:[] for a in ['absolute','incremental']}; provenance=[]
    for i,item in enumerate(manifest['sources'][:2]):
        assert item['physics_collection_policy']=='teacher'
        pair=ROOT/'runs'/item['path'].split('/runs/',1)[1]
        assert sha(pair)==item['sha256']
        trace=pair.with_name('trace.npz')
        with np.load(trace) as z:
            target=z['target'][:597,rows].copy(); actions=z['action'][:597,rows].copy()
            goal=z['goal'][:597,rows]-states[None,:,54]
            causal_q=np.concatenate([states[None,:,:20],z['q'][:596,rows]],0)
            incoming=np.concatenate([initial[None],z['target'][:596,rows]],0)
            assert z['active'][:597,rows].all() and not z['invalid'][:597,rows].any()
        qnormal=2*(causal_q-lower)/(upper-lower)-1
        qerror=float(np.abs(sensor[i,:,:,:20]-qnormal).max())
        assert qerror<2e-6,qerror
        assert np.array_equal(sensor[i,1:,:,20:40],actions[:-1])
        assert np.allclose(goal/.04,np.round(goal/.04),atol=1e-5)
        x=np.concatenate([sensor[i],np.broadcast_to(initial_normalized,(597,90,20)),goal[...,None]/.04],-1)
        xs.append(x)
        absolute=target-initial[None]
        incremental=absolute.copy();incremental[:,:,16:]=target[:,:,16:]-incoming[:,:,16:]
        expected=np.clip(incoming[:,:,16:]+.025*actions[:,:,16:],lower[16:],upper[16:])
        assert np.max(np.abs(expected-target[:,:,16:]))<1e-6
        support_expected=np.clip(initial[None,:,:16]+.04*actions[:,:,:16],lower[:16],upper[:16])
        assert np.max(np.abs(support_expected-target[:,:,:16]))<1e-6
        for a,y in [('absolute',absolute),('incremental',incremental)]:
            ys[a].append(y/np.asarray(SCALES,dtype=np.float32))
        provenance.append(dict(key=item['key'],trace=str(trace.relative_to(ROOT)),trace_sha256=sha(trace),
            history_sha256=sha(pair),causal_joint_max_error=qerror))
    x=np.stack(xs).astype(np.float32)
    ys={a:np.stack(v).astype(np.float32) for a,v in ys.items()}
    fit=x[:,:,training].reshape(-1,116).astype(np.float64)
    mean=fit.mean(0).astype(np.float32);scale=np.maximum(fit.std(0),.01).astype(np.float32)
    np.savez_compressed(args.output/'data.npz',features=x,absolute=ys['absolute'],incremental=ys['incremental'],
        training=training,rows=rows,mean=mean,scale=scale)
    torch.manual_seed(args.seed)
    base=TargetStudent(mean,scale)
    models={a:copy.deepcopy(base).to(args.device) for a in ys}
    assert tensor_digest(models['absolute'].state_dict())==tensor_digest(models['incremental'].state_dict())
    initial_digest=tensor_digest(base.state_dict())
    opts={a:torch.optim.Adam(m.parameters(),lr=2e-4) for a,m in models.items()}
    tensors=torch.tensor(x,device=args.device)
    labels={a:torch.tensor(y,device=args.device) for a,y in ys.items()}
    train_ids=torch.tensor(np.flatnonzero(training),device=args.device)
    val_ids=torch.tensor(np.flatnonzero(~training),device=args.device)
    generator=torch.Generator(device=args.device);generator.manual_seed(args.seed+1)
    state=dict(status='running',started=now(),updates_budget=args.updates,updates_completed=0,
        samples_each=0,seed=args.seed,teacher_sha256=manifest['teacher_sha256'],
        dataset_sha256=sha(args.output/'data.npz'),sources=provenance,
        training_rows=rows[training].tolist(),validation_rows=rows[~training].tolist(),
        training_labels=2*597*int(training.sum()),validation_labels=2*597*int((~training).sum()),
        initial_tensor_sha256=initial_digest,initial_states_sha256=sha(states_path),
        no_new_physics=True,normalization_training_only=True,architecture=[116,256,128,20],
        scope=__doc__,loss='SmoothL1 beta0.05; command errors /(.04rad support,.3rad thumb)',
        observations='current normalized20jointangles + preceding20actions + knowninitial55 + knowninitial20commandtargets + externalgoal',
        learning_rate=2e-4,batch=512,validation=[])
    atomic_json(args.output/'status.json',state)
    def save(update):
        validation={}
        for a,m in models.items():
            metrics={}
            with torch.no_grad():
                for i,seconds in enumerate([2,5]):
                    errors=[]
                    vx=tensors[i,:,val_ids].reshape(-1,116)
                    vy=labels[a][i,:,val_ids].reshape(-1,20)
                    for start in range(0,len(vx),2048):
                        errors.append((m(vx[start:start+2048])-vy[start:start+2048])*vx.new_tensor(SCALES))
                    err=torch.cat(errors)
                    metrics[str(seconds)]=dict(rmse_rad=torch.sqrt(err.square().mean(0)).cpu().tolist(),
                        thumb_rmse_rad=float(torch.sqrt(err[:,16:].square().mean())))
            validation[a]=metrics
            path=args.output/f'{a}-update{update:04d}.pth'
            artifact=dict(state_dict={k:v.detach().cpu() for k,v in m.state_dict().items()},
                feature_mean=mean,feature_scale=scale,arm=a,update=update,provenance={k:v for k,v in state.items() if k!='validation'},
                lower=lower,upper=upper,output_scales=SCALES,optimizer=opts[a].state_dict())
            torch.save(artifact,path)
            atomic_json(path.with_suffix('.json'),dict(sha256=sha(path),arm=a,update=update,validation=metrics))
        state['validation'].append(dict(update=update,arms=validation))
    save(0)
    for u in range(1,args.updates+1):
        source_ids=torch.arange(2,device=args.device).repeat_interleave(256)
        times=torch.randint(597,(512,),device=args.device,generator=generator)
        ids=train_ids[torch.randint(len(train_ids),(512,),device=args.device,generator=generator)]
        bx=tensors[source_ids,times,ids]
        for a,m in models.items():
            opts[a].zero_grad(set_to_none=True)
            loss=F.smooth_l1_loss(m(bx),labels[a][source_ids,times,ids],beta=.05)
            assert torch.isfinite(loss)
            loss.backward();grad=torch.nn.utils.clip_grad_norm_(m.parameters(),1.)
            assert torch.isfinite(grad)
            opts[a].step()
        state.update(updates_completed=u,samples_each=u*512,heartbeat=now())
        if u in [250,args.updates]:
            save(u)
        if u%100==0:
            atomic_json(args.output/'status.json',state)
    state.update(status='completed',finished=now())
    atomic_json(args.output/'status.json',state)
    print(json.dumps(state))


if __name__=='__main__':
    main()
