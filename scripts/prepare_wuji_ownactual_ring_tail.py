"""Bind a fitted tail to its own measured carrying state and issued targets.

Coordinate transforms adapt motor references only. They never assign object
pose, contact states or success-record control history to the native episode.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--knots',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reference-start',type=float,default=2.)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);m=json.loads(a.base.read_text());kn=json.loads(a.knots.read_text());z=np.load(a.source/'takeover.npz')
    prior=np.load(Path(m['required_actual_source'])/'takeover.npz');O=transform(z['object_state'][:3],z['object_state'][3:7]);P=transform(prior['object_state'][:3],prior['object_state'][3:7]);delta=O@np.linalg.inv(P);k=G2Kinematics()
    tt=np.array([r['time_s'] for r in kn]);rq=np.array([r['motor_q'] for r in kn]);times=np.array([r['time_s'] for r in m['rows']]);arm=np.array([r['arm_q'] for r in m['rows']]);hand=np.array([r['hand_q'] for r in m['rows']]);end=tt[-1]
    start_arm=np.array([np.interp(a.reference_start,times,arm[:,j]) for j in range(7)]);start_hand=np.array([np.interp(a.reference_start,times,hand[:,j]) for j in range(20)]);start_hand[12:16]=[np.interp(a.reference_start,tt,rq[:,j]) for j in range(4)]
    align=k.forward(z['issued_target'][:7])@np.linalg.inv(delta@k.forward(start_arm));rots=Slerp([0,1],Rotation.from_matrix([align[:3,:3],np.eye(3)]))
    load_delta=z['issued_target'][7:27]-start_hand;seed=z['issued_target'][:7].copy();rows=[]
    for r in m['rows']:
        if r['time_s']<a.reference_start-1e-7 or r['time_s']>end+1e-7:continue
        t=r['time_s']-a.reference_start;u=min(1.,t/max(.1,end-a.reference_start));f=u**3*(10-15*u+6*u*u)
        A=align.copy();A[:3,:3]=rots(f).as_matrix();A[:3,3]*=1-f
        seed,ik=k.solve_near(A@delta@k.forward(r['arm_q']),seed,max_step=.12)
        q=np.asarray(r['hand_q']);q[12:16]=[np.interp(r['time_s'],tt,rq[:,j]) for j in range(4)];q+=load_delta*(1-f)
        rows.append({'time_s':float(t),'arm_q':seed.tolist(),'hand_q':q.tolist(),'ik':ik})
    rows[0]['arm_q']=z['issued_target'][:7].tolist();rows[0]['hand_q']=z['issued_target'][7:27].tolist()
    m['rows']=rows;m['required_actual_source']=str(a.source);m.pop('retained_push_skill',None)
    m['ownactual_coordinate_binding']={'source':str(a.source),'base_source':str(Path(a.base)),'reference_start_s':a.reference_start,
        'body_world_correction':delta.tolist(),'initial_motor_alignment':align.tolist(),'captured_command_delta_rad':load_delta.tolist(),
        'scope':'Current measured knife/joints/issued targets adapt remaining references; no success physical state injected'}
    (a.output/'motor.json').write_text(json.dumps(m,indent=2));record('ring_tail_own_actual_binding_prepared',[str(a.output/'motor.json')],m['ownactual_coordinate_binding'],
        next_step='Short ownactualtail physicaltest across earliestlosswindow; referenceadaptation distinguishedfromactualbearing')
    print(json.dumps({'seconds':rows[-1]['time_s'],'rows':len(rows),'maximum_position_ik_m':max(r['ik']['position_m'] for r in rows),'sourcejump_rad':0},indent=2))

if __name__=='__main__':main()
