"""Fresh actual pickup; fixed calibration from preceding development trial only."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004'); P=B/'continuous-plans-v6/lower-side-calibrated'; PY='/home/agiuser/miniconda3/envs/artgym/bin/python'; ref=P/'reference-v1.json'; plan=B/'continuous-plans-v5/table-lower-side-index/continuous-motor-plan-v1.json'
def run(name,args):subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
run('lower-side-calibrated-direct-motor-audit-v1',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(ref),'--motor-plan',str(plan),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(P/'full-thumb-motor-audit-v1.json')])
a=json.loads((B/'jobs/actual-table-lower-side-direct-continuous-2cycles-v11/identity.json').read_text())['command'][1:]; trial=B/'continuous/actual-table-lower-side-calibrated-direct-2cycles-v12'
for key,value in [('--output',trial),('--thumb-script',ref),('--handover-calibration',P/'nominal-calibration.json')]:a[a.index(key)+1]=str(value)
run('actual-table-lower-side-calibrated-direct-continuous-2cycles-v12',a)
run('actual-table-lower-side-calibrated-functional-evaluation-v12',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])
record('actual_table_lower_side_calibrated_candidate_completed',evidence=str(trial),state_updates={'lower_side_direct_pipeline_pid':None},next='Compare cumulative relative rotation and loaded two-way progress; fixed prior only, no current truth in controller')
