"""Time a free thumb withdrawal by clearance and speed, from current actual state.

The withdrawn Cartesian waypoint is a free-space preference. Its tracking error
does not establish contact; actual native support and collision checks remain
required. Acquired SAT gaps are diagnostic lower bounds, not penetration depths.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_direct_pickup import smooth


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--maximum-rate',type=float,default=.8)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    d=json.loads(a.path.read_text());source=Path(d['source'])
    s=np.load(source/'takeover.npz')
    trial=Path(json.loads((source/'manifest.json').read_text())['source']).parent
    physics=json.loads((trial/'physics.json').read_text())
    kp=np.array(physics['kp'])[-4:];kd=np.array(physics['kd'])[-4:]
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    q=np.array([v['planned_hand_q'] for v in d['diagnostics']])
    oldtime=np.array([v['time_s'] for v in d['diagnostics']])
    u=np.array([v['fraction'] for v in d['diagnostics']])
    dt=np.maximum(np.diff(oldtime),abs(np.diff(q,axis=0)).max(axis=1)/a.maximum_rate)
    knots=np.r_[0.,np.cumsum(dt)]
    tt=np.linspace(0,knots[-1],int(np.ceil(knots[-1]*30))+1)
    Q=np.array([[np.interp(t,knots,q[:,j]) for j in range(20)] for t in tt])
    U=np.interp(tt,knots,u);velocity=np.gradient(Q[:,16:],tt,axis=0)
    checker=HandIntersection();rows=[];checks=[]
    released=d.get('released_hand_prior')
    future=np.array(json.loads(Path(released).read_text())) if released and released!='None' else None
    for i,(t,h,fraction) in enumerate(zip(tt,Q,U)):
        cmd=s['issued_target'][7:].astype(float).copy()
        cmd[16:]=h[16:]+(s['issued_target'][23:]-s['robot_q'][23:])*(1-fraction)
        cmd[16:]+=np.clip(kd/kp*velocity[i],-.07,.07)
        cmd[16:]=np.clip(cmd[16:],g.w.lower[16:],g.w.upper[16:])
        if i==0:cmd=s['issued_target'][7:].astype(float).copy()
        gaps=g.gaps(h,L,float(s['slider_q']),'thumb')
        shadow=h.copy()
        if future is not None:
            blend=smooth(fraction/.5)
            shadow[:16]=h[:16]*(1-blend)+future[:16]*blend
        checks.append(dict(time_s=float(t),planned_hand_q=h.tolist(),self=checker.inspect(h),
            unloaded_index_self=checker.inspect(shadow) if future is not None else [],
            body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
            margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min())))
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
    guard=dict(seconds=float(tt[-1]),source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),
        planned_self_frames=sum(bool(v['self']) for v in checks),
        unloaded_index_self_frames=sum(bool(v['unloaded_index_self']) for v in checks),
        minimum_planned_margin_rad=min(v['margin_rad'] for v in checks),
        acquired_body_gap_m=checks[0]['body_gap_m'],minimum_body_gap_m=min(v['body_gap_m'] for v in checks),
        terminal_body_gap_m=checks[-1]['body_gap_m'],
        maximum_planned_rate_rad_s=float((abs(np.diff(Q,axis=0))/np.diff(tt)[:,None]).max()),
        free_waypoint_max_error_m=d['maximum_error_m'],
        scope='Dense planned clearance/speed only. Free-space waypoint error is diagnostic; not a contact tracking tolerance. Native acquired contact must release and nonthumb retain knife.')
    guard['permits_native']=bool(guard['source_jump_rad']<1e-6 and guard['planned_self_frames']==0
        and guard['unloaded_index_self_frames']==0
        and guard['minimum_planned_margin_rad']>.025 and guard['terminal_body_gap_m']>.002
        and guard['minimum_body_gap_m']>guard['acquired_body_gap_m']-.0001
        and guard['maximum_planned_rate_rad_s']<=a.maximum_rate+1e-6)
    motor=dict(rows=rows,diagnostics=checks,source=str(source),guard=guard,released_hand_prior=released,
        development_abort_on_translation_m=.025,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(motor,indent=2))
    e=record('current_free_thumb_clearance_path_timed',[str(a.path),str(a.output/'motor.json')],config=guard,
        next_step='Passing clearance -> current support native withdrawal, then actual cap reach; otherwise change geometric path')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:
        f.write('\n'+e['utc']+' '+json.dumps(guard)+'\n')
    print(json.dumps(guard))
    if not guard['permits_native']:raise SystemExit(2)


if __name__=='__main__':main()
