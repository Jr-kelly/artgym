"""Same projected noisy nominal motor path, higher passive capacity."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';a=json.loads((B/'jobs/actual-table-noisy-nominal-projected-continuous-2cycles-v13/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-noisy-nominal-projected-load5-v14'
for key,value in [('--output',trial),('--load','.5'),('--detent','.5'),('--handover-calibration',B/'initial-geometry-v2/projected-00/calibration-nominal-prior.json')]:a[a.index(key)+1]=str(value)
subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name','actual-table-noisy-nominal-projected-load5-v14','--',PY]+a,check=True);subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name','actual-table-noisy-nominal-projected-load5-functional-v14','--',PY,'-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)],check=True);record('projected_noisy_nominal_higher_load_check_completed',evidence=str(trial),config={'run_startup_capacities_N':[.5,.5],'scope':'Paired development load challenge, passive capacity not real instantaneous force or real upper resistance limit'},next='Decide pressure/support/reverse reach from actual fullcycle behavior, no endpointdecimal fitting')
