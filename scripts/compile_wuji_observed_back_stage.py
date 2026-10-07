"""Compile the back-contact stage from an observed actual development source.

This creates motor references, not a recorded actual trajectory. Source channel
limitations remain in its manifest; physics and controller gains are unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_direct_route import DirectRoute
from scripts.wuji_direct_pickup import smooth
from scripts.g2_kinematics import transform, G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser()
    for key in ['prefix','source','output']:
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    if (a.output/'motor.json').exists():
        raise FileExistsError(a.output/'motor.json')
    spec=json.loads(a.prefix.read_text())['direct_pickup']
    stage=next(v for v in spec['continuous_stages'] if v['name']=='backside_support')
    stage['hand_offset_decay_joint_indices']=[12,13,14,15]
    stage['hand_offset_decay_s']=2.
    spec['continuous_stages']=[stage];spec['duration_s']=0.
    spec['knife_spec']='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'
    source=np.load(a.source/'takeover.npz')
    O=transform(source['object_state'][:3],source['object_state'][3:7])
    arm=source['robot_q'][:7].astype(float);hand=source['robot_q'][7:].astype(float)
    issued=source['issued_target']
    motion=json.loads(Path(stage['motor']).read_text())
    prior=np.load(Path(stage['source'])/'takeover.npz')
    delta=hand-prior['robot_q'][7:]
    route=DirectRoute(spec,a.output);rows=[]
    for t in np.r_[np.arange(0,stage['duration_s'],1/30),stage['duration_s']]:
        aq,hq=route.command(float(t),O,arm,hand,issued[:7],issued[7:],float(source['slider_q']))
        rows.append(dict(time_s=float(t),arm_q=aq.tolist(),hand_q=hq.tolist()))
    jump=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-issued).max())
    dt=np.diff([r['time_s'] for r in rows])
    Q=np.array([np.r_[r['arm_q'],r['hand_q']] for r in rows])
    rate=float((abs(np.diff(Q,axis=0))/dt[:,None]).max())
    k=G2Kinematics();g=DigitGeometry(max_face_axes=10,knife_spec=Path(spec['knife_spec']))
    checker=HandIntersection();checks=[]
    times=np.array([v['time_s'] for v in motion['diagnostics']])
    planned=np.array([v['planned_hand_q'] for v in motion['diagnostics']])
    for i in sorted(set(range(0,len(rows),15))|{len(rows)-1}):
        row=rows[i];t=row['time_s']
        q=np.array([np.interp(t,times,planned[:,j]) for j in range(20)])+delta
        q[12:16]-=delta[12:16]*smooth(t/2)
        W=k.forward(np.array(row['arm_q'])-(issued[:7]-arm));F=g.w.forward(q)
        points=np.concatenate([v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3]
            for n,meshes in g.meshes.items() for v,_ in meshes])
        checks.append(dict(t=t,self=checker.inspect(q),hand_table_clearance_m=float(points[:,2].min()-.75),
            planned_margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min())))
    guard=dict(sourcejump_rad=jump,max_motor_rate_rad_s=rate,
        planned_self_frames=sum(bool(v['self']) for v in checks),
        minimum_hand_table_clearance_m=min(v['hand_table_clearance_m'] for v in checks),
        minimum_planned_margin_rad=min(v['planned_margin_rad'] for v in checks),
        scope='2Hz predicted actualpose uses sourceactual-minusprioractual delta. Geometry only, not motorFK/native validation. Source missingchannels remain disclosed.',rows=checks)
    guard['permits_native']=bool(jump<1e-5 and rate<1.1 and guard['planned_self_frames']==0
        and guard['minimum_hand_table_clearance_m']>.01)
    (a.output/'guard.json').write_text(json.dumps(guard,indent=2))
    motor=dict(rows=rows,source=str(a.source),development_abort_on_translation_m=.025,
        scope=__doc__,retired_joint_indices=[12,13,14,15],retirement_s=2.)
    (a.output/'motor.json').write_text(json.dumps(motor,indent=2))
    (a.output/'stage-spec.json').write_text(json.dumps(stage,indent=2))
    summary={k:v for k,v in guard.items() if k!='rows'}
    summary['compiler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    e=record('observed_back_ring_offset_retirement_compiled',[str(a.output/'guard.json'),str(a.output/'motor.json')],
        config=summary,next_step='Passing geometry -> native backcontact segment, retained nonthumb load and actual allframe hand checks; failure changes specific path.')
    Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    print(json.dumps(summary))
    if not guard['permits_native']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
