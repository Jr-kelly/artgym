"""Independent per-source F/S checks, phase outcomes and trajectory failure times."""
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_multigrasp_trace import summarize
from scripts.summarize_wuji_unified import wilson

def analyze(directory):
    rows=[];trials=[]
    for item in json.loads((directory/'results.json').read_text()):
        dest=directory/item['directory'];report=item['report'];protocol=item['protocol'];model=item['model']
        with np.load(dest/'trace.npz') as z:t={k:z[k] for k in z.files}
        T,N=t['active'].shape;assert N%4==0;n=N//4
        valid=t['active'].astype(bool)&~t['fall'].astype(bool)&~t['invalid'].astype(bool)
        body=valid.all(0)&(t['drift']<.01).all(0)&(t['rotation']<.25).all(0)
        error=np.abs(t['slider']-t['goal'])
        if protocol.startswith('S'):
            assert T==600
            period=report['protocol']['stage_steps']
            score=score_timed_trace(t,period,9,600);ind=summarize(t,period)
            assert score['records']==report['records']
            success=np.array([r['strict'] for r in ind]);assert success.tolist()==[r['stable_full_all_endpoints'] for r in score['records']]
            holds=np.array([r['endpoints_held'] for r in score['records']]);attained=np.array([r['stages_attained'] for r in score['records']])
        else:
            assert T==1200
            # Reconstruct hold-triggered state machine from pre-switch physical goals.
            streak=np.zeros(N,dtype=int);cycles=np.zeros(N,dtype=int);phase=np.zeros(N,dtype=int)
            init=t['goal'][0]-.04
            for k in range(T):
                expected=init+np.where(phase==0,.04,0)
                assert np.allclose(t['goal'][k][valid[k]],expected[valid[k]],atol=1e-6)
                streak=np.where(valid[k]&(error[k]<.01),streak+1,0)
                ready=streak>=45;cycles+=ready&(phase==1);phase[ready]=1-phase[ready];streak[ready]=0
            assert cycles.tolist()==[r['cycles'] for r in report['records']]
            success=cycles>=1
        for s in range(4):
            sl=slice(s*n,(s+1)*n);k=int(success[sl].sum());active=t['active'][:,sl].astype(bool)
            breach=~valid[:,sl]|(t['drift'][:,sl]>=.01)|(t['rotation'][:,sl]>=.25)
            first=np.where(breach.any(0),breach.argmax(0)/30,T/30)
            row=dict(model=model,protocol=protocol,source=s,n=n,success=k,rate=k/n,wilson95=wilson(k,n),body_stable=int(body[sl].sum()),body_rate=float(body[sl].mean()),alive=int(valid[:,sl].all(0).sum()),phase_error_mean_m=float(error[:,sl][active].mean()),phase_error_max_m=float(error[:,sl][active].max()),body_first_breach_mean_sec=float(first.mean()),action_saturation=float((abs(t['action'][:,sl][active])>=.999999).mean()),max_drift_m=float(t['drift'][:,sl][active].max()),max_rotation_rad=float(t['rotation'][:,sl][active].max()),trace_sha256=hashlib.sha256((dest/'trace.npz').read_bytes()).hexdigest())
            if protocol.startswith('S'):
                row.update(phase_hold_rate=float(holds[sl].mean()),open_hold_rate=float(holds[sl,::2].mean()),close_hold_rate=float(holds[sl,1::2].mean()),phase_arrival_rate=float(attained[sl].mean()),open_arrival_rate=float(attained[sl,::2].mean()),close_arrival_rate=float(attained[sl,1::2].mean()))
            else:row.update(cycles_mean=float(cycles[sl].mean()),cycles_max=int(cycles[sl].max()))
            rows.append(row)
            for i in range(n):trials.append(dict(model=model,protocol=protocol,source=s,trial=i,success=bool(success[s*n+i]),body_stable=bool(body[s*n+i]),alive=bool(valid[:,s*n+i].all()),first_body_breach_sec=float(first[i])))
    return rows,trials

def main():
    p=argparse.ArgumentParser();p.add_argument('--directories',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    rows=[];trials=[]
    for d in a.directories:r,t=analyze(d);rows+=r;trials+=t
    (a.output/'report.json').write_text(json.dumps(dict(rows=rows,independent_rescore='passed'),indent=2)+'\n')
    with (a.output/'trials.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
    for r in rows:print(json.dumps({k:r[k] for k in ['model','protocol','source','success','n','body_stable']+(['phase_hold_rate'] if 'phase_hold_rate' in r else ['cycles_mean'])}))
if __name__=='__main__':main()
