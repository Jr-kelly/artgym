"""One bounded thumb contact-placement candidate, not a grasp/gain sweep."""
import json,pathlib,numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.plan_wuji_braced_support import plan,staged_transfer
from scripts.record_wuji_support_goal import record,R,D
B=R/'runs/support-pressure-20261003';old=R/'research/robust-knife-family-20261003';out=B/'thumb-positive1-config-v122';rows=[]
record('thumb_positive1_contact_v122_planning_started',config={'thumb_contact_bias_m':[.001,0,0],'cases':['nominal','raised1']},conclusion='One opposite-side contactplacement to earliernegative2mm candidate; preserve stagedsupport, no force/posefeedback, motorlimits/material/load/criteria unchanged. Normalmoment model doesnotestablish totalfrictionwrench, so geometrycandidate notcausalproof.',next='Keep planningfailures; only twoactual36s cases if full40mm IKfeasible')
for label in ['nominal','raised1']:
 folder=out/label;folder.mkdir(parents=True,exist_ok=False);estimate=json.loads((B/'pressure-config-v35'/label/'motor-plan.json').read_text())['initial_geometry_estimate']
 motor,support,reference,audit=adapt(estimate,json.loads((old/'functional-side-edge-under-support-equilibrium-v6/motor-plan.json').read_text()),json.loads((D/'coordinated-preload-moderate-v6.json').read_text()),json.loads((old/'functional-side-edge-under-support-v6/continuous-thumb-v2.json').read_text()),thumb_contact_bias_m=[.001,0,0])
 original=support
 try:
  assert reference['all_feasible'],'Full40mm thumbIK outside.25mm accuracy'
  brace,reference=plan(motor,support,reference,folder/'brace',old/'functional-side-edge-under-support-v6/localization.json');support=staged_transfer(motor,original,brace)
  for name,value in [('motor-plan.json',motor),('support.json',support),('reference.json',reference),('audit.json',audit)]: (folder/name).write_text(json.dumps(value,indent=2))
  rows.append(dict(label=label,passed=True,thumb_max_IK_error_m=audit['trajectory_max_error_m']))
 except (AssertionError,ValueError) as error:rows.append(dict(label=label,passed=False,error=str(error),audit=audit))
p=D/'thumb-positive1-preparation-v122.json';p.write_text(json.dumps(rows,indent=2));record('thumb_positive1_contact_v122_planning_closed',evidence=str(p.relative_to(R)),config={'results':rows},conclusion='Planningaccuracy/jointlimits only, notphysicalcontact guarantee',next='Two completephysicalcases withoriginalstrong750 ifplanningpassed');print(json.dumps(rows))
