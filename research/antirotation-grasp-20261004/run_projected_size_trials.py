"""Two focused development geometry challenges, all failures retained."""
import json,subprocess,copy
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=B/'initial-geometry-v2';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
def run(name,args):return subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args).returncode
for i,sid in [(4,'t0001'),(8,'t0002')]:
 p=D/('projected-%02d'%i);assert json.loads((p/'motor-audit.json').read_text())['all_passed'];plan=json.loads((p/'motor-plan.json').read_text());close=copy.deepcopy(plan)
 for key in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:close.pop(key,None)
 (p/'closure-plan.json').write_text(json.dumps(close,indent=2));rc=run('projected-size-%02d-closure-audit-v2'%i,['-m','scripts.audit_wuji_pickup_preload','--plan',str(p/'closure-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(p/'closure-audit.json')]);audit=json.loads((p/'closure-audit.json').read_text())
 clear=all(not r['uncertified_self_pairs'] for r in audit['rows']) and min(r['minimum_table_gap_m'] for r in audit['rows'])>0
 if not clear:
  record('projected_size_closure_geometry_rejected',evidence=str(p/'closure-audit.json'),config={'observation':i},next='Original table/self conflict blocks actual trial; repair common pickup preform, no hiddencollision relaxation');continue
 if rc:record('projected_size_table_reserve_certificate_failed',evidence=str(p/'closure-audit.json'),config={'observation':i,'original300um_passed':False,'minimum_mesh_table_gap_m':min(r['minimum_table_gap_m'] for r in audit['rows'])},next='Single physics development allowed with positiveoriginalmesh separation; retainfalsecertificate andunchangedtablephysics')
 rc=run('projected-size-%02d-transfer-audit-v2'%i,['-m','scripts.audit_wuji_pickup_preload','--plan',str(p/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(p/'transfer-audit.json')])
 if rc:continue
 a=json.loads((B/'jobs/actual-table-noisy-nominal-projected-continuous-2cycles-v13/identity.json').read_text())['command'][1:];trial=B/'continuous'/('actual-table-projected-size-%02d-load2-v16'%i)
 for key,value in [('--output',trial),('--grasp-plan',p/'motor-plan.json'),('--thumb-script',p/'reference-v1.json'),('--handover-calibration',B/'continuous-plans-v6/lower-side-calibrated/nominal-calibration.json')]:a[a.index(key)+1]=str(value)
 a+=['--knife-asset','assets/objects/knife_wuji_dense_under_20261003/'+sid+'/mobility.urdf'];rc=run(trial.name,a)
 if rc:continue
 run(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]);record('projected_noisy_size_actual_development_completed',evidence=str(trial),config={'observation':i,'physical_loading_sid':sid,'actor_asset_id_input':False,'scope':'Common noisy initial geometry mechanism; train geometry developmental challenge, not independent validation'},next='Choose pickup/continuousoperation adaptation fromactualfailure; no coverage claim fromsuccessfulIK')
