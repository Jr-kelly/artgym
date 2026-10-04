"""Actual thin-geometry trial only after full original motor/acquisition gates."""
import json,time,subprocess,os
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'initial-geometry-v4/thin-projected04-complete';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';gate=B/'jobs/thin-repaired-full-motor-dense-audit-v4/result.json'
while not gate.exists():
 try:
  stat=Path('/proc/1161145/stat').read_text().split()[2];assert stat!='Z'
 except (FileNotFoundError,AssertionError):
  record('thin_complete_geometry_pipeline_ended_before_full_gate',evidence=str(P),next='Inspect explicit upstream failure; no physical execution');raise SystemExit(1)
 time.sleep(5)
assert json.loads(gate.read_text())['exit_code']==0
def run(name,args):subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
run('thin-complete-actual-acquisition-dense-audit-v4',['-m','scripts.audit_wuji_actual_acquisition_motor','--plan',str(P/'motor-plan.json'),'--acquisition',str(B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json'),'--output',str(P/'acquisition-audit.json')])
a=json.loads((B/'jobs/actual-table-projected-size08-frozen750-load2-v19/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-thin-complete-frozen750-load2-v22'
for key,value in [('--grasp-plan',P/'motor-plan.json'),('--thumb-reference-override',P/'reference.json'),('--knife-asset','assets/objects/knife_wuji_dense_under_20261003/t0001/mobility.urdf'),('--output',trial)]:a[a.index(key)+1]=str(value)
run(trial.name,a);run(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]);record('thin_complete_projection_actual_trial_completed',evidence=str(trial),config={'controller_weight':'Frozen750 unchanged','scope':'One traingeometry development case, common onceestimated original-mesh projection; not independentgen'},next='Judge actual pickup/retention/return, then decide common geometry curriculum')
