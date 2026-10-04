"""One original-asset held diagnostic case for a matched adaptation comparison.

Actor receives measured joints, issued history and a fixed source-matched
initial estimate. No runtime object/contact/force feedback. Not a pickup demo.
"""
import argparse,json,sys,subprocess,hashlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--scene',type=Path,required=True);p.add_argument('--source',type=int,choices=[1,2],required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--load',type=float,default=.2);p.add_argument('--detent',type=float,default=.2);p.add_argument('--additional-load',type=float,default=0.);p.add_argument('--profile',choices=['constant','pulse'],default='constant');p.add_argument('--seed',type=int,default=2026100419);p.add_argument('--joint-noise',type=float,default=0.);p.add_argument('--joint-bias',type=float,default=0.);p.add_argument('--video',action='store_true');p.add_argument('--pressure-config',type=Path,help='Legal joint/issuedtarget model-based pressureadapter, notactualforcefeedback');p.add_argument('--knife-asset',type=Path,help='Simulator loading only, never actor input');a=p.parse_args();s=json.loads(a.scene.read_text());row=next(r for r in s['initial_estimated_plans'] if r['selection_source']==a.source);inputs=a.output.parent/(a.output.name+'-inputs');inputs.mkdir(parents=True,exist_ok=False)
 data={'motor-plan.json':row['motor_plan'],'reference.json':row['thumb_reference'],'calibration.json':row['calibration'],'arm-seed.json':{'q':row['held_arm_q']}}
 # Native arm seed field is inherited from a validated source-specific receipt.
 root=Path(__file__).resolve().parents[1];base=root/'runs/wrap-force-20261004/comparison/four-sources-v1'/('source%d'%a.source);arm=json.loads((base/'arm-seed.json').read_text());data['arm-seed.json']=arm
 for name,value in data.items():(inputs/name).write_text(json.dumps(value,indent=2)+'\n')
 cmd=[sys.executable,'-m','scripts.run_g2_robust_demo','--output',str(a.output),'--grasp-plan',str(inputs/'motor-plan.json'),'--table-calibration',str(base/'localization.json'),'--arm-seed',str(inputs/'arm-seed.json'),'--handover-calibration',str(inputs/'calibration.json'),'--thumb-reference-override',str(inputs/'reference.json'),'--residual-checkpoint',str(a.checkpoint),'--held-diagnostic','--dx=-.1985','--dy=.05','--load',str(a.load),'--detent',str(a.detent),'--load-profile',a.profile,'--hand-friction','.8','--knife-friction','1.8','--resistance-integration','solver-brake','--wrap-contact-measurement','--seed',str(a.seed),'--observation-noise',str(a.joint_noise),'--observation-bias',str(a.joint_bias)]
 if a.pressure_config:cmd+=['--proprioceptive-pressure-config',str(a.pressure_config)]
 if a.knife_asset:cmd+=['--knife-asset',str(a.knife_asset)]
 if a.additional_load:cmd+=['--opposing-axial-test-load',str(a.additional_load)]
 if a.video:cmd+=['--video']
 (inputs/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');subprocess.run(cmd,check=True);subprocess.run([sys.executable,'-m','scripts.evaluate_wuji_antirotation','--trial',str(a.output)],check=True);subprocess.run([sys.executable,'-m','scripts.analyze_wuji_wrap_contacts','--trial',str(a.output)],check=True)
 (a.output/'paired-case-role.json').write_text(json.dumps(dict(scope=__doc__,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),source=a.source,scene_sha256=hashlib.sha256(a.scene.read_bytes()).hexdigest(),held_diagnostic=True,continuous_pickup_demo_pass=False,additional_load_kind='Known balanced countercommand test load, not measured thumb force' if a.additional_load else None),indent=2)+'\n')
if __name__=='__main__':main()
