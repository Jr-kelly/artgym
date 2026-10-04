"""Distinct full-flow return-mechanism check, unchanged frozen750 actor."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';a=json.loads((B/'jobs/actual-table-continuous-tangential-prepare-load2-v20/identity.json').read_text())['command'][1:];i=a.index('--thumb-script');ref=a[i+1];a[i:i+2]=['--residual-checkpoint','runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth','--thumb-reference-override',ref];trial=B/'continuous/actual-table-continuous-prepared-frozen750-load5-v23'
for k,v in [('--output',str(trial)),('--load','.5'),('--detent','.5')]:a[a.index(k)+1]=v
record('continuous_reverse_preparation_frozen750_highload_started',config={'external_rail_command_mm':40,'virtual_motor_reference_mm':46,'original_physics':True,'controller':'Unchanged frozen750, known-clock prepared motor path; current object/contact excluded'},evidence=str(trial),next='One actual full-flow check of distinct reversal mechanism; no unchanged training extension')
for name,args in [(trial.name,a),(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)])]:subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
record('continuous_reverse_preparation_frozen750_highload_closed',evidence=str(trial),next='Judge actual useful endpoints/contact/support; no claims from motor feasibility alone')
