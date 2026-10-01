"""Paired learner-state latent intervention diagnosis; never label it deployable."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from scripts.analyze_wuji_geometry import read_run,paired_ci
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);root=Path('runs/geometry-generalization-20261002');models=dict(teacher='2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8',student='16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9');rows=[];target_rows=[]
 for label,target_source in [('L110',1),('W120',3)]:
  selection=json.loads((root/(label+'-static-confirm64')/'selection.json').read_text());parent_dir=root/('confirm64-'+label+'-student-F');intervention_dir=root/('latent-intervention-'+label+'-student-F')
  receipt=json.loads((intervention_dir/'geometry-receipt.json').read_text());assert not receipt['student_legal_inputs'] and receipt['teacher_latent_after_seconds']==2
  assert json.loads((intervention_dir/'report.json').read_text())['unified_student_sha256']==models['student']
  parent=read_run(parent_dir,selection,models);intervened=read_run(intervention_dir,selection,models);assert [r['attempt_row'] for r in parent]==[r['attempt_row'] for r in intervened]
  with np.load(parent_dir/'trace.npz') as x,np.load(intervention_dir/'trace.npz') as y:
   prefix=dict(action_max=float(abs(x['action'][:60]-y['action'][:60]).max()),goal_exact=bool(np.array_equal(x['goal'][:60],y['goal'][:60])),slider_max_m=float(abs(x['slider'][:60]-y['slider'][:60]).max()))
   assert prefix==dict(action_max=0.0,goal_exact=True,slider_max_m=0.0), 'Learner prefix is not paired exactly'
  for source in sorted(set(r['source'] for r in parent)):
   ids=[i for i,r in enumerate(parent) if r['source']==source];row=dict(geometry=label,source=source,n=len(ids),target=source==target_source,prefix=prefix)
   for metric in ['success','body_stable']:
    u=np.array([parent[i][metric] for i in ids],int);v=np.array([intervened[i][metric] for i in ids],int);d=v-u
    row[metric]=dict(parent=int(u.sum()),intervention=int(v.sum()),improvement_pp=float(d.mean()*100),paired_bootstrap95_pp=[x*100 for x in paired_ci(d)],both_success=int(((u==1)&(v==1)).sum()),parent_only=int(((u==1)&(v==0)).sum()),intervention_only=int(((u==0)&(v==1)).sum()),both_fail=int(((u==0)&(v==0)).sum()))
   if row['target']:
    row['supervision_supported']=row['body_stable']['improvement_pp']>=15 and row['body_stable']['paired_bootstrap95_pp'][0]>0 and row['success']['improvement_pp']>=-5;target_rows.append(row)
   rows.append(row)
 supported=all(r['supervision_supported'] for r in target_rows)
 result=dict(rows=rows,targets=target_rows,useful_supervision_supported=supported,criterion='Registered >=15ppholding gain, pairedCI lower>0 on each target; function notclearlyworse. Samefrozenlearner actor/RNN, privilegedteacherlatent after2s; no newmodel and notstudentdeployment capability.',scope='Diagnostic of current teacher supervision onlearner prefixes; no proof studentcaninferteacherlatent or trainingwillimprove. Source2 deterioration remains explicit.')
 (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
