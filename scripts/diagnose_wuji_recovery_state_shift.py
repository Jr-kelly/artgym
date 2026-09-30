"""Matched-time physical state coverage, without treating off-policy labels as an oracle."""
import argparse,json
from pathlib import Path
import numpy as np

def read(path):
    with np.load(path) as z:
        return {k:z[k] for k in ['q','target','active','fall','invalid','drift','rotation']}

def nearest(reference, query, scale):
    distance=((query[:,None,:]-reference[None,:,:])/scale)**2
    return np.sqrt(distance.mean(-1).min(-1))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evaluations',nargs='+',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    limits=json.loads((root/'runs/artmanip-recovery-20260930/reference-precheck/report.json').read_text())['joint_limits']
    scale=np.array(limits[1])-np.array(limits[0]);rows=[]
    for seconds in [2,5]:
        for source in range(4):
            expert=read(root/f'runs/unified-policy-20260930/train-data-t{seconds}/source{source}/trace.npz')
            active=expert['active']&~expert['fall']&~expert['invalid'];split=int(active.shape[1]*.75)
            candidates=[]
            for directory in a.evaluations:
                for item in json.loads((directory/'results.json').read_text()):
                    if item['protocol']!=f'S{seconds}':continue
                    t=read(directory/item['directory']/'trace.npz');n=t['active'].shape[1]//4
                    t={k:v[:,source*n:(source+1)*n] for k,v in t.items()}
                    candidates.append((item['model'],t))
            candidates.insert(0,('expert_heldout_recorded_history',{k:v[:,split:] for k,v in expert.items()}))
            for feature in ['q','target']:
                metrics={}
                for name,trace in candidates:
                    valid=trace['active']&~trace['fall']&~trace['invalid'];distances=[];by_trial=[[] for _ in range(valid.shape[1])]
                    for step in range(min(len(trace[feature]),600)):
                        ref=expert[feature][step,:split][active[step,:split]]
                        ids=np.flatnonzero(valid[step])
                        if not len(ref) or not len(ids):continue
                        d=nearest(ref,trace[feature][step,ids],scale)
                        distances.extend(d.tolist())
                        for i,value in zip(ids,d):by_trial[i].append(float(value))
                    arr=np.array(distances);assert len(arr)
                    metrics[name]=dict(mean=float(arr.mean()),p95=float(np.quantile(arr,.95)),samples=len(arr),trial_means=[float(np.mean(x)) if x else None for x in by_trial],distances=arr)
                baseline=metrics['expert_heldout_recorded_history']['p95']
                for name,m in metrics.items():
                    distances=m.pop('distances')
                    rows.append(dict(model=name,source=source,seconds=seconds,feature=feature,**m,expert_validation_p95=baseline,fraction_above_expert_validation_p95=float(np.mean(distances>baseline))))
    result=dict(scope='Descriptive physical coverage only. At each control step compare to the96 fitting expert episodes for the same source and clock protocol, using RMS joint error normalized by asset ranges. Heldout32 expert episodes supply a reference distribution. No policy obs/latent labels, causal conclusion or automatic DAgger trigger; surviving steps only, report survival separately.',rows=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for r in rows:
        if r['source']==3:print(json.dumps({k:r[k] for k in ['model','seconds','feature','mean','p95','fraction_above_expert_validation_p95']}))

if __name__=='__main__':main()
