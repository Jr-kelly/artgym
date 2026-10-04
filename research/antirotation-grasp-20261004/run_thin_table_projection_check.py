"""Repair one rejected train geometry, preserving failures and original gates."""
import json,copy,subprocess
from pathlib import Path
from scripts.record_wuji_antirotation_goal import record
B=Path('runs/antirotation-grasp-20261004');P=B/'initial-geometry-v3/thin-projected04-reserve';PY='/home/agiuser/miniconda3/envs/artgym/bin/python'
def run(name,args,required=True):
 r=subprocess.run([PY,'-m','scripts.run_wuji_antirotation_job','--name',name,'--',PY]+args);assert r.returncode==0 or not required;return r.returncode
run('thin-table-motor-projection-reserve-v2',['-m','scripts.project_wuji_estimated_table_preload','--plan',str(B/'initial-geometry-v2/projected-04/motor-plan.json'),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/'motor-plan.json')])
p=json.loads((P/'motor-plan.json').read_text());c=copy.deepcopy(p)
for k in ['post_lift_preload_seconds','post_lift_close_q','lift_preload_height_m']:c.pop(k,None)
(P/'closure-plan.json').write_text(json.dumps(c,indent=2))
for name,plan in [('closure','closure-plan.json'),('transfer','motor-plan.json')]:
 run('thin-repaired-'+name+'-dense-audit-v3',['-m','scripts.audit_wuji_pickup_preload','--plan',str(P/plan),'--localization',str(B/'pickup-plans-v1/opposed/localization.json'),'--output',str(P/(name+'-audit.json'))])
op=json.loads((B/'initial-geometry-v2/projected-04/operating-plan.json').read_text());op['close_q']=p['post_lift_close_q'];(P/'operating-plan.json').write_text(json.dumps(op,indent=2))
run('thin-repaired-direct-motor-path-v3',['-m','scripts.plan_g2_direct_thumb_motor_stroke','--plan',str(P/'operating-plan.json'),'--output',str(P/'reference.json')])
run('thin-repaired-full-motor-dense-audit-v3',['-m','scripts.audit_g2_anchored_thumb_motor','--reference',str(P/'reference.json'),'--motor-plan',str(P/'motor-plan.json'),'--knife-spec','research/robust-knife-family-20261003/real-knife-asset-spec.json','--samples','161','--output',str(P/'full-motor-audit.json')])
record('thin_estimated_geometry_original_dense_projection_checked',evidence=str(P),config={'planning_table_reserve_mm':.5,'unchanged_acceptance_mm':.3},next='Validate changed original open/approach path before actual geometry trial; no certificate inherited from nominal')
