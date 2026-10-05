"""Reuse immutable expensive pickup/contact plans, complete preload and transfer."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--track-index-clearance',action='store_true');p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False)
for n in ['pickup','planning','reference']:shutil.copytree(a.base/n,out/n)
def run(m,**kw):
 c=[sys.executable,'-m','scripts.'+m]
 for k,v in kw.items():
  if v is False:continue
  c+=['--'+k.replace('_','-')]
  if v is not True:c+=[str(v)]
 with (out/(m+'.log')).open('w') as f:subprocess.run(c,stdout=f,stderr=subprocess.STDOUT,check=True)
op=out/'operation';pickup=out/'pickup'
try:
 run('prepare_wuji_contact_support_preload',preload_aware_reserve=True,base=out/'reference',actuator_spec='runs/newknife-20261005/configs/actuator-preload-model.json',output=op)
 run('plan_wuji_contact_transfer_regrasp',resolve_index_middle=a.track_index_clearance,knife_spec=op/'estimated-collision/spec.json',table_y=-.23,pickup_plan=pickup/'motor-plan.json',acquisition=pickup/'acquisition/acquisition-path.json',calibration=pickup/'calibration.json',operation_plan=op/'motor-plan.json',contact_preserving_ik=True,reachable_pinky_path=True,output=op/'postlift-transfer.json')
 t=json.loads((op/'postlift-transfer.json').read_text());assert t['preflight_passed'] and max(x['max_active_point_error_m'] for x in t['contact_point_tracking'])<.001
 m=json.loads((op/'motor-plan.json').read_text());m['post_lift_close_q']=t['hand_q'][-1];(op/'actual-transfer-motor-plan.json').write_text(json.dumps(m,indent=2))
 run('audit_g2_anchored_thumb_motor',reference=op/'reference.json',motor_plan=op/'actual-transfer-motor-plan.json',knife_spec=op/'estimated-collision/spec.json',samples=81,output=op/'actual-transfer-stroke-audit.json')
 cert=json.loads((op/'actual-transfer-stroke-audit.json').read_text());assert cert['all_passed'] and not cert['rate_limit_required'];result=dict(passed=True,prepared=str(pickup),operation_prepared=str(op),stroke_m=json.loads((op/'reference.json').read_text())['command_travel_m'])
except Exception as e:
 (out/'preparation-result.json').write_text(json.dumps(dict(passed=False,error=str(e)),indent=2));raise
(out/'preparation-result.json').write_text(json.dumps(result,indent=2))
