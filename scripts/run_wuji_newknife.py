"""Newknife continuous35mm simulation. Uses prepared estimate-only motor path.
No robot interface; load model never enters actor. Output must be new.
"""
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--operation-prepared',type=Path,help='Certified postlift motor transfer and replacement thumb reference');p.add_argument('--checkpoint',type=Path,help='Explicit trained checkpoint; native interface checks still apply');p.add_argument('--pressure',type=Path,default=Path('runs/newknife-20261005/configs/pressure120.json'));p.add_argument('--output',type=Path,required=True);p.add_argument('--prepared',type=Path,default=Path('runs/newknife-20261005/preparation/capfront-v2'));p.add_argument('--asset',type=Path,default=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf'));p.add_argument('--resistance',type=Path,default=Path('research/newknife-20261005/resistance-constant.json'));p.add_argument('--no-video',action='store_true');a,extra=p.parse_known_args()
 assert not a.output.exists();a.output.mkdir(parents=True)
 assert json.loads((a.prepared/'full-stroke-audit.json').read_text())['all_passed']
 closure=json.loads((a.prepared/'closure-audit.json').read_text());assert closure.get('passed',closure.get('all_passed',False)),str(closure)[:300]
 selection=json.loads((R/'research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json').read_text());cmd=selection['command'][3:]
 for flag,value in [('--grasp-plan',a.prepared/'motor-plan.json'),('--table-calibration',a.prepared/'localization.json'),('--acquisition-path',a.prepared/'acquisition/acquisition-path.json'),('--handover-calibration',a.prepared/'calibration.json'),('--thumb-reference-override',a.prepared/'reference.json'),('--load',0),('--detent',0),('--output',a.output/'simulation')]:cmd[cmd.index(flag)+1]=str(value)
 loc=json.loads((a.prepared/'localization.json').read_text());cmd[cmd.index('--dx=-.1965')]='--dx='+str(loc['object_world_matrix'][0][3]-.50)
 cmd[cmd.index('--proprioceptive-pressure-config')+1]=str(a.pressure)
 if a.checkpoint:
  cmd[cmd.index('--residual-checkpoint')+1]=str(a.checkpoint)
  i=cmd.index('--thumb-residual-scale-override');del cmd[i:i+2]
  import isaacgym
  import torch
  saved=torch.load(a.checkpoint,map_location='cpu');scene=saved.get('scene_spec') or {}
  assert saved.get('public_dim')==154 and scene.get('task_stroke_m')==.035 and scene.get('newknife_resistance'), 'Checkpoint is not a declared newknife training candidate'
  if scene.get('scheduled_target_holds') and '--scheduled-target-holds' not in cmd:cmd.append('--scheduled-target-holds')
 if a.operation_prepared:
  if a.checkpoint:
   actual_geometry={f:hashlib.sha256((a.operation_prepared/f).read_bytes()).hexdigest() for f in ['postlift-transfer.json','reference.json']}
   if scene.get('operation_geometry_sha256')!=actual_geometry:
    certificate=a.operation_prepared.parent/'preparation-result.json';frozen=json.loads((R/'research/newknife-20261005/FROZEN-CANDIDATE.json').read_text());certificate_data=json.loads(certificate.read_text())
    assert str(a.checkpoint)==frozen.get('trained_checkpoint') and hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()==frozen['required_sha256'][str(a.checkpoint)], 'Only the frozen weight may use common initial-geometry adaptation'
    assert certificate_data['passed'] and certificate_data['recipe_sha256']==frozen['geometry_recipe_sha256'] and certificate_data['operation_geometry_sha256']==actual_geometry, 'Initial-geometry recipe/certificate mismatch'
  transfer=a.operation_prepared/'postlift-transfer.json';audit=a.operation_prepared/'actual-transfer-stroke-audit.json';ref=a.operation_prepared/'reference.json'
  transfer_data=json.loads(transfer.read_text());audit_data=json.loads(audit.read_text())
  assert transfer_data['preflight_passed'] and audit_data['all_passed'] and not audit_data['rate_limit_required']
  assert max(r['max_active_point_error_m'] for r in transfer_data['contact_point_tracking'])<.001
  assert hashlib.sha256(ref.read_bytes()).hexdigest()==audit_data['reference_sha256']
  motor=a.operation_prepared/'actual-transfer-motor-plan.json';assert hashlib.sha256(motor.read_bytes()).hexdigest()==audit_data['motor_plan_sha256']
  assert max(abs(x-y) for x,y in zip(json.loads(motor.read_text())['post_lift_close_q'],transfer_data['hand_q'][-1]))<1e-7
  cmd[cmd.index('--thumb-reference-override')+1]=str(ref)
  i=cmd.index('--handover-calibration');del cmd[i:i+2];cmd+=['--postlift-regrasp',str(transfer)]
 if a.no_video:cmd.remove('--video')
 cmd+=['--knife-asset',str(a.asset),'--task-stroke-m','.035','--newknife-resistance',str(a.resistance)]+extra
 checkpoint=Path(cmd[cmd.index('--residual-checkpoint')+1]);checkpoint_hash=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
 if not a.checkpoint:assert checkpoint_hash==selection['checkpoint_sha256']
 (a.output/'checkpoint-provenance.json').write_text(json.dumps(dict(path=str(checkpoint),sha256=checkpoint_hash,explicit_trained_override=bool(a.checkpoint),baseline_sha256=selection['checkpoint_sha256']),indent=2))
 (a.output/'command.json').write_text(json.dumps([sys.executable,'-m','scripts.run_g2_robust_demo']+cmd,indent=2))
 (a.output/'source-hashes.json').write_text(json.dumps({str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path('scripts/run_g2_robust_demo.py'),Path('scripts/run_wuji_newknife.py'),Path('scripts/wuji_newknife_resistance.py'),Path('scripts/g2_r800_policy.py'),Path('scripts/wuji_scheduled_thumb_reference.py'),Path('scripts/wuji_joint_deflection_pressure.py'),Path('scripts/wuji_bounded_motor_residual.py'),a.asset,a.resistance,a.pressure]+[a.prepared/f for f in ['motor-plan.json','reference.json','localization.json','calibration.json','acquisition/acquisition-path.json']]+([a.operation_prepared/'postlift-transfer.json',a.operation_prepared/'reference.json',a.operation_prepared/'actual-transfer-stroke-audit.json'] if a.operation_prepared else [])},indent=2))
 subprocess.run([sys.executable,'-m','scripts.run_g2_robust_demo']+cmd,cwd=R,check=True)
 subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_newknife','--trial',str(a.output/'simulation')],cwd=R,check=True)
if __name__=='__main__':main()
