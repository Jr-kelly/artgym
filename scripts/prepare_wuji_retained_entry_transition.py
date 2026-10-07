"""One in-hand reference from an actual carried state to a proven push entrance.

The knife is held fixed only in offline kinematic planning. Native execution
must preserve its freely simulated pose. This reference is also a short-course
learning guide if contact migration defeats the nominal motor trajectory.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--entrance',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=6.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    record('retained_entry_transition_reference_started',[str(a.source),str(a.entrance)],
           {'uncertainty':'Does a wrist/whole-hand reference connect this actual carrying state to the proven push entry without hand or table collision?',
            'control':'27 motor coordinates; original limits; no static contact bias; reference only'},next_step='Clear path -> native contact-transfer test; blocked interpolation -> contact-aware short learning reference')
    z=np.load(a.source/'takeover.npz');target=json.loads(a.entrance.read_text());k=G2Kinematics();H=HandIntersection();g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')
    O=transform(z['object_state'][:3],z['object_state'][3:7]);W0=k.forward(z['robot_q'][:7]);L1=np.linalg.inv(np.asarray(target['object_in_wrist_actual']))
    W1=O@L1;rot=Slerp([0,1],Rotation.from_matrix([W0[:3,:3],W1[:3,:3]]));q0=z['robot_q'][7:].copy();q1=np.asarray(target['hand_q']);arm=z['robot_q'][:7].copy()
    # Retain current measured-to-issued loading once; no integrated bias.
    load=z['issued_target'][7:27]-q0;goal_load=np.asarray(target['issued_hand_target'])-q1
    rows=[];audit=[];begin=time.monotonic()
    for i in range(round(a.seconds*30)+1):
        t=i/30;u=t/a.seconds;f=u**3*(10-15*u+6*u*u)
        W=W0.copy();W[:3,:3]=rot(f).as_matrix();W[:3,3]=(1-f)*W0[:3,3]+f*W1[:3,3]
        arm,ik=k.solve_near(W,arm,max_step=.12);q=(1-f)*q0+f*q1;motor=q+(1-f)*load+f*goal_load
        motor=np.clip(motor,g.w.lower,g.w.upper)
        rows.append({'time_s':t,'arm_q':arm.tolist(),'hand_q':motor.tolist()})
        if i%6==0 or i==round(a.seconds*30):
            F=g.w.forward(q);clear=min(float((v@(k.forward(arm)@F[n])[:3,:3].T+(k.forward(arm)@F[n])[:3,3])[:,2].min()-.75) for n,meshes in g.meshes.items() for v,_ in meshes)
            audit.append({'time_s':t,'self':H.inspect(q),'floor_m':clear,'ik':ik})
    result={'required_actual_source':str(a.source),'rows':rows,'retained_push_skill':{'start_s':a.seconds,'preparation_seconds':4.,'knife_spec':'assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'},
            'entry_source':str(a.entrance),'entry_sha256':hashlib.sha256(a.entrance.read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256((a.source/'takeover.npz').read_bytes()).hexdigest(),
            'scope':__doc__,'target_hand_q':q1.tolist(),'target_object_in_wrist':target['object_in_wrist_actual']}
    (a.output/'motor.json').write_text(json.dumps(result,indent=2));(a.output/'geometry.json').write_text(json.dumps(audit,indent=2))
    summary={'sampled_frames':len(audit),'self_frames':sum(bool(x['self']) for x in audit),'minimum_hand_floor_m':min(x['floor_m'] for x in audit),
             'max_ik_position_m':max(x['ik']['position_m'] for x in audit),'max_ik_rotation_rad':max(x['ik']['rotation_rad'] for x in audit),'elapsed_s':time.monotonic()-begin,
             'scope':'Nominal measured-posture reference screening; physical bearing transfer and motor deflection still unverified'}
    (a.output/'result.json').write_text(json.dumps(summary,indent=2));record('retained_entry_transition_reference_terminal',[str(a.output/'motor.json'),str(a.output/'geometry.json')],summary,
        next_step='Use exact collision/IK bottleneck to shape a contact-changing short policy; do not test a known invalid static interpolation')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
