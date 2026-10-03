"""One publicgeometry leverage candidate, not a pose/force feedback scheme."""
import json,pathlib,time
from scripts.plan_wuji_braced_support import plan,staged_transfer
from scripts.record_wuji_support_goal import record,R,D
B=R/'runs/support-pressure-20261003';dest=B/'quarterwidth-support-config-v99'
record('quarterwidth_support_v99_preparation_started',config={'anchors_fraction_of_estimated_width':[.25,.20]},conclusion='Sequentialpath restored loaded strokes but actualsupport contacts migrate toward originaledge duringoperation. Test one mechanicallylarger opposite-side lever frompublicwidth, no truthcompensation/forceincrease, oldpickup/thumb/limits retained.',next='Prepare two plans; reject infeasible originals withoutfiltering; actualcontinuous trials needed')
rows=[]
for label in ['nominal','raised1']:
 source=B/'pressure-config-v35'/label
 motor=json.loads((source/'motor-plan.json').read_text());support=json.loads((source/'support.json').read_text());reference=json.loads((source/'reference.json').read_text());width=motor['initial_geometry_estimate']['handle_size_WTL_m'][0]
 folder=dest/label;folder.mkdir(parents=True,exist_ok=False)
 try:
  brace,ref=plan(motor,support,reference,folder/'brace',R/'research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json',brace_x_m=(width*.25,width*.20))
  stage=staged_transfer(motor,support,brace)
  (folder/'support.json').write_text(json.dumps(stage,indent=2));(folder/'reference.json').write_text(json.dumps(ref,indent=2));rows.append(dict(label=label,planning_passed=True,anchors_m=[width*.25,width*.20]))
 except (AssertionError,ValueError) as e:rows.append(dict(label=label,planning_passed=False,error=str(e),anchors_m=[width*.25,width*.20]))
(D/'quarterwidth-support-preparation-v99.json').write_text(json.dumps(rows,indent=2))
record('quarterwidth_support_v99_preparation_closed',evidence=str((D/'quarterwidth-support-preparation-v99.json').relative_to(R)),config={'rows':rows},conclusion='Public IK/staticwrench/planner only, not physicalcontact or behaviorcertificate',next='Actual matched TABLE attempts for feasibleplans, retainfailedplanningreceipts')
