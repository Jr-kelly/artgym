"""Evaluate a frozen estimator on new training-family perturbations."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import torch
from scripts.train_g2_support_estimator import SupportEstimator,metrics


def onset_metrics(pred,label,groups,times):
    predicted=pred[:,7].cpu().numpy();actual=label[:,7].cpu().numpy();errors=[];misses=0;false_alarms=0;no_loss=0;events=0;initially_absent=0
    def first_loss(values):
        below=values<.5
        hits=np.flatnonzero(below[:-2]&below[1:-1]&below[2:])
        return int(hits[0]) if len(hits) else None
    for group in sorted(set(groups.tolist())):
        ids=np.flatnonzero(groups==group);ids=ids[np.argsort(times[ids])]
        if actual[ids[0]]<.5:initially_absent+=1;continue
        truth=first_loss(actual[ids]);estimate=first_loss(predicted[ids])
        if truth is None:
            no_loss+=1;false_alarms+=int(estimate is not None)
        else:
            events+=1
            if estimate is None:misses+=1
            else:errors.append(float(times[ids[estimate]]-times[ids[truth]]))
    return dict(actual_contact_loss_events=events,missed_events=misses,paired_estimate_delay_s=errors,median_delay_s=float(np.median(errors)) if errors else None,never_lost_contact_groups=no_loss,false_alarm_groups=false_alarms,initially_absent_contact_groups=initially_absent,scope='Fixed0.5proxythreshold,three consecutive samples; excludes initiallyabsent only fromonset timing, not all-sample metrics. Signed delay includesearlyfalsealarms; no calibratedpair-force claim.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--checkpoints',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;data=np.load(a.data);x=torch.tensor(data['features'],device='cuda');y=torch.tensor(data['labels'],device='cuda');groups=data['groups'];rows=[]
    for path in a.checkpoints:
        saved=torch.load(path,map_location='cuda');model=SupportEstimator(saved['input_dim']).cuda();model.load_state_dict(saved['model']);model.eval()
        with torch.no_grad():pred=model(((x[:,:saved['input_dim']]-saved['input_mean'])/saved['input_std']).clamp(-20,20))
        masks={'all_fresh_perturbations':np.ones(len(groups),bool),'assets_used_for_estimator_fitting':np.isin(groups,saved['train_groups']),'assets_reserved_from_estimator_fitting':np.isin(groups,saved['validation_groups'])}
        rows.append(dict(checkpoint=str(path),checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),input_dim=saved['input_dim'],metrics={k:metrics(pred[m],y[m]) for k,m in masks.items()},contact_loss_onsets=onset_metrics(pred,y,groups,data['times'])))
    report=dict(data=str(a.data),data_sha256=hashlib.sha256(a.data.read_bytes()).hexdigest(),rows=rows,scope='Frozen estimator on fresh512 training-family chains; no estimator updates or sample filtering. All are RL-training assets, not final independent policy validation.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
