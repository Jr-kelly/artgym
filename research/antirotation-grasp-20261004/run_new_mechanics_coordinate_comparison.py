"""Bounded new-mechanics comparison, no unchanged pilot extension."""
import json,subprocess,time,hashlib
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');PY='/home/agiuser/miniconda3/envs/artgym/bin/python';joint='actual-lower-side-fullmotor-joint-reset750-v2';normal='actual-lower-side-fullmotor-contactnormal-reset750-v3'
def run(name,args):subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
def evaluate(name,weight):
 a=json.loads((B/'jobs/actual-table-lower-side-calibrated-direct-continuous-2cycles-v12/identity.json').read_text())['command'][1:];trial=B/'continuous'/name;idx=a.index('--thumb-script');a[idx:idx+2]=['--residual-checkpoint',str(weight)];a[a.index('--output')+1]=str(trial);run(name,a);run(name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]);record('new_mechanics_frozen_native_development_check_completed',evidence=str(trial),config={'checkpoint':str(weight),'sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'scope':'Frozen development nominal actual full36s workflow, not independentgen'},next='Inspect two-way endpoints and cumulative relative slip, not trainingloss alone')
weight=B/'train'/joint/'update_000050.pth'
while not weight.exists():
 result=B/'jobs'/joint/'result.json'
 if result.exists():assert json.loads(result.read_text())['exit_code']==0,'Training failed before checkpoint50'
 time.sleep(5)
time.sleep(10);evaluate('actual-lower-side-fullmotor-joint-frozen50-nominal-v2',weight)
result=B/'jobs'/joint/'result.json'
while not result.exists():time.sleep(5)
assert json.loads(result.read_text())['exit_code']==0
args=json.loads((B/'jobs'/joint/'identity.json').read_text())['command'][1:];args[args.index('--output')+1]=str(B/'train'/normal);args[args.index('--updates')+1]='50';args+=['--support-delta-coordinates','contact-normal'];record('new_mechanics_contact_normal_comparison_started',config={'variant':normal,'change':'Same newactualtable/lowerlateralindex/fullmotor path/noisyphysicaltraining and budget; only actor supportcorrection basis differs and has no frozen supportprior','updates':50,'scope':'One bounded mechanistic comparison, no old coordinatepilot continuation'},next='Freeze50 and compare fullnative behavior');run(normal,args);evaluate('actual-lower-side-fullmotor-contactnormal-frozen50-nominal-v3',B/'train'/normal/'update_000050.pth');record('new_mechanics_coordinate_comparison_completed',evidence=str(B/'train'/normal),next='No automatic extension: choose next from full behavior and initial-geometry evidence')
