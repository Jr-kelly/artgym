"""Original geometry audit then one actual prepared46mm motor trajectory."""
import json,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'bidirectional-motor-preload-v2/continuous-flow';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';assert json.loads((P/'postlift-path.json').read_text())['preflight_passed']
def run(name,args):subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
run('prepared-bidirectional-full-motor-original-audit-v2',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(P/'reference.json'),'--motor-plan',str(P/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(P/'full-motor-audit.json')])
a=json.loads((B/'jobs/actual-table-gravity-seated-roll20-load2-v15/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-continuous-tangential-prepare-load2-v20'
for key,value in [('--output',trial),('--grasp-plan',P/'motor-plan.json'),('--thumb-script',P/'reference.json'),('--postlift-regrasp',P/'postlift-path.json')]:a[a.index(key)+1]=str(value)
run(trial.name,a);run(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]);record('continuous_tangential_preparation_actual_physics_completed',evidence=str(trial),config={'rail_external_command_mm':40,'virtual_motor_stroke_mm':46,'scope':'Actual motor preparation13.2--14.2 and shared bidirectional reference, originalbody/rail/PD/limits and genuinehistory; motorlead not constantforce or railpositive assistance; developmental subcandidate, prior fullV17 remainsfrozen'},next='Judge realpreparation contact, loadedreturn/fullextension andbody support. If transfer fails, do not extend its training.')
