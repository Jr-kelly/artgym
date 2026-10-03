"""One larger underside reaction-lever layout on known development estimates.

Not selected from frozen independent results. Existing nominal development
movie already showed sustained thumb pressure and body roll before validation.
"""
import json,pathlib
from scripts.plan_wuji_braced_support import plan,staged_transfer
from scripts.record_wuji_support_goal import record
R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003'
record('opposite_edge_support_v146_planning_started',config={'known_development_cases':['nominal','raised1'],'index_middle_target_x_m':[.006,.004]},conclusion='One physicallydifferent largeroppositeunderside reactionlever based on earlierdevelopmentbodyroll; not independentresulttuning. Frozen750/staged deliverycandidate unchanged.',next='IK/staticplanning/URDFvelocity first; atmost2 actualcontinuousdevelopmentchecks, no automaticunchangedlongtraining.')
rows=[]
for label in ['nominal','raised1']:
 old=B/'pressure-config-v35'/label;output=B/'opposite-edge-support-config-v146'/label;output.mkdir(parents=True,exist_ok=False)
 motor,support,reference=[json.loads((old/name).read_text()) for name in ['motor-plan.json','support.json','reference.json']]
 try:
  braced,ref=plan(motor,support,reference,output/'plan',R/'research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json',brace_x_m=(.006,.004))
  stage=staged_transfer(motor,support,braced)
  (output/'support.json').write_text(json.dumps(stage,indent=2));(output/'reference.json').write_text(json.dumps(ref,indent=2));row=dict(label=label,planning_pass=True,audit=stage['support_brace_audit'])
 except (AssertionError,ValueError) as e:
  row=dict(label=label,planning_pass=False,error=str(e));(output/'failure.json').write_text(json.dumps(row,indent=2))
 rows.append(row)
 record('opposite_edge_support_v146_one_planning_closed',evidence=str(output.relative_to(R)),config=row,next='Runphysicalcomparison onlyifcompletepublicestimateplanning andmotorvelocity feasible; preservefailures.')
(R/'research/support-pressure-20261003/opposite-edge-support-v146-planning.json').write_text(json.dumps(dict(entries=rows,scope='Known development inputs only; no controllerselection from independentcases, unchangedgravity/collisions/fullstroke'),indent=2));print(json.dumps(rows))
