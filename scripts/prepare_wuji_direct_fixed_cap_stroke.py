"""Actual cap-material stroke with fixed acquired wrist/support motor targets."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser()
    for name in ['source','material','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--normal-cone-cosine',type=float)
    p.add_argument('--planning-thumb-margin',type=float,default=.14)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');cfg=json.loads(a.material.read_text())
    trial,contacts,end=source_contacts(a.source);physics=json.loads((trial/'physics.json').read_text())
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    q0=s['robot_q'][7:].astype(float);m=np.array(cfg['material_point']);local=np.array(cfg['local_normal'])
    def point(q):
        T=L@g.w.forward(q)['hand_r_thumb_pad_link'];return T[:3,:3]@m+T[:3,3],T[:3,:3]@local
    P0,N0=point(q0);kp=np.array(physics['kp'])[-4:];kd=np.array(physics['kd'])[-4:]
    parts=g.knife_geometry.collision_parts;checker=HandIntersection();seed=q0[16:].copy();rows=[];D=[]
    record('direct_fixed_cap_stroke_path_start',[str(a.output)],config={
        'uncertainty':'True acquired cap26mm stroke with fixed loaded wrist/support avoids earlier coordinated path drift?',
        'source':str(a.source),'stroke_m':cfg['stroke_m'],'normal_reference_N':1.4,'axial_proxy_reference_N':.95,
        'decision':'Native >20mm plus1s/quality -> fullfresh; actual slip/loss determines specific correction'},
        next_step='Dense fixedwrist stroke, original finite preload and bounded previously working wrench proxy rule')
    for t in np.linspace(0,9,61):
        u=smooth((t-.5)/6);slider=float(s['slider_q'])+cfg['stroke_m']*u
        target=P0+np.array([0,0,cfg['stroke_m']*u]);fixedparts=parts(slider)
        g.knife_geometry.collision_parts=lambda ignored:fixedparts
        def residual(x):
            q=q0.copy();q[16:]=x;P,N=point(q);r=list((P-target)*300)
            if a.normal_cone_cosine is None:
                r.extend((N-N0)*.8)
            else:
                # Four thumb DOFs cannot in general retain a fixed material
                # normal and a three-axis path. Allow surface rolling inside
                # an explicit cone; native contact still decides usefulness.
                cosine=(1-u)*min(a.normal_cone_cosine,-N0[1])+u*a.normal_cone_cosine
                r.append(max(0.,cosine+N[1])*.8)
            for gap in g.gaps(q,L,slider,'thumb'):
                threshold=-.0003 if gap['hand_link']=='hand_r_thumb_pad_link' and gap['knife_link']=='link_1' else .0003
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*1500)
            r.extend(min(0,v['gap_lower_bound_m']-.0001)*200 for v in g.self_gaps(q,'thumb',certify_clearance_m=.0001))
            r.extend((x-seed)*.01);return np.array(r)
        if u>0:
            fit=least_squares(residual,np.clip(seed,g.w.lower[16:]+a.planning_thumb_margin,g.w.upper[16:]-a.planning_thumb_margin),
                bounds=(g.w.lower[16:]+a.planning_thumb_margin,g.w.upper[16:]-a.planning_thumb_margin),max_nfev=55,diff_step=1e-5);seed=fit.x
        q=q0.copy();q[16:]=seed;P,N=point(q);J=np.empty((3,4))
        for j in range(4):
            h=q.copy();h[16+j]+=1e-5;J[:,j]=(point(h)[0]-P)/1e-5
        blend=smooth(t);force=np.array([0,-1.4,.95*smooth((t-.5)/1.5)])
        preload=np.clip(J.T@force/kp,-.12,.12)
        h=s['issued_target'][7:].astype(float);h[16:]=q[16:]+(s['issued_target'][23:]-q0[16:])*(1-blend)+preload*blend
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=h.tolist()))
        gaps=g.gaps(q,L,slider,'thumb');D.append(dict(time_s=float(t),fraction=float(u),planned_hand_q=q.tolist(),
            thumb_error_m=float(np.linalg.norm(P-target)),body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
            housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!='hand_r_thumb_pad_link'),
            self=checker.inspect(q),normal=N.tolist(),margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min())))
    times=np.array([r['time_s'] for r in rows]);q=np.array([d['planned_hand_q'] for d in D]);v=np.gradient(q[:,16:],times,axis=0)
    for i,row in enumerate(rows):
        h=np.array(row['hand_q']);h[16:]+=np.clip(kd/kp*v[i],-.07,.07)
        h[16:]=np.clip(h[16:],g.w.lower[16:]+.02,g.w.upper[16:]-.02);row['hand_q']=h.tolist()
    # Same bounded rule previously physically useful, now applied only to real cap contact.
    servo=json.loads(Path('runs/flat-table-20261006/direct/preparation/fresh-stroke-path-v87/motor-vector.json').read_text())['direct_pressure_path_servo']
    servo['material_point']=m.tolist()
    out=dict(rows=rows,diagnostics=D,source=str(a.source),material=str(a.material),stroke_m=cfg['stroke_m'],
        normal_cone_cosine=a.normal_cone_cosine,
        direct_pressure_path_servo=servo,development_abort_on_translation_m=.025,scope=__doc__+' Proxy is not measured force; original physics unchanged.')
    summary=dict(max_error_m=max(d['thumb_error_m'] for d in D),self_frames=sum(bool(d['self']) for d in D),
        body_gap_min_m=min(d['body_gap_m'] for d in D),housing_cap_gap_min_m=min(d['housing_cap_gap_m'] for d in D),
        min_geometric_margin_rad=min(d['margin_rad'] for d in D),source_target_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()))
    summary['preflight_pass']=bool(summary['max_error_m']<.0005 and not summary['self_frames'] and summary['body_gap_min_m']>.0001 and summary['housing_cap_gap_min_m']>.0001 and summary['source_target_jump_rad']<1e-6)
    out['guard']=summary;(a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps(summary))
    record('direct_fixed_cap_stroke_path_terminal',[str(a.output/'motor.json')],config=summary,next_step='Passing new fixedwrist stroke -> native9s; genuine >20mm hold then complete fresh route')
    if not summary['preflight_pass']:raise SystemExit(2)


if __name__=='__main__':main()
