"""Focused eight-observation collision screen; no performance claims."""
import json,subprocess,copy
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');d=B/'initial-geometry-v2';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';results=[]
for i in range(0,32,4):
 row=json.loads((d/('observation-%02d.json'%i)).read_text());p=d/('audit-%02d'%i);p.mkdir(exist_ok=False);plan=row['motor_plan'];(p/'motor-plan.json').write_text(json.dumps(plan,indent=2));(p/'reference.json').write_text(json.dumps(row['thumb_reference'],indent=2));close=copy.deepcopy(plan)
 for k in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:close.pop(k,None)
 (p/'closure-plan.json').write_text(json.dumps(close,indent=2));checks=[]
 for label,args in [('closure',['-m','scripts.audit_wuji_pickup_preload','--plan',str(p/'closure-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(p/'closure-audit.json')]),('postlift',['-m','scripts.audit_wuji_pickup_preload','--plan',str(p/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(p/'postlift-audit.json')]),('thumb',['-m','scripts.audit_g2_anchored_thumb_motor','--motor-plan',str(p/'motor-plan.json'),'--reference',str(p/'reference.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','81','--output',str(p/'thumb-audit.json')])]:
  v=subprocess.run([PY]+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(p/(label+'.log')).write_text(v.stdout);checks.append({'stage':label,'exit_code':v.returncode});print(json.dumps({'observation':i,'stage':label,'exit_code':v.returncode}),flush=True)
 results.append({'observation':i,'estimate':row['estimate'],'checks':checks})
(d/'representative-geometry-audit.json').write_text(json.dumps({'scope':'Eight labelled initial observations, original motor/self/table constraints; no independent physics success','rows':results},indent=2));record('representative_two_stage_geometry_audit_completed',evidence=str(d/'representative-geometry-audit.json'),config={'passed_observations':sum(all(c['exit_code']==0 for c in r['checks']) for r in results),'total':len(results)},next='Repair reachable motor projection if original geometry fails; no physical rollout for invalid target path; initial estimate cannot imply generalization')
