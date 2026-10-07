"""Move the acquired middle carrier away from its upper stop by motor motion.

The actual pad material and captured elastic load guide a local posture change.
The wrist and all other digits retain their issued commands. Native contact
verification remains necessary; no physical contact is locked.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['source','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--margin',type=float,default=.12)
    p.add_argument('--reserve-acquired-command',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');trial,native,end=source_contacts(a.source)
    name='hand_r_middle_pad_link'
    contacts=[c for r in native for c in r['contacts']
              if c['hand_link']==name and c['knife_link']=='link_0']
    m=np.mean([c['position_hand_link_m'] for c in contacts],axis=0)
    normal=np.sum([c['force_normal_contribution_knife_N'] for c in contacts],axis=0)
    normal/=np.linalg.norm(normal)
    q0=s['robot_q'][7:].astype(float);issued=s['issued_target'][7:].astype(float)
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    ids=np.arange(4,8);free=np.array([4,5,7]);physics=json.loads((trial/'physics.json').read_text())
    kp=np.array(physics['kp'])[7:][ids];kd=np.array(physics['kd'])[7:][ids]
    def point(q):
        T=L@g.w.forward(q)[name];return T[:3,:3]@m+T[:3,3]
    def jacobian(q):
        P=point(q);J=np.empty((3,4))
        for j,index in enumerate(ids):
            h=q.copy();h[index]+=1e-5;J[:,j]=(point(h)-P)/1e-5
        return J
    P0=point(q0);T=L@g.w.forward(q0)[name];local=T[:3,:3].T@normal
    J0=jacobian(q0);tau=kp*(issued[ids]-q0[ids])
    force=np.linalg.solve(J0@J0.T+np.eye(3)*1e-7,J0@tau);null=tau-J0.T@force
    initial=g.gaps(q0,L,float(s['slider_q']),'middle')
    initial_self={(v['moving_link'],v['other_link']):v['gap_lower_bound_m'] for v in g.self_gaps(q0,'middle',certify_clearance_m=.0001)}
    checker=HandIntersection();seed=q0[free].copy();D=[];rows=[]
    record('middle_actual_upper_reserve_path_start',[str(a.output)],config={'source':str(a.source),'margin_rad':a.margin,'uncertainty':'Near-upper middle3 can retain genuinepad point and capturedload using threeother middle joints, without wrist/index motion?'},next_step='Localcarrierpose geometry thennative; no proxyforceincrease')
    captured_lag=max(0.,float(issued[6]-q0[6])) if a.reserve_acquired_command else 0.
    preload_bound=max(.1,float(abs(issued[ids]-q0[ids]).max()))
    for t in np.linspace(0,3,25):
        u=smooth(t/2.);angle=(1-u)*q0[6]+u*min(q0[6],g.w.upper[6]-a.margin-captured_lag)
        def decode(x):
            h=q0.copy();h[free]=x;h[6]=angle;return h
        def residual(x):
            h=decode(x);T=L@g.w.forward(h)[name];r=list((point(h)-P0)*2000)
            r.append(max(0.,.94-(T[:3,:3]@local)@normal)*3)
            for v,v0 in zip(g.gaps(h,L,float(s['slider_q']),'middle'),initial):
                threshold=min(.0001,v0['gap_lower_bound_m']) if v['hand_link']==name and v['knife_link']=='link_0' else (1-u)*min(.0001,v0['gap_lower_bound_m'])+u*.0001
                r.append(min(0,v['gap_lower_bound_m']-threshold)*400)
            for v in g.self_gaps(h,'middle',certify_clearance_m=.0001):
                old=initial_self.get((v['moving_link'],v['other_link']),.0001)
                r.append(min(0,v['gap_lower_bound_m']-((1-u)*min(.0001,old)+u*.0001))*300)
            r.extend((x-seed)*.01);return np.array(r)
        lo=np.maximum(g.w.lower[free]+.06,q0[free]-[.3,.12,.5])
        hi=np.minimum(g.w.upper[free]-.06,q0[free]+[.3,.12,.5])
        if u>0:seed=least_squares(residual,np.clip(seed,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=60,diff_step=1e-5).x
        h=decode(seed);offset=np.clip((jacobian(h).T@force+null)/kp,-preload_bound,preload_bound)
        command=issued.copy();command[ids]=np.clip(h[ids]+offset,g.w.lower[ids]+.02,g.w.upper[ids]-.02)
        if t==0:command=issued.copy()
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=command.tolist()))
        D.append(dict(time_s=float(t),planned_hand_q=h.tolist(),point_error_m=float(np.linalg.norm(point(h)-P0)),self=checker.inspect(h),middle3_margin_rad=float(g.w.upper[6]-h[6])))
    velocity=np.gradient(np.array([v['planned_hand_q'] for v in D])[:,ids],np.array([v['time_s'] for v in D]),axis=0)
    for i,row in enumerate(rows):
        if i:
            h=np.array(row['hand_q']);h[ids]=np.clip(h[ids]+np.clip(kd/kp*velocity[i],-.07,.07),g.w.lower[ids]+.02,g.w.upper[ids]-.02);row['hand_q']=h.tolist()
    if a.reserve_acquired_command:
        for row in rows:
            u=smooth(row['time_s']/2.)
            ceiling=(1-u)*max(issued[6],g.w.upper[6]-a.margin)+u*(g.w.upper[6]-a.margin)
            row['hand_q'][6]=min(row['hand_q'][6],float(ceiling))
    summary=dict(point_error_max_m=max(v['point_error_m'] for v in D),self_frames=sum(bool(v['self']) for v in D),terminal_middle3_margin_rad=D[-1]['middle3_margin_rad'],terminal_middle3_command_margin_rad=float(g.w.upper[6]-rows[-1]['hand_q'][6]),reserve_acquired_command=a.reserve_acquired_command,captured_middle3_lag_rad=captured_lag,source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()))
    summary['preflight_pass']=summary['point_error_max_m']<.0005 and summary['self_frames']==0 and summary['source_jump_rad']<1e-6
    result=dict(source=str(a.source),rows=rows,diagnostics=D,guard=summary,material_link=name,material_point=m.tolist(),captured_proxy_N=force.tolist(),development_abort_on_translation_m=.012,scope=__doc__)
    (a.output/'motor.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary))
    record('middle_actual_upper_reserve_path_terminal',[str(a.output/'motor.json')],config=summary,next_step='Passinglocalposture native3s retainedcap/support/actualmargin beforelaststroke')
    if not summary['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
