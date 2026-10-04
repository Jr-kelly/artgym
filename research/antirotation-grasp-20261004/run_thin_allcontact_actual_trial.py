"""Dense original acquisition gates for all-contact repaired thin development."""
import json,copy,time,subprocess,hashlib
from pathlib import Path
import numpy as np
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'initial-geometry-v5/thin-projected04-allcontacts';PY='/home/agiuser/miniconda3/envs/artgym/bin/python';gate=B/'jobs/thin-complete-middle-open-table-projection-v5/result.json'
while not gate.exists():time.sleep(5)
assert json.loads(gate.read_text())['exit_code']==0
def run(name,args):subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args,check=True)
p=json.loads((P/'motor-plan.json').read_text());c=copy.deepcopy(p)
for k in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:c.pop(k,None)
(P/'closure-plan.json').write_text(json.dumps(c,indent=2))
for name,args in [('acquisition',['-m','scripts.audit_wuji_actual_acquisition_motor','--plan',str(P/'motor-plan.json'),'--acquisition',str(B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json'),'--output',str(P/'acquisition-audit.json')]),('closure',['-m','scripts.audit_wuji_pickup_preload','--plan',str(P/'closure-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/'closure-audit.json')]),('transfer',['-m','scripts.audit_wuji_pickup_preload','--plan',str(P/'motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/'transfer-audit.json')])]:run('thin-allcontact-'+name+'-original-dense-v5',args)
old=B/'initial-geometry-v4/thin-projected04-complete';previous=json.loads((old/'motor-plan.json').read_text());assert np.allclose(p['wrist_in_knife'],previous['wrist_in_knife']) and np.allclose(np.asarray(p['post_lift_close_q'])[16:],np.asarray(previous['post_lift_close_q'])[16:]);ref=json.loads((old/'reference.json').read_text());ref['unchanged_thumb_motor_reuse']=dict(source=str(old/'reference.json'),sha256=hashlib.sha256((old/'reference.json').read_bytes()).hexdigest(),scope='Same issued thumb anchor and wrist geometry; changed support requires new dense original self check, not inherited collision certificate');(P/'reference.json').write_text(json.dumps(ref,indent=2))
run('thin-allcontact-full-thumb-original-dense-v5',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(P/'reference.json'),'--motor-plan',str(P/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(P/'full-motor-audit.json')])
a=json.loads((B/'jobs/actual-table-projected-size08-frozen750-load2-v19/identity.json').read_text())['command'][1:];trial=B/'continuous/actual-table-thin-allcontact-frozen750-load2-v24'
for key,value in [('--grasp-plan',P/'motor-plan.json'),('--thumb-reference-override',P/'reference.json'),('--knife-asset','assets/objects/knife_wuji_dense_under_20261003/t0001/mobility.urdf'),('--output',trial)]:a[a.index(key)+1]=str(value)
run(trial.name,a);run(trial.name+'-functional',['-m','scripts.evaluate_wuji_antirotation','--trial',str(trial)]);record('thin_allcontact_projection_actual_trial_completed',evidence=str(trial),next='Judge actual original thin acquisition/support/two loaded cycles; training geometry case, no independent generalization claim')
