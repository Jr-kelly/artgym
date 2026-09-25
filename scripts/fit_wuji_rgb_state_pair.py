"""Matched RGB versus masked-RGB state fitting on fixed teacher trajectories.

No physics runs here. A lower held-out state error is only a sensor-model
diagnostic; frozen closed-loop policy evaluation remains necessary.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from torch.nn import functional as F
from scripts.wuji_rgb_state_model import RGBStateModel,OUTPUT_SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--updates',type=int,default=5000);p.add_argument('--device',default='cuda:0')
    p.add_argument('--seed',type=int,default=20261084);p.add_argument('--runtime-check',action='store_true')
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    assert not args.runtime_check or args.updates<=2
    torch.set_num_threads(4)
    spec=json.loads(args.data_spec.read_text());root=Path(spec['root'])
    xs=[];ys=[];images=[];train_flags=[];domain_flags=[];sources=[]
    for source in spec['collections']:
        folder=root/source['path'];statepath=folder/'collection-status.json'
        assert hashlib.sha256(statepath.read_bytes()).hexdigest()==source['status_sha256']
        status=json.loads(statepath.read_text());assert status['status']=='completed'
        rows=np.asarray(status['selected_initial_rows'])
        assert len(rows)>0 and np.isin(rows%100,np.arange(30)).all() and (rows<300).all()
        domain=source.get('domain','teacher');assert domain in ['teacher','ownstate']
        accepted=excluded=0
        for chunk in status['chunks']:
            path=folder/chunk['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==chunk['sha256']
            with np.load(path) as z:
                active=z['active'].astype(bool)
                assert np.isfinite(z['target'][active]).all()
                rgb=z['rgb'];x=np.concatenate([z['known_initial'],z['proprio'],z['goal']],-1)
                y=z['target'][...,:7];flags=np.broadcast_to(rows%100<20,y.shape[:2])
                if args.runtime_check:
                    rgb=rgb[:1,::10].copy();x=x[:1,::10];y=y[:1,::10];flags=flags[:1,::10];active=active[:1,::10]
                accepted+=int(active.sum());excluded+=int((~active).sum())
                images.append(rgb[active]);xs.append(x[active]);ys.append(y[active]);train_flags.append(flags[active])
                domain_flags.append(np.full(int(active.sum()),domain=='ownstate',dtype=bool))
        sources.append(dict(path=source['path'],status_sha256=source['status_sha256'],teacher_sha256=status['teacher_sha256'],
            domain=domain,active_samples=accepted,inactive_excluded=excluded))
    rgb=np.concatenate(images);x=np.concatenate(xs).astype(np.float32);y=np.concatenate(ys).astype(np.float32)
    del images,xs,ys
    train=np.concatenate(train_flags);ownstate=np.concatenate(domain_flags)
    assert len(rgb)==len(x)==len(y)==len(train)==len(ownstate)
    if not args.runtime_check:
        assert len(x)==spec.get('active_samples',36000) and int(train.sum())==spec.get('training_samples',24000)
    normalization_train=train & ~ownstate
    mean=x[normalization_train].astype(np.float64).mean(0).astype(np.float32)
    scale=np.maximum(x[normalization_train].astype(np.float64).std(0),.01).astype(np.float32)
    if spec.get('normalization_artifact'):
        normalizer_path=root/spec['normalization_artifact']['path']
        assert hashlib.sha256(normalizer_path.read_bytes()).hexdigest()==spec['normalization_artifact']['sha256']
        normalizer=torch.load(normalizer_path,map_location='cpu')
        if not args.runtime_check:
            assert np.allclose(mean,normalizer['feature_mean'],atol=2e-7,rtol=1e-6)
            assert np.allclose(scale,normalizer['feature_scale'],atol=2e-7,rtol=1e-6)
        mean=normalizer['feature_mean'].copy();scale=normalizer['feature_scale'].copy()
    labels=y/np.asarray(OUTPUT_SCALES,dtype=np.float32)
    train_ids=torch.tensor(np.flatnonzero(train),device=args.device)
    val_ids=torch.tensor(np.flatnonzero(~train),device=args.device)
    by_domain={name:torch.tensor(np.flatnonzero(train & (ownstate==flag)),device=args.device)
        for name,flag in [('teacher',False),('ownstate',True)]}
    val_domains={name:torch.tensor(np.flatnonzero(~train & (ownstate==flag)),device=args.device)
        for name,flag in [('teacher',False),('ownstate',True)]}
    balanced=bool(spec.get('half_teacher_half_ownstate',False))
    if balanced:assert all(len(v)>0 for v in by_domain.values())
    pictures=torch.tensor(rgb,device=args.device);features=torch.tensor(x,device=args.device)
    targets=torch.tensor(labels,device=args.device);del rgb
    torch.manual_seed(args.seed);base=RGBStateModel(mean,scale)
    initial=tensor_digest(base.state_dict())
    if spec.get('initial_tensor_sha256'):assert initial==spec['initial_tensor_sha256']
    models={a:copy.deepcopy(base).to(args.device).eval() for a in ['rgb','masked']}
    assert all(tensor_digest(m.state_dict())==initial for m in models.values())
    optimizers={a:torch.optim.Adam(m.parameters(),lr=2e-4) for a,m in models.items()}
    generator=torch.Generator(device=args.device);generator.manual_seed(args.seed+1)
    state=dict(status='running',started=now(),scope=__doc__,updates_completed=0,updates_budget=args.updates,
        seed=args.seed,initial_tensor_sha256=initial,training_samples=int(train.sum()),validation_samples=int((~train).sum()),
        actual_optimizer_steps_each=0,samples_seen_each=0,batch=128,learning_rate=2e-4,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),data_spec=spec,sources=sources,
        runtime_check=args.runtime_check,normalization_training_only=True,physics_transitions=0,
        validation=[],input='CurrentRGB+knowninitial55+current20q+previous20actions+externalgoal; maskRGBonlyforpairedcontrol',
        target='bodytranslation3/bodyrotationvector3/sliderposition; no current truth supplied asinput',
        augmentation='Per-image brightness/contrast[.8,1.2], independent RGB noise std.01, trainingonly',
        half_teacher_half_ownstate=balanced,inactive_excluded=sum(s['inactive_excluded'] for s in sources),
        domain_training_samples={k:len(v) for k,v in by_domain.items()},
        domain_validation_samples={k:len(v) for k,v in val_domains.items()},
        normalization_source='Original teacher training rows only; never own-state or validation rows')
    atomic_json(args.output/'status.json',state)
    def save(update):
        result={}
        for arm,model in models.items():
            errors=[]
            with torch.no_grad():
                for ids in val_ids.split(128):
                    im=pictures[ids].permute(0,3,1,2).float()/255.-.5
                    pred=model(im,features[ids],mask_image=arm=='masked')
                    errors.append((pred-targets[ids])*pred.new_tensor(OUTPUT_SCALES))
                error=torch.cat(errors)
                metrics=dict(rmse=torch.sqrt(error.square().mean(0)).cpu().tolist(),max_absolute_error=error.abs().max(0).values.cpu().tolist())
                flags=torch.tensor(ownstate[~train],device=args.device)
                metrics['domains']={name:dict(rmse=error[flags==flag].square().mean(0).sqrt().cpu().tolist(),
                    samples=int((flags==flag).sum())) for name,flag in [('teacher',False),('ownstate',True)] if bool((flags==flag).any())}
            result[arm]=metrics
            path=args.output/f'{arm}-update{update:04d}.pth'
            torch.save(dict(state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                optimizer=optimizers[arm].state_dict(),arm=arm,update=update,feature_mean=mean,feature_scale=scale,
                output_scales=OUTPUT_SCALES,provenance={k:v for k,v in state.items() if k!='validation'}),path)
            atomic_json(path.with_suffix('.json'),dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),arm=arm,update=update,metrics=metrics))
        state['validation'].append(dict(update=update,arms=result));atomic_json(args.output/'status.json',state)
    try:
        save(0)
        for update in range(1,args.updates+1):
            if balanced:
                ids=torch.cat([v[torch.randint(len(v),(64,),generator=generator,device=args.device)] for v in by_domain.values()])
            else:
                ids=train_ids[torch.randint(len(train_ids),(128,),generator=generator,device=args.device)]
            im=pictures[ids].permute(0,3,1,2).float()/255.
            brightness=.8+.4*torch.rand((len(ids),1,1,1),generator=generator,device=args.device)
            contrast=.8+.4*torch.rand((len(ids),1,1,1),generator=generator,device=args.device)
            im=((im-.5)*contrast+.5)*brightness
            im=(im+.01*torch.randn(im.shape,generator=generator,device=args.device)).clamp(0,1)-.5
            losses={}
            for arm,model in models.items():
                optimizer=optimizers[arm];optimizer.zero_grad(set_to_none=True)
                loss=F.smooth_l1_loss(model(im,features[ids],mask_image=arm=='masked'),targets[ids],beta=1.)
                assert torch.isfinite(loss);loss.backward();grad=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
                assert torch.isfinite(grad);optimizer.step();losses[arm]=float(loss)
            state.update(updates_completed=update,actual_optimizer_steps_each=update,samples_seen_each=128*update,
                latest_loss=losses,heartbeat=now())
            if update in [250,1000,args.updates]:save(update)
            elif update%25==0:atomic_json(args.output/'status.json',state)
        for model in models.values():
            assert tensor_digest(model.state_dict())!=initial
            assert torch.equal(model.feature_mean,torch.tensor(mean,device=args.device))
            assert torch.equal(model.feature_scale,torch.tensor(scale,device=args.device))
        with torch.no_grad():
            ids=val_ids[:8];im=pictures[ids].permute(0,3,1,2).float()/255.-.5
            masked=models['masked'](im,features[ids],mask_image=True)
            assert torch.equal(masked,models['masked'](im.flip(0),features[ids],mask_image=True))
            delta=models['rgb'](im,features[ids])-models['rgb'](im.flip(0),features[ids])
            state['image_input_audit']=dict(masked_invariant=True,rgb_max_output_change=float(delta.abs().max()))
        state.update(status='completed',finished=now(),normalizer_unchanged=True)
    except BaseException as exc:
        state.update(status='failed',error=repr(exc),finished=now());raise
    finally:atomic_json(args.output/'status.json',state)
    print(json.dumps(state))


if __name__=='__main__':main()
