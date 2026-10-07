"""Tilt an acquired side clamp during lift so side reactions bear gravity.

This emits motor targets only. It uses an actual recorded development clamp;
native support, table contact and the later fresh episode remain to be checked.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser()
 for name in ['source','prior','output']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--tilt-degrees',type=float,default=25.)
 p.add_argument('--tilt-start-s',type=float,default=.7)
 p.add_argument('--tilt-duration-s',type=float,default=1.3)
 a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
 s=np.load(a.source/'takeover.npz');d=json.loads(a.prior.read_text())
 k=G2Kinematics();g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
 O=transform(s['object_state'][:3],s['object_state'][3:7]);W=k.forward(s['robot_q'][:7]);pivot=O[:3,3];axis=O[:3,2]
 seed=s['issued_target'][:7].astype(float);arm_offset=seed-s['robot_q'][:7]
 F=g.w.forward(s['robot_q'][7:]);checks=[];rows=[]
 e=record('acquired_tilted_lift_geometry_start',[str(a.output)],config=dict(source=str(a.source),tilt_degrees=a.tilt_degrees,tilt_start_s=a.tilt_start_s,tilt_duration_s=a.tilt_duration_s,mechanism='Tilt toward I/M side reactions after initial clearance; same acquired load, 55g weight, original gains/physics. Reduces dependence on pure side-friction lift.'),next_step='Geometry IK/table envelope first; passing path -> native4s; actual full9cm load retention then fresh')
 for row in d['rows']:
  t=row['time_s'];angle=np.deg2rad(a.tilt_degrees)*smooth((t-a.tilt_start_s)/a.tilt_duration_s);R=Rotation.from_rotvec(axis*angle).as_matrix();goal=W.copy();goal[:3,:3]=R@W[:3,:3];goal[:3,3]=pivot+R@(W[:3,3]-pivot)+[0,0,.09*smooth(t/3.)]
  seed,ik=k.solve_near(goal,seed,max_step=.12,minimum_margin=.06)
  table=min(float((v@(goal@F[n])[:3,:3].T+(goal@F[n])[:3,3])[:,2].min()-.75)for n,parts in g.meshes.items()for v,_ in parts)
  checks.append(dict(time_s=t,angle_degrees=float(np.rad2deg(angle)),table_clearance_m=table,arm_ik=ik))
  arm_command=s['issued_target'][:7] if t==0 else seed+arm_offset
  rows.append(dict(time_s=t,arm_q=arm_command.tolist(),hand_q=row['hand_q']))
 d['rows']=rows;d.pop('development_abort_on_translation_m',None);d['source']=str(a.source);d['scope']=__doc__;d['tilted_lift']=dict(degrees=a.tilt_degrees,start_s=a.tilt_start_s,duration_s=a.tilt_duration_s,axis_knife=[0,0,1]);d['geometry_checks']=checks
 initial=checks[0]['table_clearance_m'];guard=dict(max_ik_position_error_m=max(x['arm_ik']['position_m']for x in checks),max_ik_rotation_error_rad=max(x['arm_ik']['rotation_rad']for x in checks),minimum_table_clearance_m=min(x['table_clearance_m']for x in checks),initial_actual_geometry_table_clearance_m=initial,source_jump_rad=float(np.max(abs(np.array(rows[0]['arm_q'])-s['issued_target'][:7]))))
 guard['permits_native']=guard['max_ik_position_error_m']<.0001 and guard['max_ik_rotation_error_rad']<.001 and guard['minimum_table_clearance_m']>=min(initial,0)-.0001 and guard['source_jump_rad']<.0001
 d['guard']=guard;(a.output/'motor.json').write_text(json.dumps(d,indent=2));print(json.dumps(guard))
 e=record('acquired_tilted_lift_geometry_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing tilt lift -> native4s actual9cm lift/support/table; failed changes motion timing by actual geometric obstruction')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a')as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(guard)+'\n')
 if not guard['permits_native']:raise SystemExit(2)

if __name__=='__main__':main()
