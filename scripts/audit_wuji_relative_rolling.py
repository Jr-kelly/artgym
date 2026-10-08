"""Recorded development carry/relative-grip measurement, never fresh-goal acceptance."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.check_wuji_action_quality import run
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();command=json.loads((a.trial/'command.json').read_text());stroke=float(command[command.index('--task-stroke-m')+1])if '--task-stroke-m'in command else .03
 for flag in ['--recorded-support-command','--flat-table-prefix']:
  if flag in command:
   metadata=json.loads(Path(command[command.index(flag)+1]).read_text());stroke=float(metadata.get('retained_push_skill',{}).get('task_stroke_m',stroke))
 z=np.load(a.trial/'simulation/trace.npz');k=G2Kinematics();X=np.array([np.linalg.inv(transform(o[:3],o[3:7]))@k.forward(q)for o,q in zip(z['object'],z['arm_q'])]);relative=Rotation.from_matrix(X[:,:3,:3]@X[0,:3,:3].T).as_rotvec()*180/np.pi;body_rotation=(Rotation.from_quat(z['object'][0,3:7]).inv()*Rotation.from_quat(z['object'][:,3:7])).magnitude()*180/np.pi;H=run(a.trial/'simulation',a.trial/'actual-action-quality.json',1);f=FunctionalEntryAffordance(task_stroke_m=stroke);clearance=[]
 for o,s in zip(z['object'],z['slider']):
  O=transform(o[:3],o[3:7]);V=np.concatenate([p['vertices']for p in f.g.knife_geometry.collision_parts(float(s))]);clearance.append(float((V@O[:3,:3].T+O[:3,3])[:,2].min()-.75))
 prior=np.load('runs/flat-table-20261006/direct/development/ideal-tail-30mm-fullB-v773/simulation/trace.npz');G=np.linalg.inv(transform(prior['object'][119,:3],prior['object'][119,3:7]))@k.forward(prior['arm_q'][119]);goal_error=Rotation.from_matrix(G[:3,:3]@np.transpose(X[:,:3,:3],(0,2,1))).magnitude()*180/np.pi;r=dict(frames=len(X),duration_s=len(X)/30,body_position_max_m=float(np.linalg.norm(z['object'][:,:3]-z['object'][0,:3],axis=1).max()),body_rotation_max_deg=float(body_rotation.max()),relative_yaw_end_deg=float(relative[-1,2]),relative_yaw_min_deg=float(relative[:,2].min()),relative_translation_max_m=float(np.linalg.norm(X[:,:3,3]-X[0,:3,3],axis=1).max()),operating_goal_orientation_error_start_deg=float(goal_error[0]),operating_goal_orientation_error_end_deg=float(goal_error[-1]),all_actual_H_bad=H['affected_pair_intersection_frames'],whole_knife_clearance_min_m=min(clearance),final_contacts=z['finger_body_contacts'][-1].tolist(),last1s_contact_frames=(z['finger_body_contacts'][-30:]>0).sum(0).tolist(),earlystop=json.loads((a.trial/'simulation/development-early-stop.json').read_text()) if (a.trial/'simulation/development-early-stop.json').exists() else None,affordance=f.assess_relative(X[-1],z['q'][-1].astype(float),float(z['slider'][-1])),scope=__doc__);(a.trial/'rolling-result.json').write_text(json.dumps(r,indent=2));record('actual_short_relative_rolling_audit',[str(a.trial/'rolling-result.json'),str(a.trial/'actual-action-quality.json')],r,next_step='Carry+substantialrelativeprogress only->extendtowardproven773; actualnewbearingfirst beforeoldclampwithdrawal');print(json.dumps(r))
if __name__=='__main__':main()
