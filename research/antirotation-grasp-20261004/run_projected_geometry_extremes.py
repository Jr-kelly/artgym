"""Two structurally different body-size estimates through original geometry."""
import subprocess,json,time
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');D=B/'initial-geometry-v2';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
def run(name,args):return subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args).returncode
for i in [4,8]:
 p=D/('projected-%02d'%i);stem='noisy-size-%02d'%i
 rc=run(stem+'-original-motor-projection-v2',['-m','scripts.project_wuji_initial_motor_preload','--observation',str(D/('observation-%02d.json'%i)),'--operating-plan',str(B/'continuous-plans-v6/lower-side-calibrated/settled-operation-grasp.json'),'--output',str(p)])
 if rc:
  record('noisy_size_motor_projection_failed',evidence=str(p),config={'observation':i},next='Inspect original geometry conflict; no physical execution or generic coverage claim');continue
 rc=run(stem+'-full-direct-motor-path-v2',['-m','scripts.plan_g2_direct_thumb_motor_stroke','--plan',str(p/'operating-plan.json'),'--output',str(p/'reference-v1.json')])
 if rc:
  record('noisy_size_fullstroke_motor_path_failed',evidence=str(p),config={'observation':i},next='Geometry-aware common posture adaptation required; do not train invalid fullstroke reference');continue
 rc=run(stem+'-dense-original-motor-audit-v2',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(p/'reference-v1.json'),'--motor-plan',str(p/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(p/'motor-audit.json')]);record('noisy_size_fullstroke_geometry_screen_completed',evidence=str(p),config={'observation':i,'motor_audit_passed':rc==0},next='If original self-clearance passes, check closing/transition/table and real continuous physics before training')
