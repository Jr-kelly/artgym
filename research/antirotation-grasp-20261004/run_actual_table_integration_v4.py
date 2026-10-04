"""Sequential actual continuous candidate check; stop on rejected upstream geometry."""
import json,subprocess,sys,time
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'continuous-plans-v1/opposed-table-strong';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
source_job=B/'jobs/opposed-picked-up-motor-interpolation-repair-v5/result.json'
while not source_job.exists():time.sleep(3)
assert json.loads(source_job.read_text())['exit_code']==0,'Upstream motor interpolation repair rejected'
ref=P/'interpolation-repaired-reference-v5.json';motor=B/'pickup-plans-v1/opposed/table-support-projected-motor-plan-v6-retry1.json'
def run(name,args):
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
audit=P/'dense-motor-audit-v5.json'
run('opposed-picked-up-dense-motor-audit-v5',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(ref),'--motor-plan',str(motor),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(audit)])
record('actual_table_full_motor_path_passed',evidence=str(audit),conclusion='Independent dense actualtarget originalself/limit audit passed; no continuous success claim before physicalrollout',next='Immediate actual36second tablepickup and two loadedcycles, full/closeup videos')
a=json.loads((B/'jobs/opposed-table-strong-support-pickup-v3/identity.json').read_text())['command'][1:];a.remove('--grasp-only');a[a.index('--seconds')+1]='36';trial=B/'continuous/opposed-table-strong-2cycles-v4';a[a.index('--output')+1]=str(trial);a+=['--thumb-script',str(ref),'--handover-calibration',str(P/'nominal-calibration.json')]
run('opposed-table-strong-continuous-2cycles-v4',a)
run('opposed-table-strong-continuous-evaluate-v4',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])
record('actual_table_continuous_candidate_completed',evidence=str(trial),next='Read functional/contact/relativegrip results and actualfilm before training/claimingfullflow')
