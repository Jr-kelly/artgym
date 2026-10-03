"""Bounded support/progress supervision from measured inputs; asset-group split.

These are development labels from the RL training family, not independent
policy validation or a new sensor. Simulator contact remains a proxy label.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from torch import nn


class SupportEstimator(nn.Module):
    def __init__(self,dimension=150):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(dimension,128),nn.ELU(),nn.Linear(128,64),nn.ELU(),nn.Linear(64,8))

    def forward(self,x):
        raw=self.net(x)
        return torch.cat([raw[:,:7],raw[:,7:].sigmoid()],-1)


def metrics(pred,label):
    error=(pred-label).abs()
    contact=label[:,7]>.5;stable=label[:,1:4].norm(dim=-1)<1
    def progress(mask):
        return float(error[mask,0].mean()*40) if bool(mask.any()) else None
    return dict(progress_mae_mm=float(error[:,0].mean()*40),progress_p95_mm=float(torch.quantile(error[:,0]*40,.95)),position_component_mae_mm=(error[:,1:4].mean(0)*10).tolist(),rotation_component_mae_rad=(error[:,4:7].mean(0)*.25).tolist(),contact_proxy_mae=float(error[:,7].mean()),contact_proxy_classification_accuracy=float(((pred[:,7]>.5)==contact).float().mean()),contact_positive_count=int(contact.sum()),progress_mae_contact_mm=progress(contact),progress_mae_no_contact_mm=progress(~contact),progress_mae_stable_body_mm=progress(stable),progress_mae_deviated_body_mm=progress(~stable),n=len(label),scope='Bounded/clipped simulator support labels and proximity proxy; not calibrated real force')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--epochs',type=int,default=80);p.add_argument('--batch',type=int,default=2048);p.add_argument('--seed',type=int,default=2026100372);p.add_argument('--measured-only',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed);torch.backends.cuda.matmul.allow_tf32=False
    data_hash=hashlib.sha256(a.data.read_bytes()).hexdigest();raw=np.load(a.data);features=raw['features'];labels=raw['labels'];groups=raw['groups'];assert features.shape[1]==150 and labels.shape[1]==8
    # Never split adjacent frames of the same physical asset between partitions.
    validation=groups%5==0;assert validation.any() and (~validation).any();train_groups=sorted(set(groups[~validation].tolist()));validation_groups=sorted(set(groups[validation].tolist()));assert not set(train_groups)&set(validation_groups)
    dimension=134 if a.measured_only else 150;device='cuda';x=torch.tensor(features[:,:dimension],device=device);y=torch.tensor(labels,device=device);train=torch.tensor(np.flatnonzero(~validation),device=device);valid=torch.tensor(np.flatnonzero(validation),device=device)
    mean=x[train].mean(0);std=x[train].std(0).clamp_min(.02);x=((x-mean)/std).clamp(-20,20);model=SupportEstimator(dimension).to(device);opt=torch.optim.Adam(model.parameters(),lr=3e-4);begin=time.monotonic();best=float('inf');best_epoch=0
    for epoch in range(1,a.epochs+1):
        model.train();losses=[]
        for ids in train[torch.randperm(len(train),device=device)].split(a.batch):
            pred=model(x[ids]);loss=nn.functional.smooth_l1_loss(pred[:,:7],y[ids,:7])+nn.functional.binary_cross_entropy(pred[:,7].clamp(1e-6,1-1e-6),y[ids,7])*.25
            opt.zero_grad(set_to_none=True);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);opt.step();losses.append(float(loss))
        model.eval()
        with torch.no_grad():
            pred=model(x[valid]);v=float(nn.functional.smooth_l1_loss(pred[:,:7],y[valid,:7])+nn.functional.binary_cross_entropy(pred[:,7].clamp(1e-6,1-1e-6),y[valid,7])*.25)
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)),group_validation_loss=v,wall_seconds=time.monotonic()-begin)
        with (a.output/'learning.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        if v<best:
            best=v;best_epoch=epoch;payload=dict(format='g2-legal-support-estimator-v1',model=model.state_dict(),optimizer=opt.state_dict(),input_mean=mean,input_std=std,input_dim=dimension,epoch=epoch,rng_cpu=torch.get_rng_state(),rng_cuda=torch.cuda.get_rng_state_all(),rng_numpy=np.random.get_state(),args=vars(a),train_groups=train_groups,validation_groups=validation_groups,label_scales=dict(progress_m=.04,position_m=.01,rotation_rad=.25),data_sha256=data_hash,scope='Training-family estimator development; no independent policy validation. Legal134 measured/known channels'+(' plus frozen16D SC encoding from same2076 packet' if dimension==150 else ''))
            torch.save(payload,a.output/'best.pth')
        if epoch==1 or epoch%10==0:print(json.dumps(row),flush=True)
    saved=torch.load(a.output/'best.pth',map_location=device);model.load_state_dict(saved['model'])
    with torch.no_grad():pred=model(x[valid]);fit=model(x[train]);constant=y[train].mean(0)[None].expand(len(valid),-1);goal_baseline=constant.clone();goal_baseline[:,0]=torch.tensor(features[validation,95]/.04,device=device)
    report=dict(args=vars(a),best_epoch=best_epoch,train_groups=train_groups,validation_groups=validation_groups,train_metrics=metrics(fit,y[train]),validation_metrics=metrics(pred,y[valid]),constant_training_mean_baseline=metrics(constant,y[valid]),instant_known_goal_baseline=metrics(goal_baseline,y[valid]),checkpoint_sha256=hashlib.sha256((a.output/'best.pth').read_bytes()).hexdigest(),data_sha256=saved['data_sha256'],scope=saved['scope'],wall_seconds=time.monotonic()-begin)
    np.savez_compressed(a.output/'validation-predictions.npz',indices=valid.cpu().numpy(),predictions=pred.cpu().numpy(),labels=y[valid].cpu().numpy(),groups=groups[validation],times=raw['times'][validation]);(a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps(report,default=str),flush=True)


if __name__=='__main__':main()
