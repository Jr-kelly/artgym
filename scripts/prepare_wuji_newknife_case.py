"""Common initial-estimate-only preparation; no physical asset or load ID input.
Every failed geometry gate is retained. Does not execute a physical rollout.
"""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--estimate',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True);recipe=json.loads(a.recipe.read_text());commands=[]
 def run(module,**kw):
  cmd=[sys.executable,'-m','scripts.'+module]
  for key,value in kw.items():
   if value is False or value is None:continue
   cmd+=['--'+key.replace('_','-')]
   if value is not True:cmd.append(str(value))
  commands.append(cmd);(a.output/'commands.json').write_text(json.dumps(commands,indent=2))
  with (a.output/(str(len(commands)).zfill(2)+'-'+module+'.log')).open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 pickup=a.output/'pickup';planning=a.output/'planning';refprep=a.output/'reference';operation=a.output/'operation'
 try:
  run('adapt_wuji_direct_corner_initial_geometry',estimate=a.estimate,plan=recipe['baseline_plan'],reference=recipe['baseline_reference'],localization=recipe['baseline_localization'],output=pickup,body_root_inset=.01,grip_tail_shift_m=.006,preserve_middle_axis=True,thumb_lateral_bias_m=.0025,thumb_face_toward_cap=True)
  ref=json.loads((pickup/'reference.json').read_text());ref['command_travel_m']=.035;(pickup/'reference.json').write_text(json.dumps(ref,indent=2))
  run('plan_g2_functional_acquisition_path',plan=pickup/'motor-plan.json',localization=pickup/'localization.json',knife_spec=pickup/'estimated-collision/spec.json',table_y=-.23,output=pickup/'acquisition')
  run('audit_wuji_actual_acquisition_motor',plan=pickup/'motor-plan.json',acquisition=pickup/'acquisition/acquisition-path.json',table_y=-.23,output=pickup/'closure-audit.json')
  run('audit_g2_anchored_thumb_motor',reference=pickup/'reference.json',motor_plan=pickup/'motor-plan.json',knife_spec=pickup/'estimated-collision/spec.json',samples=81,output=pickup/'full-stroke-audit.json')
  run('plan_wuji_newknife_contact_pose',base=pickup,initialize=recipe['nominal_operation_seed'],fixed_wrist_from_initialize=True,smooth=True,small_wrist=True,minimum_front_cosine=.5,middle_support_crosswidth_fraction=.22,pinky_support_crosswidth_fraction=0,sites=12,output=planning)
  run('prepare_wuji_newknife_joint_pose',pose=planning,base=pickup,continuous=True,lifted_operation=True,thumb_preload_normal_m=.0003,preserve_authored_normal=True,output=refprep)
  run('prepare_wuji_newknife_support_preload',base=refprep,actuator_spec=recipe['actuator_spec'],output=operation)
  run('plan_wuji_postlift_regrasp',knife_spec=operation/'estimated-collision/spec.json',table_y=-.23,pickup_plan=pickup/'motor-plan.json',acquisition=pickup/'acquisition/acquisition-path.json',calibration=pickup/'calibration.json',operation_plan=operation/'motor-plan.json',contact_preserving_ik=True,reachable_pinky_path=True,output=operation/'postlift-transfer.json')
  transfer=json.loads((operation/'postlift-transfer.json').read_text());assert transfer['preflight_passed'] and max(r['max_active_point_error_m'] for r in transfer['contact_point_tracking'])<.001
  motor=json.loads((operation/'motor-plan.json').read_text());motor['post_lift_close_q']=transfer['hand_q'][-1];(operation/'actual-transfer-motor-plan.json').write_text(json.dumps(motor,indent=2))
  run('audit_g2_anchored_thumb_motor',reference=operation/'reference.json',motor_plan=operation/'actual-transfer-motor-plan.json',knife_spec=operation/'estimated-collision/spec.json',samples=81,output=operation/'actual-transfer-stroke-audit.json')
  audit=json.loads((operation/'actual-transfer-stroke-audit.json').read_text());assert audit['all_passed'] and not audit['rate_limit_required']
  result=dict(passed=True,scope=__doc__,recipe_sha256=hashlib.sha256(a.recipe.read_bytes()).hexdigest(),estimate_sha256=hashlib.sha256(a.estimate.read_bytes()).hexdigest(),prepared=str(pickup),operation_prepared=str(operation),operation_geometry_sha256={f:hashlib.sha256((operation/f).read_bytes()).hexdigest() for f in ['postlift-transfer.json','reference.json']})
 except Exception as error:
  (a.output/'preparation-result.json').write_text(json.dumps(dict(passed=False,scope=__doc__,failure_type=type(error).__name__,failure=str(error),commands=commands),indent=2));raise
 (a.output/'preparation-result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
