"""Offline motor interface parity; does not launch a physics execution."""
import argparse,json
from pathlib import Path
from scripts.g2_v2_grip_runtime import GripPolicyRuntime
import numpy as np
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--update',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 prefix=np.load(a.run/('prefix-end-%05d.npz'%a.update));frames=np.load(a.run/('eval-%05d.npz'%a.update));meta=json.loads(Path('configs/g2_functional_v2/grip-prefix-v2/physics.json').read_text())
 policy=GripPolicyRuntime(a.run/('checkpoint-%05d.pth'%a.update),meta,prefix['all_dof_position'][0],prefix['dof_velocity'][0],prefix['reference_targets'][0],prefix['wrist'][0],prefix['object_rigid_state'][0],prefix['slider_rigid_state'][0]);errors=[]
 for i in range(len(frames['time'])):
  x={k:prefix[k][0] if i==0 else frames[k][i-1,0] for k in ['all_dof_position','dof_velocity','wrist','object_rigid_state','slider_rigid_state']}
  q=policy.step(x['all_dof_position'],x['dof_velocity'],x['wrist'],x['object_rigid_state'],x['slider_rigid_state']);errors.append(float(np.max(abs(q-frames['reference_targets'][i,0,7:27]))))
 report=dict(scope='Offline124D/action mapping replay from actual logged prefix end and subsequent states; no physical execution',frames=len(errors),motor_max_difference_rad=max(errors),first_difference_rad=errors[0],success=max(errors)<1e-6,checkpoint=policy.description())
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert report['success']
if __name__=='__main__':main()
