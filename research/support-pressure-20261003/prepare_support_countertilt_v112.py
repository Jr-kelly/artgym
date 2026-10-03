import json,pathlib
from scripts.plan_wuji_support_countertilt import plan
from scripts.record_wuji_support_goal import record,R,D
B=R/'runs/support-pressure-20261003';out=B/'support-countertilt-config-v112';rows=[]
record('support_countertilt_v112_preparation_started',config={'degrees':-4,'knownstroke_m':.04},conclusion='Stagednominal developmentpeak rotation is predominantly positiveknifeZ (.333/.350rad); test boundedopposite supportgeometry tilt, not fullwrist twist or loadretentionfeedback. No physicalrange enlargement or currenttruthcontrol.',next='Only run if complete40mm IKcurve fitsoriginalsupportspan/limits; retainplanningfailures')
for label in ['nominal','raised1']:
 folder=out/label;folder.mkdir(parents=True,exist_ok=False);motor=json.loads((B/'pressure-config-v35'/label/'motor-plan.json').read_text());support=json.loads((B/'staged-brace-config-v86'/label/'support.json').read_text());reference=json.loads((B/'staged-brace-config-v86'/label/'reference.json').read_text())
 try:
  ref=plan(motor,support,reference,degrees=-4.);(folder/'reference.json').write_text(json.dumps(ref,indent=2));(folder/'support.json').write_text(json.dumps(support,indent=2));rows.append(dict(label=label,plan_passed=True,max_offset_rad=max(v['max_motor_offset_rad'] for v in ref['support_countertilt']['rows'])))
 except (AssertionError,ValueError) as e:rows.append(dict(label=label,plan_passed=False,error=str(e)))
p=D/'support-countertilt-preparation-v112.json';p.write_text(json.dumps(rows,indent=2));record('support_countertilt_v112_preparation_closed',evidence=str(p.relative_to(R)),config={'rows':rows},conclusion='Static IK/actionspan only, no contactcertificate',next='Two completephysical episodes if feasible, no trajectorysize or endpointcriteria changes');print(json.dumps(rows))
