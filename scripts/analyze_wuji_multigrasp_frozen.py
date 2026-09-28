"""Rescore every frozen physical trace and report per-base-grasp factorial contrasts."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.wuji_arrival_metrics import score_arrival_trace
from scripts.summarize_wuji_multigrasp_trace import summarize
R=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--cohort-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 run=json.loads(a.results.read_text());assert run['status']=='completed'
 cohort=json.loads(a.cohort_manifest.read_text());assert sha(a.cohort_manifest)==run['plan']['mapping_sha256'];mapping=cohort['rows']
 a.output.mkdir(parents=True,exist_ok=False);trials=[];grouped=[];static=None;temporal=[]
 for result in run['results']:
  path=R/result['evidence'];saved=result['report'];protocol=result['protocol']
  # Materialize once: each NpzFile access otherwise decompresses the complete
  # array again inside the per-grasp temporal analysis.
  with np.load(path/'trace.npz') as archive:trace={key:archive[key] for key in archive.files}
  assert saved['initial_states_sha256']==cohort['states_sha256'] and len(mapping)==trace['active'].shape[1]
  physical=(trace['active']&~trace['fall']&~trace['invalid']).all(0)
  body=physical&(trace['drift']<.01).all(0)&(trace['rotation']<.25).all(0)
  if protocol=='static':static=dict(alive=physical,body_stable=body);continue
  assert static is not None,'Static baseline must precede policies'
  if protocol=='arrival':
   rescored=score_arrival_trace(trace,600,.01);metric='three_cycles'
  else:
   rescored=score_timed_trace(trace,150 if protocol=='fixed5' else 60,9,600);metric='stable_full_all_endpoints'
   details=summarize(trace,150 if protocol=='fixed5' else 60);trace_sha256=sha(path/'trace.npz')
   for i,detail in enumerate(details):
    assert detail['strict']==rescored['records'][i][metric], 'Independent endpoint calculation disagrees'
    temporal.append(dict(model=result['model'],protocol=protocol,**mapping[i],diagnostics=detail,trace_sha256=trace_sha256))
  for k,v in rescored.items():
   if k=='records':
    for old,new in zip(saved[k],v):
     assert old==new,'Per-trial rescore mismatch'
   else:assert saved[k]==v,(k,saved[k],v)
  for i,record in enumerate(rescored['records']):
   success=record[metric];row=dict(model=result['model'],protocol=protocol,**mapping[i],success=bool(success),alive_full=record['alive_full'],static_alive=bool(static['alive'][i]),static_body_stable=bool(static['body_stable'][i]),max_drift_mm=record['max_drift_m']*1000,max_rotation_deg=np.rad2deg(record['max_rotation_rad']),checkpoint_sha256=saved['checkpoint_sha256'])
   if protocol=='arrival':row['cycles']=record['cycles']
   else:row['cycles']=sum(all(record['endpoints_held'][j:j+2]) for j in range(0,len(record['endpoints_held']),2))
   trials.append(row)
 for model in ['A','B','C','D','reference']:
  for protocol in ['fixed2','fixed5','arrival']:
   for source in sorted({x['source_id'] for x in mapping}):
    rows=[x for x in trials if x['model']==model and x['protocol']==protocol and x['source_id']==source];assert rows
    valid=[x for x in rows if x['static_alive']];stable=[x for x in rows if x['static_body_stable']]
    grouped.append(dict(model=model,protocol=protocol,cohort=rows[0]['cohort'],source_id=source,trial_count=len(rows),successes=sum(x['success'] for x in rows),success_rate=np.mean([x['success'] for x in rows]),alive_full=sum(x['alive_full'] for x in rows),static_alive_count=len(valid),success_on_static_alive=sum(x['success'] for x in valid),static_stable_count=len(stable),success_on_static_stable=sum(x['success'] for x in stable),mean_cycles=np.mean([x['cycles'] for x in rows]),max_drift_mm=max(x['max_drift_mm'] for x in rows),max_rotation_deg=max(x['max_rotation_deg'] for x in rows)))
 contrasts=[]
 for protocol in ['fixed2','fixed5','arrival']:
  for cohort_name in sorted({x['cohort'] for x in mapping}):
   means={m:float(np.mean([x['success_rate'] for x in grouped if x['model']==m and x['protocol']==protocol and x['cohort']==cohort_name])) for m in ['A','B','C','D','reference']}
   contrasts.append(dict(protocol=protocol,cohort=cohort_name,macro_by_base=means,more_minus_small_at04=means['B']-means['A'],more_minus_small_at20=means['D']-means['C'],span20_minus04_small=means['C']-means['A'],span20_minus04_more=means['D']-means['B'],interaction=(means['D']-means['C'])-(means['B']-means['A'])))
 for name,rows in [('trials',trials),('per-grasp',grouped)]:
  with (a.output/(name+'.csv')).open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (a.output/'temporal-diagnostics.json').write_text(json.dumps(temporal,indent=2)+'\n')
 report=dict(status='independently_rescored',checkpoint_selection=run['plan'].get('selection','development'),results_sha256=sha(a.results),cohort_sha256=sha(a.cohort_manifest),training_seeds=1,physical_trial_count=len(trials),base_record_count=len({x['source_id'] for x in mapping}),new_base_count=cohort['new_base_count'],contrasts=contrasts,interpretation='one training seed only; paired empirical differences, no stable causal claim; repetitions are nested within base grasps; original3 include one near-family',scope='arrival success=at least3complete cycles; fixed success=allstrictendpoints+alive+body throughout20s; static failures separately counted, never silently removed; timed temporal diagnostics independently check endpoints and include contact-proxy loss, slider error, target/actual error and body threshold time',artifact_sha256={n:sha(a.output/n) for n in ['trials.csv','per-grasp.csv','temporal-diagnostics.json']})
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
