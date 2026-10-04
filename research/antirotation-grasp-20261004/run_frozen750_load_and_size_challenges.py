"""Two focused frozen750 challenges after first full actual functional demo."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';base=json.loads((B/'jobs/actual-table-projected-grasp-frozen750-load2-v17/identity.json').read_text())['command'][1:]
for label,size,load in [('actual-table-projected-grasp-frozen750-load5-v18',None,'.5'),('actual-table-projected-size08-frozen750-load2-v19',8,'.2')]:
 a=base.copy();trial=B/'continuous'/label;a[a.index('--output')+1]=str(trial);a[a.index('--load')+1]=load;a[a.index('--detent')+1]=load
 if size is not None:
  p=B/'initial-geometry-v2'/('projected-%02d'%size);assert json.loads((p/'motor-audit.json').read_text())['all_passed'] and json.loads((p/'closure-audit.json').read_text())['passed'] and json.loads((p/'transfer-audit.json').read_text())['passed'];a[a.index('--grasp-plan')+1]=str(p/'motor-plan.json');a[a.index('--thumb-reference-override')+1]=str(p/'reference-v1.json');a+=['--knife-asset','assets/objects/knife_wuji_dense_under_20261003/t0002/mobility.urdf']
 subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',label,'--',PY]+a,check=True);subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',label+'-functional','--',PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)],check=True);record('frozen750_full_flow_load_or_geometry_challenge_completed',evidence=str(trial),config={'scope':'Same frozen750 actor, common noisyinitial geometry/PD motor planning; developmental challenge, not independentgen','capacities_N':[float(load),float(load)],'size_observation':size},next='Choose realremaining pickup/loadedreturn mechanism; preserve allfailures and oldcriterion, no nominaldecimal tweaking')
