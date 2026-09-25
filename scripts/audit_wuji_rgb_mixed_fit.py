"""Independently verify the mixed-data fit, all validation labels and frozen normalizer."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_rgb_state_model import RGBStateModel, OUTPUT_SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fitting',type=Path,required=True);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--device',default='cuda:0')
    args=p.parse_args();assert not args.output.exists();torch.set_num_threads(4)
    state=json.loads((args.fitting/'status.json').read_text());assert state['status']=='completed'
    update=state['updates_budget'];runtime=state['runtime_check'];spec=state['data_spec']
    assert update==(2 if runtime else 5000)
    assert state['half_teacher_half_ownstate'] and state['normalizer_unchanged']
    normalpath=args.root/spec['normalization_artifact']['path']
    assert hashlib.sha256(normalpath.read_bytes()).hexdigest()==spec['normalization_artifact']['sha256']
    original=torch.load(normalpath,map_location='cpu')
    models={};before={};results={}
    for arm in ['rgb','masked']:
        path=args.fitting/f'{arm}-update{update:04d}.pth'
        sha=hashlib.sha256(path.read_bytes()).hexdigest();meta=json.loads(path.with_suffix('.json').read_text())
        assert sha==meta['sha256']
        artifact=torch.load(path,map_location='cpu');initial=torch.load(args.fitting/f'{arm}-update0000.pth',map_location='cpu')
        assert tensor_digest(initial['state_dict'])==spec['initial_tensor_sha256']==tensor_digest(original['state_dict'])
        steps=[int(v['step']) for v in artifact['optimizer']['state'].values()];assert len(steps)==14 and set(steps)=={update}
        assert artifact['arm']==arm and artifact['update']==update
        for key in ['feature_mean','feature_scale']:
            assert np.array_equal(artifact[key],initial[key]) and np.array_equal(artifact[key],original[key])
        model=RGBStateModel(artifact['feature_mean'],artifact['feature_scale'])
        model.load_state_dict(artifact['state_dict']);model.to(args.device).eval()
        models[arm]=model;before[arm]=tensor_digest(model.state_dict())
        assert before[arm]!=spec['initial_tensor_sha256']
        results[arm]=dict(sha256=sha,optimizer_steps=steps,domains={})
    counts={d:dict(training=0,validation=0,inactive=0) for d in ['teacher','ownstate']}
    normal_sum=np.zeros(96);normal_sq=np.zeros(96);normal_n=0;chunks=0
    for source in spec['collections']:
        folder=args.root/source['path'];statepath=folder/'collection-status.json'
        assert hashlib.sha256(statepath.read_bytes()).hexdigest()==source['status_sha256']
        collection=json.loads(statepath.read_text());rows=np.asarray(collection['selected_initial_rows'])
        assert (rows<300).all() and np.isin(rows%100,np.arange(30)).all()
        domain=source['domain'];assert domain in counts
        for c in collection['chunks']:
            path=folder/c['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==c['sha256']
            with np.load(path) as z:
                x=np.concatenate([z['known_initial'],z['proprio'],z['goal']],-1)
                y=z['target'][...,:7];rgb=z['rgb'];active=z['active'].astype(bool)
                train=np.broadcast_to(rows%100<20,active.shape)
                if runtime:
                    x=x[:1,::10];y=y[:1,::10];rgb=rgb[:1,::10];active=active[:1,::10];train=train[:1,::10]
                tx=x[train&active].astype(np.float64)
                counts[domain]['training']+=len(tx);counts[domain]['inactive']+=int((~active).sum())
                if domain=='teacher':
                    normal_sum+=tx.sum(0);normal_sq+=(tx*tx).sum(0);normal_n+=len(tx)
                mask=~train&active;vx=x[mask];vy=y[mask];images=rgb[mask]
                counts[domain]['validation']+=len(vx)
                for start in range(0,len(vx),128):
                    im=torch.tensor(images[start:start+128],device=args.device).permute(0,3,1,2).float()/255.-.5
                    features=torch.tensor(vx[start:start+128],device=args.device)
                    for arm,model in models.items():
                        with torch.no_grad():pred=model(im,features,mask_image=arm=='masked').cpu().numpy()
                        err=pred*np.array(OUTPUT_SCALES)-vy[start:start+128]
                        result=results[arm]['domains'].setdefault(domain,dict(squared=np.zeros(7),maximum=np.zeros(7),samples=0))
                        result['squared']+=(err*err).sum(0);result['maximum']=np.maximum(result['maximum'],np.abs(err).max(0));result['samples']+=len(err)
            chunks+=1
    if not runtime:
        mean=(normal_sum/normal_n).astype(np.float32)
        scale=np.maximum(np.sqrt(np.maximum(normal_sq/normal_n-(normal_sum/normal_n)**2,0)),.01).astype(np.float32)
        assert np.allclose(mean,original['feature_mean'],atol=2e-7,rtol=1e-6)
        assert np.allclose(scale,original['feature_scale'],atol=2e-7,rtol=1e-6)
    for domain,count in counts.items():
        assert count['training']==state['domain_training_samples'][domain]
        assert count['validation']==state['domain_validation_samples'][domain]
    assert sum(c['inactive'] for c in counts.values())==state['inactive_excluded']
    for arm,model in models.items():
        assert tensor_digest(model.state_dict())==before[arm]
        domains=results[arm]['domains'];n=sum(r['samples'] for r in domains.values())
        rmse=np.sqrt(sum(r['squared'] for r in domains.values())/n)
        maximum=np.maximum.reduce([r['maximum'] for r in domains.values()])
        reported=state['validation'][-1]['arms'][arm]
        assert np.allclose(rmse,reported['rmse'],atol=1e-7,rtol=.002)
        assert np.allclose(maximum,reported['max_absolute_error'],atol=1e-6,rtol=.002)
        for domain,result in domains.items():
            result['rmse']=np.sqrt(result.pop('squared')/result['samples']).tolist()
            result['max_absolute_error']=result.pop('maximum').tolist()
            assert np.allclose(result['rmse'],reported['domains'][domain]['rmse'],atol=1e-7,rtol=.002)
        results[arm].update(rmse=rmse.tolist(),max_absolute_error=maximum.tolist())
    atomic_json(args.output,dict(status='passed',finished=now(),arms=results,counts=counts,chunks_verified=chunks,
        updates=update,runtime_check=runtime,physics_transitions=0,models_unchanged=True,
        original_initial_weights_matched=True,original_teacher_training_normalizer_preserved=True,
        inactive_excluded=True,scope='Offline held-out old rows only. Closed-loop and independent task validation are still required.'))
    print(args.output)


if __name__=='__main__':main()
