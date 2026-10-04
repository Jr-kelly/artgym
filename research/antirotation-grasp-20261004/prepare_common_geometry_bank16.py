"""Common initial-estimate planner on sixteen train sensor observations.

Preparation for necessary geometry curriculum, not repeated success testing.
Physical identities exist only in the external simulator schedule.
"""
import json,copy,subprocess,hashlib
from pathlib import Path
from scripts.project_wuji_initial_motor_preload import project as project_self
from scripts.project_wuji_estimated_table_preload import project_all
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=Path('research/antirotation-grasp-20261004');OUT=B/'common-geometry-bank16-v1';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';OUT.mkdir(parents=True,exist_ok=False);loc=json.loads((B/'pickup-plans-v1/opposed/localization.json').read_text());op0=json.loads((B/'continuous-plans-v6/lower-side-calibrated/settled-operation-grasp.json').read_text());rows=[];ids=[];outcomes=[]
def run(name,args):
 return subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args).returncode
for base,sid in zip(range(0,32,4),['t0000','t0001','t0002','t0003','t0005','t0007','t0009','t0011']):
 for index in [base,base+1]:
  source=B/'initial-geometry-v2'/('observation-%02d.json'%index);row=json.loads(source.read_text());out=OUT/('observation-%02d'%index);out.mkdir();record('common_geometry_curriculum_target_preparation_started',config={'observation':index,'initial_estimate':row['estimate'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scope':'Train-only labelled simulated initial observation, planner gets no physical ID or current object/contact'},evidence=str(out),next='Common bounded original geometry projection, dense gates before physics')
  motor=project_self(row['motor_plan']);motor=project_all(motor,loc) if motor['initial_motor_self_projection']['passed'] else motor;(out/'motor-plan.json').write_text(json.dumps(motor,indent=2));valid=motor['initial_motor_self_projection']['passed'] and motor.get('common_initial_table_projection',{}).get('passed',False);checks=[]
  if valid:
   close=copy.deepcopy(motor)
   for key in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:close.pop(key,None)
   (out/'closure-plan.json').write_text(json.dumps(close,indent=2));op=copy.deepcopy(op0);op.update(close_q=motor['post_lift_close_q'],initial_geometry_estimate=row['estimate']);(out/'operating-plan.json').write_text(json.dumps(op,indent=2))
   commands=[('acquisition',['-m','scripts.audit_wuji_actual_acquisition_motor','--plan',str(out/'motor-plan.json'),'--acquisition',str(B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json'),'--output',str(out/'acquisition-audit.json')]),('transfer',['-m','scripts.audit_wuji_pickup_preload','--plan',str(out/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(out/'transfer-audit.json')]),('thumbplan',['-m','scripts.plan_g2_direct_thumb_motor_stroke','--plan',str(out/'operating-plan.json'),'--output',str(out/'reference.json')]),('thumbdense',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(out/'reference.json'),'--motor-plan',str(out/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(out/'motor-audit.json')])]
   for label,args in commands:
    rc=run('common-bank16-obs%02d-%s-v1'%(index,label),args);checks.append(dict(stage=label,exit_code=rc))
    if rc:valid=False;break
  if valid:
   rows.append(dict(estimate=row['estimate'],motor_plan=motor,support_target_q=motor['post_lift_close_q'],thumb_reference=json.loads((out/'reference.json').read_text())));ids.append(sid)
  outcomes.append(dict(observation=index,passed=valid,checks=checks,output=str(out)));(OUT/'outcomes.json').write_text(json.dumps(outcomes,indent=2));(OUT/'records.json').write_text(json.dumps(rows,indent=2));(OUT/'physical-schedule-templates.json').write_text(json.dumps({'instances':ids,'scope':'Simulator train loading only; no physical identity supplied to planner or actor'},indent=2));record('common_geometry_curriculum_target_preparation_closed',config={'observation':index,'original_dense_passed':valid,'valid_templates_so_far':len(rows)},evidence=str(out),next='Continue necessary train geometry preparation; rejected templates excluded without physics relaxation')
record('common_geometry_bank16_preparation_completed',evidence=str(OUT),config={'passed':len(rows),'attempted':len(outcomes),'scope':'Geometry preparation only, no actual behavior or independent validation'},next='Actual small batch compatibility with matching physical schedule, then qualified necessary-geometry curriculum only if genuine support holds')
