"""Reuse timed scoring and existing paired intervals; no GPU or model selection."""
import json,csv
import numpy as np
from scripts.record_wuji_real_size_goal import R,D
from scripts.wuji_timed_command_metrics import score_timed_trace
from scripts.summarize_wuji_unified import wilson
from scripts.analyze_wuji_geometry import paired_ci
B=R/'runs/real-size-student-adaptation-20261002';episodes=[];cells=[];pairs=[]
for phase in ['baseline','dev','confirm','diagnostic']:
 for p in sorted((B/phase).glob('*/press-report.json')):
  j=json.loads(p.read_text());t=dict(np.load(p.parent/'trace.npz'));k3=score_timed_trace(t,150,3,600);s5=score_timed_trace(t,150,9,600);rows=[]
  for i,r in enumerate(j['records']):
   good=t['active'][:,i]&~t['fall'][:,i]&~t['invalid'][:,i]&(t['drift'][:,i]<.01)&(t['rotation'][:,i]<.25);full=len(good)==600 and bool(good.all());stage=k3['records'][i]['stages_attained'];ordered=any(stage[o] and stage[c] for o in [0,2] for c in [1,3] if o<c);assert bool(ordered and full)==r['K20'];assert bool(s5['records'][i]['stable_full_all_endpoints'])==r['S5'];bad=np.flatnonzero(~good)
   x=dict(phase=phase,run=p.parent.name,states_sha256=j['states_sha256'],**r,first_instability_s=float((bad[0]+1)/30) if len(bad) else None);rows.append(x);episodes.append(x)
  for source in ['all']+sorted(set(x['source'] for x in rows)):
   subset=[x for x in rows if source=='all' or x['source']==source];n=len(subset);cell=dict(phase=phase,run=p.parent.name,source=source,n=n)
   for metric in ['K20','ordered_open_close','body_stable','S5']:
    k=sum(x[metric] for x in subset);cell[metric]=dict(k=k,n=n,wilson95=wilson(k,n))
   times=[x['first_instability_s'] for x in subset if x['first_instability_s'] is not None];cell['median_first_instability_s_among_failures']=float(np.median(times)) if times else None;cell['unstable_n']=len(times);cell['contact_fraction_mean']=float(np.mean([x['contact_fraction'] for x in subset]));cell['pd_saturation_proxy_mean']=float(np.mean([x['pd_saturation_proxy'] for x in subset]));cells.append(cell)
for phase in ['dev','confirm']:
 names=sorted(set(x['run'] for x in episodes if x['phase']==phase))
 for a in names:
  for b in names:
   if a>=b:continue
   aa=[x for x in episodes if x['phase']==phase and x['run']==a];bb=[x for x in episodes if x['phase']==phase and x['run']==b]
   if len(aa)!=len(bb) or aa[0]['states_sha256']!=bb[0]['states_sha256']:continue
   for metric in ['K20','ordered_open_close','body_stable','S5']:
    av=np.array([x[metric] for x in aa]);bv=np.array([x[metric] for x in bb]);delta=av.astype(float)-bv.astype(float);discord=int((av!=bv).sum());pairs.append(dict(phase=phase,a=a,b=b,metric=metric,n=len(aa),both_success=int((av&bv).sum()),a_only=int((av&~bv).sum()),b_only=int((~av&bv).sum()),both_fail=int((~av&~bv).sum()),difference=float(delta.mean()),bootstrap95=paired_ci(delta),degenerate_no_discordance=discord==0,discordance_wilson95=wilson(discord,len(aa))))
out=B/'analysis';out.mkdir(exist_ok=True);(out/'summary.json').write_text(json.dumps(dict(cells=cells,pairs=pairs),indent=2))
if episodes:
 with (out/'episodes.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(episodes[0]));w.writeheader();w.writerows(episodes)
for c in cells:
 if c['source']=='all':print(c['phase'],c['run'],*[str(c[m]['k'])+'/'+str(c['n']) for m in ['K20','ordered_open_close','body_stable','S5']])
