"""Causal loaded motor path for the current forward-bearing grip adjustment."""
import argparse, json, time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_direct_pickup import smooth
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--endpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--load-transport',choices=['point-wrench','joint-deflection'],default='point-wrench')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);c=json.loads(a.endpoint.read_text())
    assert c['permits_path'];source=Path(c['source']);s=np.load(source/'takeover.npz')
    trial,native,end=source_contacts(source);physics=json.loads((trial/'physics.json').read_text())
    kp=np.array(physics['kp'][7:]);kd=np.array(physics['kd'][7:]);effort=np.array(physics['effort'][7:]) if 'effort' in physics else None
    k=G2Kinematics();g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    checker=HandIntersection();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7])
    q0=s['robot_q'][7:].astype(float);ids=np.r_[0:8,12:20];names=list(c['materials']);materials={n:np.array(m) for n,m in c['materials'].items()}
    F0=g.w.forward(q0);points={n:(L0@F0[n])[:3,:3]@materials[n]+(L0@F0[n])[:3,3] for n in names}
    L1=np.array(c['wrist_in_knife']);rot=Rotation.from_matrix(L1[:3,:3]@L0[:3,:3].T).as_rotvec()
    end_pose=np.r_[L1[:3,3]-L0[:3,3],rot];x0=np.r_[np.zeros(6),q0[ids]];previous=x0.copy()
    acquired={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','ring','thumb']}
    acquired_self={f:g.self_gaps(q0,f,certify_clearance_m=.0002) for f in ['index','middle','ring','thumb']}
    lower=np.r_[[-.02]*3,[-.2]*3,g.w.lower[ids]+.035];upper=np.r_[[.02]*3,[.2]*3,g.w.upper[ids]-.035]
    arm_seed=s['robot_q'][:7].astype(float);rows=[];D=[];normal_priors={}
    for n in names:
        C=[v for row in native for v in row['contacts'] if v['hand_link']==n];N=np.sum([v['force_normal_contribution_knife_N'] for v in C],0);N/=np.linalg.norm(N)
        normal_priors[n]=((L0@F0[n])[:3,:3].T@N,N)

    def decode(x):
        L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3]
        q=q0.copy();q[ids]=x[6:];return L,q,g.w.forward(q)

    def jacobian(q,L,name,digit_ids):
        def point(x):
            T=L@g.w.forward(x)[name];return T[:3,:3]@materials[name]+T[:3,3]
        P=point(q);J=np.empty((3,4))
        for j,index in enumerate(digit_ids):
            x=q.copy();x[index]+=1e-5;J[:,j]=(point(x)-P)/1e-5
        return J

    loads={};digit_ids={n:np.arange(16,20) if '_thumb_' in n else np.arange(0,4) if '_index_' in n else np.arange(4,8) if '_middle_' in n else np.arange(12,16) for n in names}
    for n,digit in digit_ids.items():
        J=jacobian(q0,L0,n,digit);tau=kp[digit]*(s['issued_target'][7:][digit]-q0[digit])
        wrench=np.linalg.solve(J@J.T+np.eye(3)*1e-7,J@tau);loads[n]=(wrench,tau-J.T@wrench)
    spec=c.get('spec',{})
    if a.load_transport=='point-wrench' and len({tuple(v) for v in digit_ids.values()})!=len(names):
        raise ValueError('Multiple bearing parts of one digit require joint-deflection transport; a single-point wrench is not identifiable')
    e=record('current_forward_reaction_path_start',[str(a.output),str(a.endpoint)],config={'candidate':spec.get('candidate','C560-R10'),'source':str(source),
        'load_transport':a.load_transport,'endpoint':str(a.endpoint),
        'uncertainty':spec.get('uncertainty','Can small jointgrip adjustment continuously move Middle bearing ahead while real othercontacts remain loaded?'),
        'decision':'Denseplannedclear -> one native acquisition; actual loss repairs corresponding segment, no idealhandoff',
        'scope':'Geometry and source acquiredtorque transport, no physicalreset'},next_step='Actual615 causal loadedpath thennative; no strokeuntil newbearingactual retained')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    started=time.time()
    for t in np.linspace(0,5,11):
        u=smooth((t-.3)/4.)
        targets={n:points[n]+u*(np.array(c['planned_points'][n])-points[n]) for n in names}
        def residual(x):
            L,q,F=decode(x);r=[]
            for n in names:
                T=L@F[n];P=T[:3,:3]@materials[n]+T[:3,3];r.extend((P-targets[n])*350)
                local,normal=normal_priors[n]
                goalnormal=np.asarray(spec.get('normal_targets',{}).get(n,normal))
                normal=(1-u)*normal+u*goalnormal;normal/=np.linalg.norm(normal)
                r.extend((T[:3,:3]@local-normal)*.15)
            transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in meshes]
                         for n,meshes in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])}
            spheres={}
            for n,parts in transformed.items():
                for j,(v,_) in enumerate(parts):
                    C=v.mean(0);spheres[n,j]=(C,np.linalg.norm(v-C,axis=1).max())
            for finger in ['index','middle','ring','thumb']:
                for j,gap in enumerate(g.gaps(q,L,float(s['slider_q']),finger,frames=F)):
                    threshold=-.0004 if gap['hand_link'] in names else .0001
                    if gap['knife_link']=='link_0':
                        if finger=='thumb':threshold=.0003
                        else:threshold=min(threshold,acquired[finger][j]['gap_lower_bound_m']*(1-u)+(-.0004)*u)
                    r.append(min(0.,gap['gap_lower_bound_m']-threshold)*500)
                # Preserve this independently inspected source's conservative
                # SAT gaps at entry. A negative SAT gap is not an intersection;
                # forcing every source certificate positive can introduce a
                # large posture change in an otherwise tiny requested step.
                for j,v in enumerate(g.self_gaps(q,finger,certify_clearance_m=.0002,frames=F,transformed=transformed,enclosing_spheres=spheres)):
                    threshold=min(.0002,acquired_self[finger][j]['gap_lower_bound_m']*(1-u)+.0002*u)
                    r.append(min(0.,v['gap_lower_bound_m']-threshold)*250)
            r.extend((x[:3]-end_pose[:3]*u)*3);r.extend((x[3:6]-end_pose[3:]*u)*.3)
            r.extend((x[6:]-((1-u)*q0[ids]+u*np.array(c['hand_q'])[ids]))*.02)
            return np.array(r)
        center=np.r_[end_pose*u,(1-u)*q0[ids]+u*np.array(c['hand_q'])[ids]]
        if u>=1-1e-9:
            previous=center.copy()
        elif u>0 and (not D or abs(u-D[-1]['fraction'])>1e-9):
            # Constrain the otherwise free wrist/posture nullspace throughout
            # the transition, not just the four fingertip coordinates. The
            # envelope vanishes at source and endpoint and grows smoothly.
            envelope=np.r_[[.006]*3,[.1]*3,[.25]*len(ids)]*u*(1-u)
            lo=np.maximum(lower,center-envelope);hi=np.minimum(upper,center+envelope)
            fit=least_squares(residual,np.clip(previous,lo+1e-9,hi-1e-9),bounds=(lo,hi),max_nfev=55,diff_step=1e-5)
            previous=fit.x
        L,q,F=decode(previous);arm,ik=k.solve_near(O@L,arm_seed,max_step=.2,minimum_margin=.06);arm_seed=arm.copy();actualL=np.linalg.inv(O)@k.forward(arm)
        errors={n:float(np.linalg.norm((actualL@F[n])[:3,:3]@materials[n]+(actualL@F[n])[:3,3]-targets[n])) for n in names}
        command=q.copy()
        handled=set()
        for n,digit in digit_ids.items():
            key=tuple(digit)
            if key in handled:continue
            handled.add(key)
            if a.load_transport=='joint-deflection':
                # Multiple actual bearing parts share one joint torque. Keep
                # its measured motor deviation once per digit; do not assign
                # the whole torque independently to each material point.
                offset=s['issued_target'][7:][digit]-q0[digit]
            else:
                wrench,null=loads[n];offset=(jacobian(q,actualL,n,digit).T@wrench+null)/kp[digit]
            bound=max(.12,float(abs(s['issued_target'][7:][digit]-q0[digit]).max()))
            command[digit]+=np.clip(offset,-bound,bound)
        command=np.clip(command,g.w.lower+.02,g.w.upper-.02)
        motor_arm=arm+s['issued_target'][:7]-s['robot_q'][:7]
        if t==0:command=s['issued_target'][7:].copy();motor_arm=s['issued_target'][:7].copy()
        rows.append(dict(time_s=float(t),arm_q=motor_arm.tolist(),hand_q=command.tolist()))
        D.append(dict(time_s=float(t),fraction=float(u),actual_arm_ik=ik,planned_arm_q=arm.tolist(),planned_hand_q=q.tolist(),
                      point_errors_m=errors,self_intersections=checker.inspect(q),planned_object_world=O.tolist()))
        print(json.dumps(D[-1]),flush=True)
    # Damping feedforward is bounded by the same existing motor-interface convention.
    v=np.gradient(np.array([d['planned_hand_q'] for d in D]),np.array([d['time_s'] for d in D]),axis=0)
    for i,row in enumerate(rows):
        if i:row['hand_q']=(np.array(row['hand_q'])+np.clip(kd/kp*v[i],-.07,.07)).tolist()
    guard=[]
    for t in np.arange(0,5.0001,1/30):
        q=np.array([np.interp(t,[d['time_s'] for d in D],[d['planned_hand_q'][j] for d in D]) for j in range(20)])
        arm=np.array([np.interp(t,[d['time_s'] for d in D],[d['planned_arm_q'][j] for d in D]) for j in range(7)])
        L=np.linalg.inv(O)@k.forward(arm);gaps=g.gaps(q,L,float(s['slider_q']),'thumb');F=g.w.forward(q)
        guard.append(dict(time_s=float(t),self=checker.inspect(q),thumb_body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
                          housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!='hand_r_thumb_pad_link')))
    source_first_step_pose=np.linalg.inv(k.forward(s['robot_q'][:7]))@k.forward(np.array(D[1]['planned_arm_q']))
    summary=dict(self_frames=sum(bool(d['self']) for d in guard),max_point_error_m=max(max(d['point_errors_m'].values()) for d in D),
                 min_thumb_body_gap_m=min(d['thumb_body_gap_m'] for d in guard),min_housing_cap_gap_m=min(d['housing_cap_gap_m'] for d in guard),
                 source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),elapsed_s=time.time()-started,
                 first_step_fraction=D[1]['fraction'],first_step_wrist_translation_m=float(np.linalg.norm(source_first_step_pose[:3,3])),
                 first_step_wrist_rotation_rad=float(Rotation.from_matrix(source_first_step_pose[:3,:3]).magnitude()),
                 first_step_hand_delta_rad=float(abs(np.array(D[1]['planned_hand_q'])-q0).max()),
                 continuous_posture_envelope=True)
    summary['permits_native']=summary['self_frames']==0 and summary['max_point_error_m']<.0008 and summary['min_thumb_body_gap_m']>.0001 and summary['min_housing_cap_gap_m']>.0001
    servo=json.loads(Path('runs/flat-table-20261006/direct/preparation/current-C560-acquired-pressure-continuity-v621/motor.json').read_text())['direct_pressure_path_servo']
    servo['material_point']=materials['hand_r_thumb_pad_link'].tolist();servo['axial_reference_N']=float(loads['hand_r_thumb_pad_link'][0][2])
    servo['acquired_normal_reference_N']=None
    for carrier in servo['rolling_pair_clearance']['carriers']:carrier['material_point']=materials[carrier['material_link']].tolist()
    motor=dict(source=str(source),candidate=spec.get('candidate','C560-R10'),endpoint=str(a.endpoint),load_transport=a.load_transport,rows=rows,diagnostics=D,direct_pressure_path_servo=servo,
               development_abort_on_translation_m=.025,scope=__doc__,guard=summary)
    (a.output/'motor.json').write_text(json.dumps(motor,indent=2));(a.output/'dense-guard.json').write_text(json.dumps(dict(summary=summary,rows=guard),indent=2))
    print(json.dumps(summary),flush=True);e=record('current_forward_reaction_path_terminal',[str(a.output/'motor.json'),str(a.output/'dense-guard.json')],config=summary,
        next_step='Only geometricallyeligible path -> actualforwardbearing acquisition; verify fullphysicalinterval support/hand/contact before newstroke')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')


if __name__=='__main__':main()
