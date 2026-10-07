"""Open acquired thumb base before moving its distal joints past the index.

The free endpoint and unloaded obstacle are development geometry priors. Only
motor targets are produced; no physical state, actuator or collision is changed.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['source','free_path','unloaded_hand','output']:
        p.add_argument('--'+key.replace('_','-'),dest=key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float)
    d=json.loads(a.free_path.read_text());qend=np.array(d['diagnostics'][-1]['planned_hand_q'])
    qbase=q0.copy();qbase[16]-=.2
    shadow=np.array(json.loads(a.unloaded_hand.read_text()))
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    trial=Path(json.loads((a.source/'manifest.json').read_text())['source']).parent
    physics=json.loads((trial/'physics.json').read_text());kp=np.array(physics['kp'])[-4:];kd=np.array(physics['kd'])[-4:]
    times=np.arange(0,5.2+1/60,1/30);Q=[]
    for t in times:
        if t<1.5:q=q0+(qbase-q0)*smooth(t/1.5)
        else:q=qbase+(qend-qbase)*smooth((t-1.8)/2.3)
        Q.append(q)
    Q=np.array(Q);velocity=np.gradient(Q[:,16:],times,axis=0);checker=HandIntersection();rows=[];checks=[]
    for i,(t,q) in enumerate(zip(times,Q)):
        unload=smooth(t/1.5)
        h=s['issued_target'][7:].astype(float).copy()
        h[16:]=q[16:]+(s['issued_target'][23:]-q0[16:])*(1-unload)+np.clip(kd/kp*velocity[i],-.07,.07)
        h[16:]=np.clip(h[16:],g.w.lower[16:],g.w.upper[16:])
        if i==0:h=s['issued_target'][7:].astype(float).copy()
        sh=q.copy();sh[:16]=shadow[:16]
        checks.append(dict(time_s=float(t),planned_hand_q=q.tolist(),self=checker.inspect(q),
            unloaded_index_self=checker.inspect(sh),body_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(q,L,float(s['slider_q']),'thumb') if v['knife_link']=='link_0'),
            margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min())))
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=h.tolist()))
    guard=dict(source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),
        planned_self_frames=sum(bool(v['self']) for v in checks),unloaded_index_self_frames=sum(bool(v['unloaded_index_self']) for v in checks),
        acquired_body_gap_m=checks[0]['body_gap_m'],minimum_body_gap_m=min(v['body_gap_m'] for v in checks),terminal_body_gap_m=checks[-1]['body_gap_m'],
        minimum_planned_margin_rad=min(v['margin_rad'] for v in checks),maximum_planned_rate_rad_s=float((abs(np.diff(Q,axis=0))/np.diff(times)[:,None]).max()),
        scope='Dense planned loaded/unloaded geometry, acquired SAT gap diagnostic only; actual native contact required')
    guard['permits_native']=bool(guard['source_jump_rad']<1e-6 and not guard['planned_self_frames'] and not guard['unloaded_index_self_frames']
        and guard['minimum_body_gap_m']>guard['acquired_body_gap_m']-.0001 and guard['terminal_body_gap_m']>.002
        and guard['minimum_planned_margin_rad']>.025 and guard['maximum_planned_rate_rad_s']<.8)
    tracking=dict(joint_indices=[16,17,18,19],path=[dict(time_s=float(t),joint_q=q[16:].tolist()) for t,q in zip(times,Q)],
        activation_s=.5,gain_per_frame=.15,max_step_rad=.01,max_correction_rad=.12)
    motor=dict(rows=rows,diagnostics=checks,source=str(a.source),free_endpoint_geometry=str(a.free_path),unloaded_hand_geometry=str(a.unloaded_hand),
        direct_joint_path_tracking=tracking,guard=guard,development_abort_on_translation_m=.025,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(motor,indent=2))
    e=record('current_base_first_thumb_free_path_prepared',[str(a.output/'motor.json')],config=guard,
        next_step='Passing geometry -> native base-first withdrawal; current actual selfclear support -> cap and stroke')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(guard)+'\n')
    print(json.dumps(guard))
    if not guard['permits_native']:raise SystemExit(2)


if __name__=='__main__':main()
