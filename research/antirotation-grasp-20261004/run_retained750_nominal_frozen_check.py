"""One qualified retained-policy pilot; judge actual loaded behavior after fit."""
import json,subprocess,time,hashlib
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';name='actual-projected-realnominal-retain750-v4';r=B/'jobs'/name/'result.json'
while not r.exists():time.sleep(5)
assert json.loads(r.read_text())['exit_code']==0
weight=B/'train'/name/'update_000050.pth';a=json.loads((B/'jobs/actual-table-projected-grasp-frozen750-load5-v18/identity.json').read_text())['command'][1:];a[a.index('--residual-checkpoint')+1]=str(weight);trial=B/'continuous/actual-table-projected-retain750-frozen50-load5-v21';a[a.index('--output')+1]=str(trial)
for job,args in [(trial.name,a),(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])]:subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',job,'--',PY]+args,check=True)
record('retained750_projected_nominal_pilot_frozen50_completed',evidence=str(trial),config={'weight_sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'development_scope':'Realnominal geometry, capped50 mixed resistance and sensor fitting; same.5/.5 actual continuous check as frozen750, not independent necessary geometry validation'},next='Compare actual support/contact/traction and reversals against V18; no unchanged pilot extension')
