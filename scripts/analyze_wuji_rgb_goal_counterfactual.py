"""Measure state-estimate changes when only the external command is flipped.

The physical image, proprioception and initial state stay identical. This is
a diagnostic of a possible command shortcut, not evidence of task success.
Only old validation rows and the first/last sampled frame of each chunk are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_rgb_state_model import RGBStateModel,OUTPUT_SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json,now


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists();args.output.mkdir(parents=True);torch.set_num_threads(4)
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal';models={};before={};model_hashes={}
    for variant,folder in [('baseline','rgb-state-fitting-1537-v2'),('mixed','rgb-mixed-fitting-1705-v1')]:
        for arm in ['rgb','masked']:
            path=base/'diagnostics'/folder/'fitting'/(arm+'-update5000.pth');sha=hashlib.sha256(path.read_bytes()).hexdigest()
            assert sha==json.loads(path.with_suffix('.json').read_text())['sha256']
            a=torch.load(path,map_location='cpu');m=RGBStateModel(a['feature_mean'],a['feature_scale']);m.load_state_dict(a['state_dict']);m.eval()
            key=variant+'-'+arm;models[key]=m;before[key]=tensor_digest(m.state_dict());model_hashes[key]=sha
    spec=json.loads((base/'rgb-mixed-fit-data-spec-1705-v1.json').read_text());items=[];records={k:[] for k in models};stride_audit=[]
    for source in spec['collections']:
        folder=root/source['path'];statuspath=folder/'collection-status.json';assert hashlib.sha256(statuspath.read_bytes()).hexdigest()==source['status_sha256']
        s=json.loads(statuspath.read_text());rows=np.asarray(s['selected_initial_rows']);selected=rows%100>=20
        command_steps=int(s['clock_seconds']*30);all_steps=[]
        for c in s['chunks']:
            path=folder/c['path'];sha=hashlib.sha256(path.read_bytes()).hexdigest();assert sha==c['sha256']
            with np.load(path) as z:
                all_steps.extend(map(int,z['step']));frame_ids=np.array([0,len(z['step'])-1])
                images=z['rgb'][frame_ids][:,selected].reshape(-1,320,320,3)
                x=np.concatenate([z['known_initial'],z['proprio'],z['goal']],-1)[frame_ids][:,selected].reshape(-1,96)
                truth=z['target'][frame_ids][:,selected,:7].reshape(-1,7)
                assert z['active'][frame_ids][:,selected].all()
                assert np.isclose(x[:,95],0,atol=1e-7).all() or np.isin(np.round(x[:,95],6),[0,.04]).all()
                features=torch.tensor(x);changed=features.clone();changed[:,95]=.04-changed[:,95]
                im=torch.tensor(images).permute(0,3,1,2).float()/255.-.5
                for key,model in models.items():
                    with torch.no_grad():
                        original=model(im,features,mask_image=key.endswith('masked')).numpy()*np.array(OUTPUT_SCALES)
                        flipped=model(im,changed,mask_image=key.endswith('masked')).numpy()*np.array(OUTPUT_SCALES)
                    records[key].append(np.concatenate([original,flipped,truth],1))
                items.extend([dict(domain=source['domain'],collection=source['path'],chunk=c['path'],chunk_sha256=sha,
                    step=int(z['step'][f]),initial_row=int(row)) for f in frame_ids for row in rows[selected]])
        stride_audit.append(dict(collection=source['path'],sampled_frames=len(all_steps),command_steps=command_steps,
            samples_exactly_at_command_switch=sum(t%command_steps==0 for t in all_steps)))
    arrays={k:np.concatenate(v) for k,v in records.items()};np.savez_compressed(args.output/'predictions.npz',**arrays)
    summary={}
    for key,a in arrays.items():
        assert tensor_digest(models[key].state_dict())==before[key]
        summary[key]={}
        for domain in ['teacher','ownstate']:
            mask=np.array([i['domain']==domain for i in items]);z=a[mask];delta=z[:,7:14]-z[:,:7]
            summary[key][domain]=dict(samples=len(z),original_rmse=np.sqrt(((z[:,:7]-z[:,14:])**2).mean(0)).tolist(),
                flipped_rmse=np.sqrt(((z[:,7:14]-z[:,14:])**2).mean(0)).tolist(),
                state_change_rms=np.sqrt((delta**2).mean(0)).tolist(),
                slider_abs_change_quantiles_m=np.quantile(np.abs(delta[:,6]),[.5,.9,.95,.99,1]).tolist(),
                translation_change_norm_quantiles_m=np.quantile(np.linalg.norm(delta[:,:3],axis=1),[.5,.95,1]).tolist(),
                rotation_vector_change_norm_quantiles_rad=np.quantile(np.linalg.norm(delta[:,3:6],axis=1),[.5,.95,1]).tolist())
    atomic_json(args.output/'result.json',dict(status='completed',finished=now(),models=model_hashes,summary=summary,
        sampled_items=items,collection_stride_audit=stride_audit,all_models_unchanged=True,physics_transitions=0,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope=__doc__))
    print(json.dumps(summary))


if __name__=='__main__':main()
