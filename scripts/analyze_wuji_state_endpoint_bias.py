"""Describe estimator bias at commanded endpoints without changing success criteria."""
import argparse
import datetime
import json
from pathlib import Path
import numpy as np


def summarize(folder):
    report=json.loads((folder/'report.json').read_text())
    assert report['num_envs']==332 and report['recorded_steps']==600
    with np.load(folder/'trace.npz') as z:
        slider=z['slider'];goal=z['goal'];alive=z['active']
    with np.load(folder/'estimation-trace.npz') as z:
        bias=(z['prediction'][:,:,6]-z['target'][:,:,6])*.0005
        active=z['active']
    period=report['protocol']['stage_steps'];rows=[]
    for group,start in enumerate([0,100,200]):
        for parity in [0,1]:
            actuals=[];biases=[];held=[]
            for stage,end in enumerate(range(period,601,period)):
                if stage%2!=parity:continue
                lo=end-9;hi=end
                valid=(active[lo:hi,start:start+100]&alive[lo:hi,start:start+100]).all(0)
                actuals.extend(np.mean(slider[lo:hi,start:start+100]-goal[lo:hi,start:start+100],axis=0)[valid].tolist())
                biases.extend(np.mean(bias[lo:hi,start:start+100],axis=0)[valid].tolist())
                held.extend([report['records'][start+i]['endpoints_held'][stage] for i in np.flatnonzero(valid)])
            x=np.asarray(actuals);y=np.asarray(biases)
            corr=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and x.std()>0 and y.std()>0 else None
            rows.append(dict(training_grasp=group,command='open' if parity==0 else 'close',active_endpoint_windows=len(x),
                held_endpoint_windows=sum(held),actual_signed_error_quantiles_mm=(1000*np.quantile(x,[.05,.5,.95])).tolist(),
                estimate_signed_error_quantiles_mm=(1000*np.quantile(y,[.05,.5,.95])).tolist(),
                correlation=corr,opposite_sign_fraction=float(np.mean(x*y<0))))
    return dict(folder=str(folder),seconds=report['protocol']['stage_seconds'],joint=report['stable_full_all_endpoints'],rows=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folders',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    results=[summarize(folder) for folder in args.folders]
    out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),results=results,
        scope='Descriptive endpoint-window correlation on reused development trajectories, not a causal estimate. Both residuals contain the same actual slider value with opposite signs, so their correlation has algebraic coupling and does not identify causal direction. Estimation trace is pre-action and physical trace post-action; only final9steps of stages used, active throughout. Windows and grasps are dependent observations. No policy changes or revised scoring.')
    args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(results))


if __name__=='__main__':
    main()
