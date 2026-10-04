"""Three targeted actual continuous checks, not a generalization matrix."""
import json,subprocess,time
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';audit_job=B/'jobs/actual-table-direct-side-support-motor-audit-v1/result.json'
while not audit_job.exists():time.sleep(3)
assert json.loads(audit_job.read_text())['exit_code']==0
base=json.loads((B/'jobs/opposed-table-strong-continuous-2cycles-v4/identity.json').read_text())['command'][1:]
cases=[('actual-table-direct-side-2cycles-v8',B/'continuous-plans-v4/direct-tangential/reference-v1-retry1.json',B/'continuous-plans-v3/table-index-side/continuous-motor-plan-v1.json','.2'),('actual-table-projected-no-groove-v9',B/'continuous-plans-v1/opposed-table-strong/interpolation-repaired-reference-v5.json',B/'pickup-plans-v1/opposed/table-support-projected-motor-plan-v6-retry1.json','0'),('actual-table-direct-no-groove-v10',B/'continuous-plans-v4/direct-tangential/reference-v1-retry1.json',B/'pickup-plans-v1/opposed/table-support-projected-motor-plan-v6-retry1.json','0')]
for name,ref,plan,detent in cases:
 a=base.copy();trial=B/'continuous'/name;a[a.index('--output')+1]=str(trial);a[a.index('--thumb-script')+1]=str(ref);a[a.index('--grasp-plan')+1]=str(plan);a[a.index('--detent')+1]=detent
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+a,check=True)
 subprocess.run([PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)],check=True)
 record('targeted_direct_support_or_groove_check_completed',evidence=str(trial),config={'running_capacity_N':.2,'startup_and_groove_capacity_N':float(detent),'scope':'Actualcontinuousdevelopment mechanicaldiagnostic; .2/0 removesbarrier only forcausalcheck, not mainloadedacceptance orindependentgen'},next='Reviewcontact/rotation/endpoints; choose supportgeometry ortraction control fromactualbehavior, notrawmodelpressure')
