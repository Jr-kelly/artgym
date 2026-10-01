"""Recompute episode scores and geometry/source paired intervals from raw traces."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from scripts.summarize_wuji_unified import wilson
from scripts.summarize_wuji_multigrasp_trace import summarize
def paired_ci(difference,seed=2026100210):
 d=np.asarray(difference,dtype=float)
 if not len(d):return None
 rng=np.random.default_rng(seed);v=d[rng.integers(len(d),size=(4000,len(d)))].mean(1)
 return [float(x) for x in np.quantile(v,[.025,.975])]
def read_run(directory,selection,models):
 report=json.loads((directory/'report.json').read_text());receipt=json.loads((directory/'geometry-receipt.json').read_text());label=receipt['asset']['parameters']['label'];model=receipt['model'];protocol=receipt['protocol'];horizon=1200 if protocol=='F' else 600
 assert receipt['model_unchanged'] and report['checkpoint_sha256']==models['teacher']
 if model=='student':assert report['unified_student_sha256']==models['student']
 with np.load(directory/'trace.npz') as z:t={k:z[k] for k in z.files}
 T,N=t['active'].shape;assert N==len(selection['source_order'])
 valid=t['active']&~t['fall']&~t['invalid'];pose=(t['drift']<.01)&(t['rotation']<.25)&np.isfinite(t['drift'])&np.isfinite(t['rotation']);body=valid.all(0)&pose.all(0)&(T==horizon)
 drift=np.linalg.norm(t['object_pos']-t['init_object_pos'],axis=-1);assert np.allclose(drift,t['drift'],atol=2e-6)
 q=t['object_rot'].astype(float);q0=t['init_object_rot'].astype(float);v=-q[...,3,None]*q0[...,:3]+q0[...,3,None]*q[...,:3]-np.cross(q[...,:3],q0[...,:3]);rotation=2*np.arcsin(np.clip(np.linalg.norm(v,axis=-1),0,1));assert np.array_equal(rotation<.25,t['rotation']<.25)
 error=abs(t['slider']-t['goal']);cycles=np.zeros(N,int);reached_counts=np.zeros(N,int);first_arrival=np.full(N,np.nan)
 if protocol=='F':
  phase=np.zeros(N,int);streak=np.zeros(N,int);init=t['goal'][0]-.04
  for k in range(T):
   assert np.allclose(t['goal'][k][valid[k]],(init+np.where(phase==0,.04,0))[valid[k]],atol=1e-6)
   streak=np.where(valid[k]&(error[k]<.01),streak+1,0);ready=streak>=45
   first_arrival[np.isnan(first_arrival)&ready]=(k+1)/30
   cycles+=ready&(phase==1);reached_counts+=ready;phase[ready]=1-phase[ready];streak[ready]=0
  success=cycles>=1;assert cycles.tolist()==[r['cycles'] for r in report['records']]
  holds=None
 else:
  period=report['protocol']['stage_steps'];ind=summarize(t,period);success=np.array([r['strict'] for r in ind]);assert success.tolist()==[r['stable_full_all_endpoints'] for r in report['records']]
  holds=np.zeros((N,600//period),bool)
  for stage,start in enumerate(range(0,600,period)):
   end=start+period
   if end<=T:holds[:,stage]=((error[end-9:end]<.002)&valid[end-9:end]).all(0)
   streak=np.zeros(N,int);got=np.zeros(N,bool)
   for k in range(start,min(end,T)):
    streak=np.where(valid[k]&(error[k]<.002),streak+1,0);ready=(streak>=9)&~got;got|=ready
    first_arrival[np.isnan(first_arrival)&ready]=(k+1)/30
   reached_counts+=got
  cycles=np.array([sum(r['stages_attained'][j] and r['stages_attained'][j+1] for j in range(0,len(r['stages_attained']),2)) for r in report['records']])
 assert body.tolist()==[r['body_stable'] for r in report['records']]
 trials=[];tracehash=hashlib.sha256((directory/'trace.npz').read_bytes()).hexdigest()
 for i,source in enumerate(selection['source_order']):
  active=t['active'][:,i];bad=np.flatnonzero(~valid[:,i]|~pose[:,i]);first_bad=float((bad[0]+1)/30) if len(bad) else None
  init=t['goal'][0,i]-.04;path=t['slider'][:,i][active]
  trials.append(dict(geometry=label,model=model,protocol=protocol,source=source,attempt_row=selection['selected_attempt_rows'][i],env=i,success=bool(success[i]),body_stable=bool(body[i]),alive_full=bool(valid[:,i].all() and T==horizon),failure=('body/invalid' if not body[i] else 'endpoint' if not success[i] else None),max_drift_m=float(t['drift'][:,i][active].max()),max_rotation_rad=float(t['rotation'][:,i][active].max()),first_body_breach_s=first_bad,first_arrival_s=None if np.isnan(first_arrival[i]) else float(first_arrival[i]),max_extension_fraction=float(np.clip((path.max()-init)/.04,0,1)),travel_range_fraction=float(np.clip((path.max()-path.min())/.04,0,1)),valid_open_close_cycles=int(cycles[i]),commands_reached=int(reached_counts[i]),endpoint_holds=''.join('1' if x else '0' for x in holds[i]) if holds is not None else '',cohort_sha256=report['initial_states_sha256'],trace_sha256=tracehash,mean_abs_slider_error_m=float(error[:,i][active].mean()),max_abs_slider_error_m=float(error[:,i][active].max()),worst_stage_tail_mean_error_m=max(float(error[max(0,min(T,start+period)-9):min(T,start+period),i].mean()) for start in range(0,T,period)) if protocol!='F' else None))
 return trials
def main():
 p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,default=Path('runs/geometry-generalization-20261002'));p.add_argument('--prefix',default='screen-');p.add_argument('--output',type=Path,required=True);p.add_argument('--teacher-sha256',default='2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8');p.add_argument('--student-sha256',default='16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);models=dict(teacher=a.teacher_sha256,student=a.student_sha256)
 selections={}
 for path in a.runs.glob('*/selection.json'):
  matrix=path.parent/'valid-states.npy'
  if matrix.exists():selections[hashlib.sha256(matrix.read_bytes()).hexdigest()]=json.loads(path.read_text())
 trials=[];runs=[]
 for path in sorted(a.runs.glob(a.prefix+'*/geometry-receipt.json')):
  directory=path.parent;report=json.loads((directory/'report.json').read_text());trials+=read_run(directory,selections[report['initial_states_sha256']],models);runs.append(str(directory))
 assert trials,'No complete physical runs'
 rows=[]
 keys=sorted(set((t['geometry'],t['model'],t['protocol'],t['source']) for t in trials))
 for g,m,p,s in keys:
  group=[t for t in trials if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,m,p,s)];n=len(group);k=sum(t['success'] for t in group);b=sum(t['body_stable'] for t in group)
  rows.append(dict(geometry=g,model=m,protocol=p,source=s,n=n,success=k,rate=k/n,wilson95=wilson(k,n),body_stable=b,body_rate=b/n,body_wilson95=wilson(b,n),stable_endpoint_failures=sum(t['body_stable'] and not t['success'] for t in group),max_drift_m=max(t['max_drift_m'] for t in group),max_rotation_rad=max(t['max_rotation_rad'] for t in group),median_travel_fraction=float(np.median([t['travel_range_fraction'] for t in group])),median_first_arrival_s=float(np.median([t['first_arrival_s'] for t in group if t['first_arrival_s'] is not None])) if any(t['first_arrival_s'] is not None for t in group) else None))
 pairs=[];baseline=[]
 for g,p,s in sorted(set((t['geometry'],t['protocol'],t['source']) for t in trials)):
  teacher={t['attempt_row']:t for t in trials if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,'teacher',p,s)};student={t['attempt_row']:t for t in trials if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,'student',p,s)}
  if not teacher or not student:continue
  assert teacher.keys()==student.keys();ids=sorted(teacher)
  assert all(teacher[i]['cohort_sha256']==student[i]['cohort_sha256'] for i in ids)
  row=dict(geometry=g,protocol=p,source=s,n=len(ids))
  for metric in ['success','body_stable']:
   x=[teacher[i][metric] for i in ids];y=[student[i][metric] for i in ids];difference=np.array(x,int)-np.array(y,int)
   row[metric]=dict(both_success=sum(a and b for a,b in zip(x,y)),teacher_only=sum(a and not b for a,b in zip(x,y)),student_only=sum(not a and b for a,b in zip(x,y)),both_fail=sum(not a and not b for a,b in zip(x,y)),teacher_minus_student=float(difference.mean()),paired_bootstrap95=paired_ci(difference))
  pairs.append(row)
 for row in rows:
  group=[t for t in trials if all(t[k]==row[k] for k in ['geometry','model','protocol','source'])]
  k=sum(t['success'] and t['body_stable'] for t in group)
  row.update(success_and_full_stability=k,success_and_full_stability_rate=k/row['n'],success_and_full_stability_wilson95=wilson(k,row['n']),median_mean_abs_slider_error_m=float(np.median([t['mean_abs_slider_error_m'] for t in group])))
 for row in rows:
  g,m,p,s=[row[k] for k in ['geometry','model','protocol','source']]
  if g=='baseline':continue
  base={t['attempt_row']:t for t in trials if (t['geometry'],t['model'],t['protocol'],t['source'])==('baseline',m,p,s)};changed={t['attempt_row']:t for t in trials if (t['geometry'],t['model'],t['protocol'],t['source'])==(g,m,p,s)};ids=sorted(base.keys()&changed.keys())
  if ids:
   difference=[int(changed[i]['success'])-int(base[i]['success']) for i in ids];baseline.append(dict(geometry=g,model=m,protocol=p,source=s,shared_lineage_n=len(ids),changed_minus_baseline=float(np.mean(difference)),paired_bootstrap95=paired_ci(difference),scope='shared perturbation lineage; adapted states differ physically'))
 macro=[]
 for m,p in sorted(set((r['model'],r['protocol']) for r in rows)):
  groups=[]
  for g in sorted(set(r['geometry'] for r in rows)):
   group=[r for r in rows if (r['geometry'],r['model'],r['protocol'])==(g,m,p)]
   if len(group)==4:groups.append(dict(geometry=g,rate=float(np.mean([r['rate'] for r in group])),body_rate=float(np.mean([r['body_rate'] for r in group])),worst_source=min(r['rate'] for r in group)))
  if groups:macro.append(dict(model=m,protocol=p,complete_geometries=len(groups),equal_geometry_source_macro=float(np.mean([r['rate'] for r in groups])),worst_geometry=min(groups,key=lambda r:r['rate']),geometries=groups,scope='incomplete-source geometries remain separate; not averaged away'))
 conditional_macro=[]
 for m,p in sorted(set((r['model'],r['protocol']) for r in rows)):
  groups=[]
  for g in sorted(set(r['geometry'] for r in rows)):
   group=[r for r in rows if (r['geometry'],r['model'],r['protocol'])==(g,m,p)]
   if group:groups.append(dict(geometry=g,covered_sources=[r['source'] for r in group],missing_sources=sorted(set(range(4))-{r['source'] for r in group}),minimum_source_n=min(r['n'] for r in group),rate=float(np.mean([r['rate'] for r in group])),body_rate=float(np.mean([r['body_rate'] for r in group])),success_and_full_stability_rate=float(np.mean([r['success_and_full_stability_rate'] for r in group])),worst_source=min(group,key=lambda r:r['rate'])))
  if groups:conditional_macro.append(dict(model=m,protocol=p,geometries=len(groups),equal_geometry_available_source_macro=float(np.mean([r['rate'] for r in groups])),body_macro=float(np.mean([r['body_rate'] for r in groups])),success_and_full_stability_macro=float(np.mean([r['success_and_full_stability_rate'] for r in groups])),worst_geometry=min(groups,key=lambda r:r['rate']),geometry_rows=groups,scope='Conditional on available sources only; geometry coverage differs and is explicit. No claim of full4source coverage or continuous range.'))
 result=dict(rows=rows,paired=pairs,baseline_paired=baseline,macro=macro,available_source_macro=conditional_macro,runs=runs,expected_model_sha256=models,independent_rescore=True,time_convention='Trace captures after each30Hzphysics control step: framek at(k+1)/30s.',statistics='Episode unit; Wilson95 per cell; bootstrap within paired episode; source/geometry explicit; zero valid source is missing coverage, not0%policy success')
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
 for name,records in [('episodes.csv',trials),('cells.csv',rows)]:
  with (a.output/name).open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 print(json.dumps(dict(completed_runs=len(runs),episodes=len(trials),cells=len(rows),macro=macro)))
if __name__=='__main__':main()
