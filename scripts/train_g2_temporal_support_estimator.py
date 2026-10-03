"""Train bounded support estimates from the same real 50x40 command history.

Asset-group separation is development validation; current truth is label-only.
The head is neither a sensor nor a calibrated force/contact controller.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from scripts.train_g2_support_estimator import metrics


class TemporalSupportEstimator(nn.Module):
    def __init__(self):
        super().__init__()
        self.history=nn.Sequential(nn.Conv1d(40,32,5,stride=2),nn.ELU(),nn.Conv1d(32,32,5,stride=2),nn.ELU(),nn.Flatten())
        self.net=nn.Sequential(nn.Linear(454,128),nn.ELU(),nn.Linear(128,64),nn.ELU(),nn.Linear(64,8))

    def forward(self,public,history):
        raw=self.net(torch.cat([public,self.history(history.transpose(1,2))],-1))
        return torch.cat([raw[:,:7],raw[:,7:].sigmoid()],-1)


def normalized_inputs(raw,device,mean=None,std=None,history_mean=None,history_std=None,train=None):
    features=raw['features'];assert features.shape[1]==150
    public=torch.tensor(features[:,:134],device=device)
    history=torch.tensor(raw['packets'][:,:2000].reshape(-1,50,40),device=device)
    if mean is None:
        mean=public[train].mean(0);std=public[train].std(0).clamp_min(.02)
        history_mean=history[train].mean((0,1));history_std=history[train].flatten(0,1).std(0).clamp_min(.02)
    return ((public-mean)/std).clamp(-20,20),((history-history_mean)/history_std).clamp(-20,20),mean,std,history_mean,history_std


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--fresh-data',type=Path);p.add_argument('--epochs',type=int,default=80);p.add_argument('--batch',type=int,default=2048);p.add_argument('--seed',type=int,default=2026100388);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    raw=np.load(a.data);groups=raw['groups'];validation=groups%5==0
    train_groups=sorted(set(groups[~validation].tolist()));validation_groups=sorted(set(groups[validation].tolist()));assert not set(train_groups)&set(validation_groups)
    device='cuda';train=torch.tensor(np.flatnonzero(~validation),device=device);valid=torch.tensor(np.flatnonzero(validation),device=device)
    x,h,mean,std,hmean,hstd=normalized_inputs(raw,device,train=train);y=torch.tensor(raw['labels'],device=device);assert y.shape[1]==8
    model=TemporalSupportEstimator().to(device);opt=torch.optim.Adam(model.parameters(),lr=3e-4);begin=time.monotonic();best=float('inf');best_epoch=0
    def loss_fn(pred,truth):return nn.functional.smooth_l1_loss(pred[:,:7],truth[:,:7])+.25*nn.functional.binary_cross_entropy(pred[:,7].clamp(1e-6,1-1e-6),truth[:,7])
    for epoch in range(1,a.epochs+1):
        model.train();losses=[]
        for ids in train[torch.randperm(len(train),device=device)].split(a.batch):
            pred=model(x[ids],h[ids]);loss=loss_fn(pred,y[ids]);opt.zero_grad(set_to_none=True);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5.);opt.step();losses.append(float(loss))
        model.eval()
        with torch.no_grad():v=float(loss_fn(model(x[valid],h[valid]),y[valid]))
        row=dict(epoch=epoch,train_loss=float(np.mean(losses)),group_validation_loss=v,wall_seconds=time.monotonic()-begin)
        with (a.output/'learning.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        if v<best:
            best=v;best_epoch=epoch;saved=dict(format='g2-legal-temporal-support-estimator-v1',model=model.state_dict(),optimizer=opt.state_dict(),input_mean=mean,input_std=std,history_mean=hmean,history_std=hstd,input_dim=134,epoch=epoch,rng_cpu=torch.get_rng_state(),rng_cuda=torch.cuda.get_rng_state_all(),rng_numpy=np.random.get_state(),args=vars(a),train_groups=train_groups,validation_groups=validation_groups,label_scales=dict(progress_m=.04,position_m=.01,rotation_rad=.25),data_sha256=hashlib.sha256(a.data.read_bytes()).hexdigest(),scope='134measured/knownpublic+first2000ofsamelegal2076real50x40history; simulatortruthlabelonly, no asset/material/loadID inputs. Assetgroupsplit isdevelopment, notindependentpolicyvalidation.')
            torch.save(saved,a.output/'best.pth')
        if epoch==1 or epoch%10==0:print(json.dumps(row),flush=True)
    saved=torch.load(a.output/'best.pth',map_location=device);model.load_state_dict(saved['model'])
    with torch.no_grad():pred=model(x[valid],h[valid]);fit=model(x[train],h[train]);constant=y[train].mean(0)[None].expand(len(valid),-1)
    report=dict(args=vars(a),best_epoch=best_epoch,train_groups=train_groups,validation_groups=validation_groups,train_metrics=metrics(fit,y[train]),validation_metrics=metrics(pred,y[valid]),constant_training_mean_baseline=metrics(constant,y[valid]),checkpoint_sha256=hashlib.sha256((a.output/'best.pth').read_bytes()).hexdigest(),data_sha256=saved['data_sha256'],scope=saved['scope'],wall_seconds=time.monotonic()-begin)
    np.savez_compressed(a.output/'validation-predictions.npz',indices=valid.cpu().numpy(),predictions=pred.cpu().numpy(),labels=y[valid].cpu().numpy(),groups=groups[validation],times=raw['times'][validation])
    if a.fresh_data:
        fresh=np.load(a.fresh_data);fx,fh,*_=normalized_inputs(fresh,device,mean,std,hmean,hstd);fy=torch.tensor(fresh['labels'],device=device)
        with torch.no_grad():fp=torch.cat([model(fx[ids],fh[ids]) for ids in torch.arange(len(fy),device=device).split(a.batch)])
        dev=torch.tensor(fresh['groups']%5==0,device=device)
        report['fresh_all_metrics']=metrics(fp,fy);report['fresh_group_validation_metrics']=metrics(fp[dev],fy[dev]);report['fresh_data_sha256']=hashlib.sha256(a.fresh_data.read_bytes()).hexdigest()
        np.savez_compressed(a.output/'fresh-predictions.npz',predictions=fp.cpu().numpy(),labels=fresh['labels'],groups=fresh['groups'],times=fresh['times'])
    (a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps(report,default=str),flush=True)


if __name__=='__main__':main()
