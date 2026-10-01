"""Stagewise development evidence; episode samples remain the statistical unit."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from scripts.analyze_wuji_student import analyze

def main():
 p=argparse.ArgumentParser();p.add_argument('--models',nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 root=Path('runs/unified-student-20261001');a.output.mkdir(parents=True,exist_ok=True)
 rows=[];trials=[];stages=[];missing=[]
 for name in a.models:
  for protocol in ['S2','S5','F']:
   d=root/(name+'-development')/(name+'-'+protocol)
   if not (d/'trace.npz').exists() or not (d/'report.json').exists():missing.append(str(d));continue
   rr,tt=analyze(d,name);rows+=rr;trials+=tt
   if protocol=='F':continue
   for source in range(4):
    group=[t for t in tt if t['source']==source];holds=np.array([[v=='1' for v in t['endpoint_holds']] for t in group]);breach=np.array([t['first_body_breach_sec'] for t in group])
    stages.append(dict(model=name,protocol=protocol,source=source,n=len(group),stage_hold_counts=holds.sum(0).tolist(),opening_stage_counts=holds[:,::2].sum(0).tolist(),closing_stage_counts=holds[:,1::2].sum(0).tolist(),first_body_breach_median_sec=float(np.median(breach)),body_survived_horizon=int((breach==20).sum()),note='Stages from same episode are correlated; counts are descriptive, not independent trials'))
 result=dict(rows=rows,stages=stages,missing=missing,independent_rescore=True)
 (a.output/'report.json').write_text(json.dumps(result,indent=2))
 if trials:
  with (a.output/'trials.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
 print(json.dumps(dict(cells=len(rows),trials=len(trials),missing=missing)))
if __name__=='__main__':main()
