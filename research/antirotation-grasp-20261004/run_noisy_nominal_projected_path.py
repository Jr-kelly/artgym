"""Collision-constrained noisy initial estimate development, no online truth."""
import json,subprocess,copy,numpy as np
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'initial-geometry-v2/projected-00';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
def run(name,args,required=True):
 result=subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args);assert result.returncode==0 or not required;return result.returncode
plan=json.loads((P/'motor-plan.json').read_text());close=copy.deepcopy(plan)
for key in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:close.pop(key,None)
(P/'closure-plan.json').write_text(json.dumps(close,indent=2));rc=run('projected-noisy-nominal-closure-audit-v2',['-m','scripts.audit_wuji_pickup_preload','--plan',str(P/'closure-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/'closure-audit.json')],False)
audit=json.loads((P/'closure-audit.json').read_text());assert all(not r['uncertified_self_pairs'] for r in audit['rows']);assert min(r['minimum_table_gap_m'] for r in audit['rows'])>0
if rc:
 record('projected_noisy_nominal_table_margin_certificate_failed',evidence=str(P/'closure-audit.json'),config={'original_300um_margin_passed':False,'actual_minimum_mesh_table_gap_m':min(r['minimum_table_gap_m'] for r in audit['rows']),'self_geometry_clear':True},next='Preserve failed300um certificate; single actual development rollout allowed with positive original-mesh separation, no margin/physics changes')
run('projected-noisy-nominal-transfer-audit-v2',['-m','scripts.audit_wuji_pickup_preload','--plan',str(P/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/'transfer-audit.json')])
run('projected-noisy-nominal-direct-motor-path-v2',['-m','scripts.plan_g2_direct_thumb_motor_stroke','--plan',str(P/'operating-plan.json'),'--output',str(P/'reference-v1.json')])
run('projected-noisy-nominal-dense-motor-audit-v2',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(P/'reference-v1.json'),'--motor-plan',str(P/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(P/'motor-audit.json')])
cal=json.loads((B/'continuous-plans-v6/lower-side-calibrated/nominal-calibration.json').read_text());cal['scope']='Previous nominal prior only. Native runner applies the labelled noisy initial observation once; do not preapply its shift.';(P/'calibration-nominal-prior.json').write_text(json.dumps(cal,indent=2))
a=json.loads((B/'jobs/actual-table-lower-side-calibrated-direct-continuous-2cycles-v12/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-noisy-nominal-projected-2cycles-v13'
for key,value in [('--output',trial),('--grasp-plan',P/'motor-plan.json'),('--thumb-script',P/'reference-v1.json'),('--handover-calibration',P/'calibration-nominal-prior.json')]:a[a.index(key)+1]=str(value)
run('actual-table-noisy-nominal-projected-continuous-2cycles-v13',a);run('actual-table-noisy-nominal-projected-functional-evaluation-v13',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])
record('projected_noisy_initial_observation_actual_trial_completed',evidence=str(trial),next='Compare observed pickup/loaded two-cycle behavior; common planner developmental test, never independent generalization')
