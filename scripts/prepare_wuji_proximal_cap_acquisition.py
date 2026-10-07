"""Thumb-only release, proximal cap acquisition, preserving acquired carriers."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    c=json.loads(a.geometry.read_text());assert c['permits_path'];source=Path(c['source']);s=np.load(source/'takeover.npz')
    trial,native,end=source_contacts(source);physics=json.loads((trial/'physics.json').read_text());kp=np.array(physics['kp'][-4:]);kd=np.array(physics['kd'][-4:])
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();checker=HandIntersection();q0=s['robot_q'][7:].astype(float);q=q0.copy()
    O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);m=np.array(c['material_point']);n='hand_r_thumb_pad_link';local=np.array(c['material_normal_local'])
    T=L@g.w.forward(q)[n];P0=T[:3,:3]@m+T[:3,3];goal=np.array(c['rows'][0]['target_knife_m']);N0=T[:3,:3]@local
    e=record('proximal_cap_acquisition_path_start',[str(a.geometry),str(a.output)],config=dict(candidate='C560-R12',grasp_end='actual611/source615',
        support_layout='actual Ipad/Mpad/M4/Ring4; no wrist or bearing adjustment',thumb_start=goal.tolist(),
        uncertainty='Can a simple outwardrelease and proximalreentry retain acquirednonthumb support and create usable22mm initialthumb geometry?',
        decision='Clearcontinuous Thumb path -> one native; actualsafeproxcap -> rebuildstroke from its ownactualend',
        preceding635='RearYtopology path geometricallyeligible but needs15mm wristshift; notnativepromoted. Proximal Thumb path changes functionallever with carriersheld, avoids loadedbearing relocation'),next_step='One actualproximalcap acquisition, not ideal22mmstroke or accumulatedrestores')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    started=time.time();rows=[];D=[]
    for t in np.linspace(0,7,29):
        target=P0.copy();clear=P0.copy();clear[1]+=.004
        hover=goal.copy();hover[1]=clear[1]
        if t<=1.5:target=P0+(clear-P0)*smooth(t/1.5)
        elif t<=4:target=clear+(hover-clear)*smooth((t-1.5)/2.5)
        else:target=hover+(goal-hover)*smooth((t-4)/1.5)
        release=smooth(t/1.5);reentry=smooth((t-4)/1.5)
        normal=(1-reentry)*N0+reentry*np.array(c['rows'][0]['thumb_normal']);normal/=np.linalg.norm(normal)
        previous=q[16:].copy()
        def residual(x):
            h=q0.copy();h[16:]=x;F=g.w.forward(h);T=L@F[n];P=T[:3,:3]@m+T[:3,3];r=list((P-target)*500)
            r.extend((T[:3,:3]@local-normal)*.15)
            for gap in g.gaps(h,L,float(s['slider_q']),'thumb',frames=F):
                threshold=-.00025 if gap['hand_link']==n and gap['knife_link']=='link_1' else .0003
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*700)
            r.extend(min(0,v['gap_lower_bound_m']-.0002)*250 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0002,frames=F))
            r.extend((x-previous)*.015);return np.array(r)
        if t>0 and t<=5.5:
            lo=np.maximum(g.w.lower[16:]+.035,previous-.2);hi=np.minimum(g.w.upper[16:]-.035,previous+.2)
            fit=least_squares(residual,np.clip(previous,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=60,diff_step=1e-5);q[16:]=fit.x
        T=L@g.w.forward(q)[n];P=T[:3,:3]@m+T[:3,3];J=np.empty((3,4))
        for j in range(4):
            h=q.copy();h[16+j]+=1e-5;TT=L@g.w.forward(h)[n];J[:,j]=(TT[:3,:3]@m+TT[:3,3]-P)/1e-5
        # Original native motor gains and effort. Release source deformation;
        # acquire the same cap with a bounded normal motor preload only.
        cmd=s['issued_target'][7:].copy();cmd[16:]=q[16:]+(s['issued_target'][7:][16:]-q0[16:])*(1-release)
        force=np.array([0.,-.85,0.])*smooth((t-5)/.8)
        cmd[16:]+=np.clip(J.T@force/kp,-.12,.12);cmd=np.clip(cmd,g.w.lower+.02,g.w.upper-.02)
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
        D.append(dict(time_s=float(t),planned_hand_q=q.tolist(),thumb_target_knife_m=target.tolist(),thumb_point_knife_m=P.tolist(),
            point_error_m=float(np.linalg.norm(P-target)),step_rad=float(abs(q[16:]-previous).max())))
    velocity=np.gradient(np.array([r['planned_hand_q'][16:] for r in D]),np.array([r['time_s'] for r in D]),axis=0)
    for i,r in enumerate(rows):
        if i:r['hand_q'][16:]=np.clip(np.array(r['hand_q'][16:])+np.clip(kd/kp*velocity[i],-.07,.07),
                                     g.w.lower[16:]+.035,g.w.upper[16:]-.035).tolist()
    guard=[]
    for t in np.arange(0,7.0001,1/30):
        h=np.array([np.interp(t,[r['time_s'] for r in D],[r['planned_hand_q'][j] for r in D]) for j in range(20)])
        gaps=g.gaps(h,L,float(s['slider_q']),'thumb')
        guard.append(dict(time_s=float(t),self=checker.inspect(h),
            min_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
            min_housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!=n),
            min_margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min())))
    summary=dict(self_frames=sum(bool(r['self']) for r in guard),max_point_error_m=max(r['point_error_m'] for r in D),
        min_body_gap_m=min(r['min_body_gap_m'] for r in guard),min_housing_cap_gap_m=min(r['min_housing_cap_gap_m'] for r in guard),
        min_planned_margin_rad=min(r['min_margin_rad'] for r in guard),source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),
        nonthumb_motor_max_delta_rad=max(float(np.max(abs(np.asarray(r['hand_q'][:16])-s['issued_target'][7:][:16]))) for r in rows),
        nonthumb_motor_constant=all(np.allclose(r['hand_q'][:16],s['issued_target'][7:][:16],rtol=0,atol=1e-7) for r in rows),elapsed_s=time.time()-started)
    summary['permits_native']=summary['self_frames']==0 and summary['max_point_error_m']<.0008 and summary['min_body_gap_m']>.0001 and summary['min_housing_cap_gap_m']>.0001 and summary['source_jump_rad']<1e-6
    servo=json.loads(Path('runs/flat-table-20261006/direct/preparation/current-C560-acquired-pressure-continuity-v621/motor.json').read_text())['direct_pressure_path_servo']
    servo.update(material_point=m.tolist(),normal_direction=[0,-1,0],normal_reference_N=.85,retain_acquired_wrench=False,full_wrench_tracking=False,
        axial_reference_N=0.,activation_start_s=5.5,activation_ramp_s=.5)
    servo.pop('material_nullspace_reserve_rad',None);servo.pop('acquired_normal_reference_N',None)
    motor=dict(source=str(source),candidate='C560-R12',geometry=str(a.geometry),rows=rows,diagnostics=D,
        direct_pressure_path_servo=servo,development_abort_on_translation_m=.02,guard=summary,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(motor,indent=2));(a.output/'dense-guard.json').write_text(json.dumps(dict(summary=summary,rows=guard),indent=2))
    print(json.dumps(summary),flush=True)
    e=record('proximal_cap_acquisition_path_terminal',[str(a.output/'motor.json'),str(a.output/'dense-guard.json')],config=summary,
        next_step='Eligible -> native7s, actualsupport/cap quality decides nextstroke; blocked -> specificgeometry first')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')


if __name__=='__main__':main()
