"""Independent raw-trace scoring, per-episode CSV and paired student gates."""
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from scripts.summarize_wuji_unified import wilson
from scripts.summarize_wuji_multigrasp_trace import summarize

def analyze(directory,model):
 report=json.loads((directory/'report.json').read_text())
 with np.load(directory/'trace.npz') as z:t={k:z[k] for k in z.files}
 T,N=t['active'].shape;assert N%4==0;n=N//4
 kind=report['protocol']['kind'];protocol='F' if kind=='F' else 'S'+str(int(report['protocol']['stage_seconds']))
 horizon=1200 if kind=='F' else 600
 valid=t['active'].astype(bool)&~t['fall'].astype(bool)&~t['invalid'].astype(bool)
 pose=(t['drift']<.01)&(t['rotation']<.25)&np.isfinite(t['drift'])&np.isfinite(t['rotation'])
 body=valid.all(0)&pose.all(0)&(T==horizon)
 error=np.abs(t['slider']-t['goal']);holds=None
 if kind=='S':
  period=report['protocol']['stage_steps'];ind=summarize(t,period)
  success=np.array([r['strict'] for r in ind]);assert success.tolist()==[r['stable_full_all_endpoints'] for r in report['records']]
  holds=np.zeros((N,600//period),bool)
  for stage,start in enumerate(range(0,600,period)):
   end=start+period
   if end<=T:holds[:,stage]=((error[end-9:end]<.002)&valid[end-9:end]).all(0)
 else:
  phase=np.zeros(N,int);streak=np.zeros(N,int);cycles=np.zeros(N,int);init=t['goal'][0]-.04
  for k in range(T):
   expected=init+np.where(phase==0,.04,0)
   assert np.allclose(t['goal'][k][valid[k]],expected[valid[k]],atol=1e-6)
   streak=np.where(valid[k]&(error[k]<.01),streak+1,0);ready=streak>=45
   cycles+=ready&(phase==1);phase[ready]=1-phase[ready];streak[ready]=0
  assert cycles.tolist()==[r['cycles'] for r in report['records']];success=cycles>=1
 if 'init_object_pos' in t:
  drift=np.linalg.norm(t['object_pos']-t['init_object_pos'],axis=-1)
  assert np.allclose(drift,t['drift'],atol=2e-6)
  q=t['object_rot'].astype(np.float64);q0=t['init_object_rot'].astype(np.float64)
  # Quaternion q * conjugate(q0), independently in float64.
  vector=-q[...,3,None]*q0[...,:3]+q0[...,3,None]*q[...,:3]-np.cross(q[...,:3],q0[...,:3])
  angle=2*np.arcsin(np.clip(np.linalg.norm(vector,axis=-1),0,1))
  assert np.allclose(angle[valid],t['rotation'][valid],atol=2e-6)
  assert np.array_equal(angle<.25,t['rotation']<.25), 'Independent rotation threshold disagreement'
  # Inactive post-terminal spins near pi magnify float32 asin rounding;
  # validate their threshold classification, not a uniform angle tolerance.
 tracehash=hashlib.sha256((directory/'trace.npz').read_bytes()).hexdigest();rows=[];trials=[]
 for s in range(4):
  ids=np.arange(s*n,(s+1)*n);k=int(success[ids].sum());kb=int(body[ids].sum())
  row=dict(model=model,protocol=protocol,source=s,n=n,success=k,rate=k/n,wilson95=wilson(k,n),body_stable=kb,body_rate=kb/n,cohort_sha256=report['initial_states_sha256'],trace_sha256=tracehash,input_mode=report['control_mode'])
  if holds is not None:row.update(phase_hold=float(holds[ids].mean()),worst_stage_hold=float(holds[ids].mean(0).min()))
  if kind=='F':row['cycles_mean']=float(cycles[ids].mean())
  rows.append(row)
  for i in ids:
   bad=np.flatnonzero(~valid[:,i]|~pose[:,i]);first=float(bad[0]/30) if len(bad) else horizon/30
   trials.append(dict(model=model,protocol=protocol,source=s,trial=int(i-s*n),success=bool(success[i]),body_stable=bool(body[i]),alive=bool(T==horizon and valid[:,i].all()),first_body_breach_sec=first,endpoint_holds=''.join('1' if x else '0' for x in holds[i]) if holds is not None else '',cycles=int(cycles[i]) if kind=='F' else '',cohort_sha256=report['initial_states_sha256']))
 return rows,trials

def main():
 p=argparse.ArgumentParser();p.add_argument('--entries',nargs='+',required=True,help='model=directory; repeat model across protocols');p.add_argument('--teacher',default='teacher');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 rows=[];trials=[]
 for entry in a.entries:
  model,directory=entry.split('=',1);r,t=analyze(Path(directory),model);rows+=r;trials+=t
 pairs=[];gates={}
 for model in sorted(set(r['model'] for r in rows)-{a.teacher}):
  candidate=[r for r in rows if r['model']==model];checks=[]
  for r in candidate:
   ref=next((x for x in rows if x['model']==a.teacher and x['source']==r['source'] and x['protocol']==r['protocol'] and x['cohort_sha256']==r['cohort_sha256']),None)
   if ref is None:continue
   cellpass=r['rate']>=.8
   if r['protocol']!='F':cellpass=cellpass and r['body_rate']>=.95 and ref['rate']-r['rate']<=.10000001 and ref['body_rate']-r['body_rate']<=.03000001
   checks.append(dict(protocol=r['protocol'],source=r['source'],passed=cellpass,strict_drop=ref['rate']-r['rate'],body_drop=ref['body_rate']-r['body_rate']))
   ct=sorted([t for t in trials if t['model']==model and t['source']==r['source'] and t['protocol']==r['protocol']],key=lambda x:x['trial']);rt=sorted([t for t in trials if t['model']==a.teacher and t['source']==r['source'] and t['protocol']==r['protocol']],key=lambda x:x['trial'])
   assert len(ct)==len(rt)
   pairs.append(dict(model=model,source=r['source'],protocol=r['protocol'],both_pass=sum(x['success'] and y['success'] for x,y in zip(ct,rt)),teacher_only=sum(not x['success'] and y['success'] for x,y in zip(ct,rt)),student_only=sum(x['success'] and not y['success'] for x,y in zip(ct,rt)),both_fail=sum(not x['success'] and not y['success'] for x,y in zip(ct,rt)),body_both_pass=sum(x['body_stable'] and y['body_stable'] for x,y in zip(ct,rt)),body_teacher_only=sum(not x['body_stable'] and y['body_stable'] for x,y in zip(ct,rt)),body_student_only=sum(x['body_stable'] and not y['body_stable'] for x,y in zip(ct,rt)),body_both_fail=sum(not x['body_stable'] and not y['body_stable'] for x,y in zip(ct,rt))))
  gates[model]=dict(complete_cells=len(checks)==12,passed=len(checks)==12 and all(x['passed'] for x in checks),checks=checks)
 clusters=[]
 for model,protocol in sorted(set((r['model'],r['protocol']) for r in rows)):
  for name,sources in [('near01',[0,1]),('source2',[2]),('source3',[3])]:
   group=[r for r in rows if r['model']==model and r['protocol']==protocol and r['source'] in sources];n=sum(r['n'] for r in group);k=sum(r['success'] for r in group)
   clusters.append(dict(model=model,protocol=protocol,cluster=name,n=n,success=k,wilson95=wilson(k,n)))
 result=dict(rows=rows,paired_transitions=pairs,gates=gates,clusters=clusters,independent_rescore=True)
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
 with (a.output/'trials.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(trials[0]));w.writeheader();w.writerows(trials)
 print(json.dumps(dict(rows=[{k:r[k] for k in ['model','protocol','source','n','success','body_stable']} for r in rows],gates=gates)))
if __name__=='__main__':main()
