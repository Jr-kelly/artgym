"""Independent trace rescore and per-source Wilson intervals for frozen batches."""
import argparse,json,math,csv,hashlib
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_multigrasp_trace import summarize
from scripts.summarize_wuji_hold_stages import stages,grouped

def wilson(k,n):
 z=1.95996398454;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [c-r,c+r]
def main():
 p=argparse.ArgumentParser();p.add_argument('--directories',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sources',type=int,nargs='+',default=[0,1,2,3]);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[];trials=[];temporal=[];endpoints=[]
 for directory in a.directories:
  for item in json.loads((directory/'results.json').read_text()):
   model=item['model'];report=item['report'];dest=directory/model
   with np.load(dest/'trace.npz') as z:t={k:z[k] for k in z.files}
   n=t['active'].shape[1]//len(a.sources);assert n*len(a.sources)==t['active'].shape[1]
   rescored=score_timed_trace(t,report['protocol']['stage_steps'],9,600);assert rescored['records']==report['records']
   for index,source in enumerate(a.sources):
    ids=slice(index*n,(index+1)*n);sub={k:v[:,ids] for k,v in t.items()};r=score_timed_trace(sub,report['protocol']['stage_steps'],9,600)
    independent=summarize(sub,report['protocol']['stage_steps'])
    assert [x['strict'] for x in independent]==[x['stable_full_all_endpoints'] for x in r['records']]
    temporal.extend(dict(model=model,source=source,seconds=report['protocol']['stage_seconds'],**x) for x in independent)
    endpoints.extend(dict(model=model,source=source,seconds=report['protocol']['stage_seconds'],**x) for x in grouped(stages(sub,report['protocol']['stage_steps'])))
    valid=sub['active']&~sub['fall']&~sub['invalid'];body=valid.all(0)&(sub['drift']<.01).all(0)&(sub['rotation']<.25).all(0)
    success=r['stable_full_all_endpoints'];row=dict(model=model,source=source,seconds=report['protocol']['stage_seconds'],n=n,success=success,rate=success/n,wilson95=wilson(success,n),body_stable=int(body.sum()),body_rate=float(body.mean()),alive=r['alive_full'],trace_sha256=hashlib.sha256((dest/'trace.npz').read_bytes()).hexdigest());rows.append(row)
    for i,record in enumerate(r['records']):trials.append(dict(model=model,source=source,seconds=row['seconds'],trial=i,strict=record['stable_full_all_endpoints'],body_stable=bool(body[i]),alive=record['alive_full']))
 (a.output/'temporal.json').write_text(json.dumps(temporal,indent=2)+'\n')
 (a.output/'endpoints.json').write_text(json.dumps(endpoints,indent=2)+'\n')
 (a.output/'report.json').write_text(json.dumps(dict(rows=rows,independent_rescore='passed',scope='Simulation, trained base neighbourhoods; source0/1/2 are three records in two near-duplicate clusters; no unseen-base/hardware claim'),indent=2)+'\n')
 with (a.output/'trials.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
 print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
