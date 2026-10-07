"""Descend a thumb already above the cap while holding acquired support targets."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser()
    for key in ['source','material','output']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--thumb1-upper',type=float)
    p.add_argument('--selected-root-clearance-m',type=float)
    p.add_argument('--normal-cone-cosine',type=float)
    p.add_argument('--cap-z-offset-m',type=float,default=-.020)
    p.add_argument('--endpoint-branch-prior',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');cfg=json.loads(a.material.read_text())
    trial=Path(json.loads((a.source/'manifest.json').read_text())['source']).parent
    physics=json.loads((trial/'physics.json').read_text())
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();q0=s['robot_q'][7:].astype(float)
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@k.forward(s['robot_q'][:7])
    m=np.array(cfg['material_point']);local=np.array(cfg['local_normal'])
    def point(h):
        T=L@g.w.forward(h)['hand_r_thumb_pad_link']
        return T[:3,:3]@m+T[:3,3],T[:3,:3]@local
    P0,N0=point(q0);end=np.array([0,.006,a.cap_z_offset_m+float(s['slider_q'])])
    initial_root_gap=min(v['gap_lower_bound_m'] for v in g.gaps(q0,L,float(s['slider_q']),'thumb') if v['hand_link']=='hand_r_thumb_link2' and v['knife_link']=='link_0')
    kp=np.array(physics['kp'])[-4:];kd=np.array(physics['kd'])[-4:]
    checker=HandIntersection();seed=q0[16:].copy();rows=[];D=[]
    branch=None
    if a.endpoint_branch_prior:
        branch=np.array(json.loads(a.endpoint_branch_prior.read_text())['hand_q'])[16:]
        seed=branch.copy()
    record('direct_fixed_cap_entry_path_start',[str(a.output)],config={
        'source':str(a.source),'uncertainty':'Remove late wrist movement after actual high crossing, retain acquired motor support and descend only thumb','target_m':end.tolist(),
        'decision':'Actual cap contact with held support -> stroke immediately; otherwise first actual deviation decides grip/path change'},
        next_step='Fixedwrist true-material dense path guard then one native cap entry')
    knots=np.linspace(0,5,41)
    if branch is not None:knots=knots[::-1]
    for t in knots:
        u=smooth((t-.8)/2.2);target=P0*(1-u)+end*u
        N=N0*(1-u)+np.array([0,-1,0])*u;N/=np.linalg.norm(N)
        def residual(x):
            h=q0.copy();h[16:]=x;P,n=point(h)
            r=list((P-target)*300)
            if a.normal_cone_cosine is None:r.extend((n-N)*.6)
            else:r.append(max(0.,(1-u)*min(a.normal_cone_cosine,-N0[1])+u*a.normal_cone_cosine+n[1])*.6)
            for gap in g.gaps(h,L,float(s['slider_q']),'thumb'):
                threshold=-.0003 if gap['hand_link']=='hand_r_thumb_pad_link' and gap['knife_link']=='link_1' else .0003
                if a.selected_root_clearance_m is not None and gap['hand_link']=='hand_r_thumb_link2' and gap['knife_link']=='link_0':
                    threshold=(1-u)*min(a.selected_root_clearance_m,initial_root_gap)+u*a.selected_root_clearance_m
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*1500)
            r.extend(min(0,v['gap_lower_bound_m']-.0001)*200 for v in g.self_gaps(h,'thumb',certify_clearance_m=.0001))
            r.extend((x-seed)*.01)
            if branch is not None:r.extend((x-((1-u)*q0[16:]+u*branch))*.02)
            return np.array(r)
        if u>0:
            lo=g.w.lower[16:]+.05;hi=g.w.upper[16:]-.05
            if a.thumb1_upper is not None:hi[0]=min(hi[0],(1-u)*max(q0[16],a.thumb1_upper)+u*a.thumb1_upper)
            fit=least_squares(residual,np.clip(seed,lo,hi),bounds=(lo,hi),max_nfev=55,diff_step=1e-5)
            seed=fit.x
        elif branch is not None:seed=q0[16:].copy()
        h=q0.copy();h[16:]=seed;P,n=point(h);J=np.empty((3,4))
        for j in range(4):
            hh=h.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)[0]-P)/1e-5
        load=(s['issued_target'][23:]-q0[16:])*(1-u)
        load+=np.clip(J.T@np.array([0,-1.4,0])/kp,-.12,.12)*smooth((u-.85)/.15)
        cmd=s['issued_target'][7:].astype(float);cmd[16:]=h[16:]+load
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
        D.append(dict(time_s=float(t),fraction=float(u),hand_q=h.tolist(),error_m=float(np.linalg.norm(P-target)),normal=n.tolist(),self=checker.inspect(h),body_gap_m=min(v['gap_lower_bound_m'] for v in g.gaps(h,L,float(s['slider_q']),'thumb') if v['knife_link']=='link_0')))
    rows.sort(key=lambda r:r['time_s']);D.sort(key=lambda r:r['time_s'])
    times=np.array([r['time_s'] for r in rows]);hands=np.array([d['hand_q'] for d in D]);v=np.gradient(hands[:,16:],times,axis=0)
    for i,row in enumerate(rows):
        h=np.array(row['hand_q']);h[16:]+=np.clip(kd/kp*v[i],-.07,.07)
        h[16:]=np.clip(h[16:],g.w.lower[16:]+.02,g.w.upper[16:]-.02)
        row['hand_q']=h.tolist()
    start=np.r_[rows[0]['arm_q'],rows[0]['hand_q']]
    result=dict(rows=rows,diagnostics=D,source=str(a.source),material=str(a.material),
        thumb1_upper=a.thumb1_upper,selected_root_clearance_m=a.selected_root_clearance_m,normal_cone_cosine=a.normal_cone_cosine,cap_z_offset_m=a.cap_z_offset_m,
        endpoint_branch_prior=str(a.endpoint_branch_prior) if a.endpoint_branch_prior else None,
        maximum_planned_rate_rad_s=float((abs(np.diff(hands,axis=0))/np.diff(times)[:,None]).max()),
        max_error_m=max(d['error_m'] for d in D),self_frames=sum(bool(d['self']) for d in D),
        thumb_body_gap_min_m=min(d['body_gap_m'] for d in D),source_target_jump_rad=float(abs(start-s['issued_target']).max()),
        development_abort_on_translation_m=.025,scope=__doc__+' Original physics/PD/limits, normal reference is not measured force.')
    result['preflight_pass']=bool(result['max_error_m']<.0005 and not result['self_frames'] and result['thumb_body_gap_min_m']>.0001 and result['source_target_jump_rad']<1e-6)
    (a.output/'motor.json').write_text(json.dumps(result,indent=2));summary={key:value for key,value in result.items() if key not in ['rows','diagnostics']}
    print(json.dumps(summary));record('direct_fixed_cap_entry_path_terminal',[str(a.output/'motor.json')],config=summary,
        next_step='Passed fixedwrist path -> native acquiredsupport capentry; failed -> specificgeometry change')
    if not result['preflight_pass']:raise SystemExit(2)


if __name__=='__main__':main()
