"""Align the carried knife's slider-side normal upward before releasing the side clamp.

Only motor commands. A rigid-pose IK guide is not actual load-transfer evidence.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform,minimal_alignment
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=4);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 z=np.load(Path(a.source)/'takeover.npz');q=z['robot_q'].astype(float);issued=z['issued_target'].astype(float);k=G2Kinematics();W=k.forward(q[:7]);O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@W;rotation=minimal_alignment(O[:3,1],[0,0,1]);angle=Rotation.from_matrix(rotation).as_rotvec();rows=[dict(time_s=0.,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())];errors=[];arm=q[:7].copy();offset=issued[:7]-arm
 for i in range(1,int(round(a.seconds*30))+1):
  u=i/(a.seconds*30);f=10*u**3-15*u**4+6*u**5;target=O.copy();target[:3,:3]=Rotation.from_rotvec(angle*f).as_matrix()@O[:3,:3];arm,err=k.solve_near(target@L,arm,max_step=.08,minimum_margin=.01);assert err['position_m']<.0002 and err['rotation_rad']<.002,err;errors.append(err);motor=arm+offset;prev=np.array(rows[-1]['arm_q']);motor=np.clip(motor,prev-.006,prev+.006);rows.append(dict(time_s=i/30,arm_q=motor.tolist(),hand_q=issued[7:].tolist()))
 final_pose=k.forward(np.array(rows[-1]['arm_q'])-offset)@np.linalg.inv(L);out={'required_actual_source':a.source,'development_abort_on_translation_m':.10,'rows':rows,'scope':__doc__,'planned_initial_normal_world':O[:3,1].tolist(),'planned_final_normal_world':final_pose[:3,1].tolist(),'planned_rotation_deg':float(np.linalg.norm(angle)*180/np.pi),'arm_servo_slew_max_rad':float(abs(np.diff([r['arm_q'] for r in rows],axis=0)).max())};(a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'}));record('gravity_supported_transfer_motor_prepared',[str(a.output/'motor.json')],{k:v for k,v in out.items() if k!='rows'},next_step='Native arm alignment with oldgrip retained; if carryingstable, free thumb towardprovenfunctional cap thenfull B; otherwise revise front grip')
if __name__=='__main__':main()
