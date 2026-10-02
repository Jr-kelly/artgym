"""Offline frozen R800 replay of actually executed scripted G2 commands.

Only measured q/FK, actual50-frame q/action history, known issued targets, arm FK
and a once-loaded prior calibration enter the154 actor features. Recorded live
object/slider/contact columns are deliberately never read. This prepares labels;
it does not fit a model or establish fresh physics/generalization success.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.wuji_goal_common import configuration
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_robust_learning import R800,TEACHER
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--demo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--interface-checkpoint',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 z=np.load(a.demo/'trace.npz');plan=json.loads((a.demo/'plan.json').read_text());cal=plan['handover_calibration'];assert cal and plan['args']['thumb_script'];hand=json.loads((a.demo/'physics.json').read_text())['hand_indices'];cfg=configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator','+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
 policy=G2R800Policy(cfg,TEACHER,R800,residual_checkpoint=a.interface_checkpoint);kin=G2Kinematics();rows=[];targets=[];times=[];err=0.;previous=np.zeros(20,dtype=np.float32);taken=False
 for i in range(1,len(z['time'])):
  q=z['q'][i-1];t=i/30.;policy.record(q,previous if taken else np.zeros(20,dtype=np.float32))
  if i<480:continue
  if not taken:
   policy.takeover_estimate(q,z['target'][i-1,hand],np.array(cal['object_in_wrist']),np.array(cal['slider_in_wrist']));taken=True
  issued=policy.known.issued.clone();goal=.04 if ((i-480)//150)%2==0 else 0.;policy.command(q,goal,wrist_gravity=kin.forward(z['arm_q'][i-1])[:3,:3].T@np.array([0.,0.,-1.]))
  rows.append(policy.last_public_features.copy());teacher=z['action'][i].copy();targets.append(teacher);times.append(t);policy.known.issued[:]=issued;motor=policy.known.step(policy.tensor(teacher))[0].cpu().numpy();err=max(err,float(abs(motor-z['target'][i,hand]).max()));policy.last_action=teacher;previous=teacher
 x=np.array(rows);y=np.array(targets);assert x.shape==(600,154) and y.shape==(600,20);assert err<2e-6,err
 np.savez_compressed(a.output/'legal-demonstration.npz',public=x,executed_action=y,control_time_s=np.array(times),train=np.array(times)<26.,validation=np.array(times)>=26.)
 receipt=dict(source_demo=str(a.demo),source_trace_sha256=hashlib.sha256((a.demo/'trace.npz').read_bytes()).hexdigest(),prior_calibration=cal,interface_checkpoint_sha256=hashlib.sha256(a.interface_checkpoint.read_bytes()).hexdigest(),teacher_sha256=hashlib.sha256(TEACHER.read_bytes()).hexdigest(),student_sha256=hashlib.sha256(R800.read_bytes()).hexdigest(),frames=len(x),public_dim=154,max_reconstructed_motor_target_error_rad=err,split='first actual cycle16-26 for fitting; second26-36 offline repeat-cycle validation, not independent physics or geometry',live_truth_columns_read=False,scope='Legal deployable features replayed from actual script, body rotation~31deg unresolved in source; learned behavior bootstrap evidence only')
 (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
