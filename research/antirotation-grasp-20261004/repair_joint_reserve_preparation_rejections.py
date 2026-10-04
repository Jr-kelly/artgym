"""One common bound-enforcement repair before behavioral validation, no reroll."""
import copy,hashlib,json,subprocess,time
from pathlib import Path
from scripts.project_wuji_initial_motor_preload import project as project_self
from scripts.project_wuji_estimated_table_preload import project_all
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');O=B/'common-joint-reserve-repair-v2';O.mkdir(exist_ok=False);PY='/home/agiuser/miniconda3/envs/artgym/bin/python';loc=json.loads((B/'pickup-plans-v1/opposed/localization.json').read_text());op0=json.loads((B/'continuous-plans-v6/lower-side-calibrated/settled-operation-grasp.json').read_text());all_results=[]
for kind,root,count in [('height',B/'height-geometry-bank8-v1',8),('fresh',B/'fresh-joint-challenges4-v1',4)]:
 path=root/('outcomes.json' if kind=='height' else 'manifest.json')
 while not path.exists() or len(json.loads(path.read_text()) if kind=='height' else json.loads(path.read_text())['rows'])<count:time.sleep(5)
 source=json.loads(path.read_text());rows=source if kind=='height' else source['rows'];corrected=[]
 for i,row in enumerate(rows):
  passed=row['passed'] if kind=='height' else row['geometry_passed'];source_dir=Path(row['output'] if kind=='height' else row['directory'])
  if passed:corrected.append(dict(row,repair_performed=False));continue
  dest=O/('%s-%02d'%(kind,i));dest.mkdir();estimate=json.loads((source_dir/'estimate.json').read_text());motor=project_self(json.loads((source_dir/'motor-plan.json').read_text()));motor=project_all(motor,loc) if motor['initial_motor_self_projection']['passed'] else motor;(dest/'motor-plan.json').write_text(json.dumps(motor,indent=2));(dest/'estimate.json').write_text(json.dumps(estimate,indent=2));valid=motor['initial_motor_self_projection']['passed'] and motor.get('common_initial_table_projection',{}).get('passed',False);checks=[];record('common_joint_reserve_rejection_repair_started',config={'kind':kind,'source_motor_sha256':hashlib.sha256((source_dir/'motor-plan.json').read_bytes()).hexdigest(),'scope':'Same originallo/hi5mrad reserve/self geometry; fixed shortcut nowchecks bounds, originalfailurepreserved. No actor/currenttruth/physicalID or measuredpressure. No redrawncondition.'},evidence=str(dest),next='Sameacquisition/transfer/fullthumb originaldensegates, no criterion relaxation')
  if valid:
   op=copy.deepcopy(op0);op.update(close_q=motor['post_lift_close_q'],initial_geometry_estimate=estimate);(dest/'operating-plan.json').write_text(json.dumps(op,indent=2));commands=[('acquisition',['-m','scripts.audit_wuji_actual_acquisition_motor','--plan',str(dest/'motor-plan.json'),'--acquisition',str(B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json'),'--output',str(dest/'acquisition-audit.json')]),('transfer',['-m','scripts.audit_wuji_pickup_preload','--plan',str(dest/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(dest/'transfer-audit.json')]),('thumbplan',['-m','scripts.plan_g2_direct_thumb_motor_stroke','--plan',str(dest/'operating-plan.json'),'--output',str(dest/'reference.json')]),('thumbdense',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(dest/'reference.json'),'--motor-plan',str(dest/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(dest/'motor-audit.json')])]
   for stage,args in commands:
    code=subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name','reserve-%s-%02d-%s-v2'%(kind,i,stage),'--',PY]+args).returncode;checks.append({'stage':stage,'exit_code':code})
    if code:valid=False;break
  updated=dict(row,repair_performed=True,original_rejection_directory=str(source_dir),repair_directory=str(dest),repair_checks=checks)
  if kind=='height':updated.update(passed=valid,output=str(dest))
  else:updated.update(geometry_passed=valid,directory=str(dest))
  corrected.append(updated);all_results.append(updated);(O/'repair-outcomes.json').write_text(json.dumps(all_results,indent=2));record('common_joint_reserve_rejection_repair_closed',config={'kind':kind,'passed':valid,'scope':'Geometry preparation only, no behavioraltest/resultsselection'},evidence=str(dest),next='Retainallcases andsourcefailures; freshcases remainunopened until actorfreeze')
 (O/(kind+'-corrected-outcomes.json')).write_text(json.dumps(corrected,indent=2));record('common_joint_reserve_bank_ready',config={'kind':kind,'count':len(corrected),'qualified':sum(r.get('passed',r.get('geometry_passed',False)) for r in corrected)},evidence=str(O/(kind+'-corrected-outcomes.json')),next='Height commoncurriculum orpredeclaredfreshchallenge; do not reusefailednominalcertificate')
