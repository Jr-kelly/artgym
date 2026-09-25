"""Matched fixed-data state fitting: two-clock teacher vs teacher plus own trajectories.

One finite dataset-aggregation round. Frozen student data includes its mistakes.
Both arms retain the same initial encoder, optimizer, update and sample budgets;
validation rows never enter gradients. Offline losses are not task success.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from scripts import wuji_goal_common
import numpy as np
import torch
from scripts.wuji_physical_state_encoder import make_encoder, SCALES
from scripts.audit_distillation_runtime import tensor_digest
from scripts.monitor_wuji_checkpoints import atomic_json, now


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--initial',type=Path,required=True)
    p.add_argument('--teacher-data',type=Path,nargs=2,required=True)
    p.add_argument('--student-data',type=Path,nargs=2,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--updates',type=int,default=1000)
    args=p.parse_args()
    assert not args.output.exists() and args.updates>0
    args.output.mkdir(parents=True)
    torch.set_num_threads(4)
    device=torch.device('cuda:0')
    initial_sha=digest(args.initial)
    assert initial_sha==json.loads(args.initial.with_suffix('.json').read_text())['sha256']
    artifact=torch.load(args.initial,map_location='cpu')
    assert artifact['phase']=='offline_teacher_fit' and artifact['update']==1000
    assert np.allclose(artifact['output_scales'],SCALES,rtol=1e-6,atol=1e-10)
    data={};manifests={};rows_reference=None
    scales=torch.tensor(SCALES,device=device)
    for kind,paths in [('teacher',args.teacher_data),('student',args.student_data)]:
        for seconds,path in zip([2,5],paths):
            manifest=json.loads(path.with_name('dataset-manifest.json').read_text())
            assert digest(path)==manifest['dataset_sha256'] and manifest['status']=='passed'
            assert manifest['source_teacher_sha256']==artifact['teacher_sha256']
            report=json.loads(path.with_name('report.json').read_text())
            assert report['protocol']['stage_seconds']==seconds
            if kind=='student':
                assert manifest['student_sha256']==initial_sha and not manifest['current_privileged_actor_input']
                assert manifest['encoder_unchanged'] and manifest['teacher_unchanged']
            with np.load(path) as z:
                histories,labels,active=z['history'],z['target'],z['active']
                rows,train=z['initial_rows'],z['train_rows']
                assert np.array_equal(train,rows%100<20)
                assert np.array_equal(z['step'],np.arange(0,600,4))
            assert histories.shape==(150,90,2055) and labels.shape==(150,90,8)
            if rows_reference is not None:assert np.array_equal(rows,rows_reference)
            rows_reference=rows
            key=f'{kind}{seconds}'
            groups=np.broadcast_to((rows//100)[None,:],active.shape)
            data[key]={}
            for split,selected in [('train',active & train[None,:]),('validation',active & ~train[None,:])]:
                x=torch.from_numpy(histories[selected].copy()).to(device)
                y=torch.from_numpy(labels[selected].copy()).to(device)/scales
                assert torch.isfinite(x).all() and torch.isfinite(y).all() and len(x)>4000
                data[key][split]=(x,y,torch.from_numpy(groups[selected].copy()).to(device))
            manifests[key]=dict(path=str(path),sha256=digest(path),
                train_count=len(data[key]['train'][0]),validation_count=len(data[key]['validation'][0]),
                initial_rows=rows.tolist())
    first,spec=make_encoder(artifact['encoder_spec']);first.load_state_dict(artifact['state_encoder'])
    first.to(device).eval()
    nets={'teacher_only':first,'aggregated':copy.deepcopy(first)}
    initial_tensor=tensor_digest(first.state_dict())
    assert initial_tensor==tensor_digest(nets['aggregated'].state_dict())
    optimizers={k:torch.optim.Adam(net.parameters(),lr=2e-5) for k,net in nets.items()}
    rng=torch.Generator(device='cpu').manual_seed(20261074)
    state=dict(status='running',started=now(),scope=__doc__,initial_sha256=initial_sha,
        initial_tensor_sha256=initial_tensor,datasets=manifests,updates_budget=args.updates,
        updates_completed=0,batch_size=512,lr=2e-5,grad_clip=1.,seed=20261074,
        sampling='128 teacher2 +128 teacher5 shared first half; second half independent 128+128 teacher or student draws; replacement; private CPU RNG.',
        supervised_counts={k:0 for k in nets},same_initial_tensors=True,validation_excluded=True)
    atomic_json(args.output/'status.json',state)
    validations=[]
    def evaluate(update):
        for arm,net in nets.items():
            with torch.no_grad():
                for key,entry in data.items():
                    x,y,g=entry['validation'];errors=[]
                    for start in range(0,len(x),512):errors.append((net(x[start:start+512])-y[start:start+512])*scales)
                    error=torch.cat(errors)
                    assert torch.isfinite(error).all()
                    validations.append(dict(update=update,arm=arm,data=key,
                        rmse=error.square().mean(0).sqrt().cpu().tolist(),
                        per_grasp_rmse=[error[g==i].square().mean(0).sqrt().cpu().tolist() for i in [0,1,2]]))
        atomic_json(args.output/'validation.json',validations)
    def save(update):
        for arm,net in nets.items():
            path=args.output/f'{arm}-update{update:04d}.pth'
            assert not path.exists()
            provenance=dict(scope=__doc__,arm=arm,initial_sha256=initial_sha,datasets=manifests,
                optimizer_updates=update,supervised_samples=512*update,seed=20261074,
                teacher_physics_transitions=398400,student_physics_transitions=398400,
                shared_collection_budget=True,validation_excluded=True)
            payload=dict(artifact)
            payload.update(state_encoder=net.state_dict(),encoder_spec=spec,optimizer=optimizers[arm].state_dict(),
                update=update,phase='offline_teacher_fit',fitting_provenance=provenance)
            torch.save(payload,path)
            atomic_json(path.with_suffix('.json'),dict(sha256=digest(path),created=now(),fitting_provenance=provenance))
    try:
        evaluate(0);save(0)
        for update in range(1,args.updates+1):
            # Draw every stream irrespective of arm. Both models see exactly
            # the same first 256 teacher examples and consume 512 total.
            samples={}
            for name,key in [('first2','teacher2'),('first5','teacher5'),('teacher2','teacher2'),
                             ('teacher5','teacher5'),('student2','student2'),('student5','student5')]:
                x,y,_=data[key]['train']
                ix=torch.randint(len(x),(128,),generator=rng).to(device)
                samples[name]=(x[ix],y[ix])
            metrics={}
            for arm,net in nets.items():
                suffix='teacher' if arm=='teacher_only' else 'student'
                keys=['first2','first5',suffix+'2',suffix+'5']
                x=torch.cat([samples[k][0] for k in keys]);y=torch.cat([samples[k][1] for k in keys])
                assert x.shape==(512,2055) and y.shape==(512,8)
                optimizer=optimizers[arm];optimizer.zero_grad(set_to_none=True)
                prediction=net(x)
                loss=torch.nn.functional.smooth_l1_loss(prediction,y)
                assert torch.isfinite(loss)
                loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(net.parameters(),1.,error_if_nonfinite=True)
                optimizer.step()
                assert all(torch.isfinite(v).all() for v in net.state_dict().values())
                state['supervised_counts'][arm]+=512
                metrics[arm]=dict(loss=float(loss.detach()),grad_norm=float(norm))
            if update in [1,100,250,500,args.updates]:
                evaluate(update);save(update)
                assert all(tensor_digest(net.state_dict())!=initial_tensor for net in nets.values())
            if update%10==0 or update==1:
                state.update(updates_completed=update,latest=metrics,heartbeat=now())
                atomic_json(args.output/'status.json',state)
                print(json.dumps(dict(update=update,metrics=metrics)),flush=True)
        assert all(v==args.updates*512 for v in state['supervised_counts'].values())
        state.update(status='completed',finished=now(),updates_completed=args.updates,no_task_success_claim=True,
            final_tensor_sha256={k:tensor_digest(net.state_dict()) for k,net in nets.items()})
        atomic_json(args.output/'status.json',state)
    except BaseException as error:
        state.update(status='failed',finished=now(),error=repr(error));atomic_json(args.output/'status.json',state)
        raise


if __name__=='__main__':main()
