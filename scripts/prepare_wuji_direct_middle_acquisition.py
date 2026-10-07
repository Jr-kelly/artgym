"""Acquire a third carrier in the real I/R underpad grip, other motors held."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--arch-m',type=float,default=.008);a=p.parse_args()
    a.output.mkdir(exist_ok=False);s=np.load(a.source/'takeover.npz');c=json.loads(a.candidate.read_text())
    assert c['finger']=='middle'
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@G2Kinematics().forward(s['robot_q'][:7])
    q0=s['robot_q'][7:].astype(float);m=np.array(c['material_point']);name='hand_r_middle_pad_link';ids=np.arange(4,8)
    def point(q):
        T=L@g.w.forward(q)[name];return T[:3,:3]@m+T[:3,3]
    P0=point(q0);Pend=np.array(c['point']);checker=HandIntersection();seed=q0[ids].copy();rows=[];D=[]
    record('direct_new_underpad_middle_path_start',[str(a.output)],config={'uncertainty':'Thirdmiddle carrier can enter newactualI/R grip aroundbackface without disturbing heldthumb/I/R?','source_foot_m':P0.tolist(),'endpoint_foot_m':Pend.tolist(),'change':'Separate middleacquisition beforethumbrelease; otherissuedtargets unchanged'},next_step='Guardnewmiddlepath -> one nativeacquisition; actual3carriersheld then functionalcap')
    for t in np.linspace(0,6,25):
        u=smooth((t-.5)/3.5);P=(1-u)*P0+u*Pend;P[1]-=a.arch_m*np.sin(np.pi*u)
        def decode(x):
            q=q0.copy();q[ids]=x;return q
        def res(x):
            q=decode(x);r=list((point(q)-P)*350)
            for v in g.gaps(q,L,float(s['slider_q']),'middle'):
                threshold=-(c['preload_m']*.9)*smooth((u-.7)/.3) if v['hand_link']==name and v['knife_link']=='link_0' else .0001
                r.append(min(0,v['gap_lower_bound_m']-threshold)*700)
            r.extend(min(0,v['gap_lower_bound_m']-.0002)*200 for v in g.self_gaps(q,'middle',certify_clearance_m=.0002))
            r.extend((x-seed)*.008);return np.array(r)
        if 0<u<1:
            fit=least_squares(res,np.clip(seed,g.w.lower[ids]+.05,g.w.upper[ids]-.05),bounds=(g.w.lower[ids]+.05,g.w.upper[ids]-.05),max_nfev=55,diff_step=1e-5);seed=fit.x
        elif u==1:seed=np.array(c['hand_q'])[ids]
        q=decode(seed);cmd=s['issued_target'][7:].copy();cmd[ids]=q[ids]+(1-u)*(s['issued_target'][7:][ids]-q0[ids])
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
        d=dict(time_s=float(t),fraction=float(u),point_error_m=float(np.linalg.norm(point(q)-P)),planned_hand_q=q.tolist(),minimum_middle_gap_m=g.minimum_gap(q,L,float(s['slider_q']),'middle'),self=checker.inspect(q));D.append(d);print(json.dumps(d),flush=True)
    dense=[]
    for t in np.linspace(0,6,49):
        q=np.array([np.interp(t,[d['time_s'] for d in D],[d['planned_hand_q'][j] for d in D]) for j in range(20)])
        dense.append(dict(time_s=float(t),self=checker.inspect(q),middle_gap_m=g.minimum_gap(q,L,float(s['slider_q']),'middle'),margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min())))
    result=dict(source=str(a.source),candidate=str(a.candidate),arch_m=a.arch_m,rows=rows,diagnostics=D,dense=dense,
        max_point_error_m=max(d['point_error_m'] for d in D),self_frames=sum(bool(d['self']) for d in dense),
        min_middle_gap_m=min(d['middle_gap_m'] for d in dense),scope='Onlymiddle motorpath; endpoint retainsoriginal1p5mm PDpreload prior, not physicalpenetrationconstraint relaxation')
    result['preflight_pass']=bool(result['max_point_error_m']<.0005 and result['self_frames']==0 and result['min_middle_gap_m']>=-c['preload_m']*.95 and min(d['margin_rad'] for d in dense)>.049)
    (a.output/'motor.json').write_text(json.dumps(result,indent=2));summary={key:result[key] for key in ['preflight_pass','max_point_error_m','self_frames','min_middle_gap_m']}
    print(json.dumps(summary));record('direct_new_underpad_middle_path_terminal',[str(a.output/'motor.json')],config=summary,next_step='Feasiblethirdcarrierpath -> native now; failure changes actualmiddleentry not thumbforce')
    if not result['preflight_pass']:raise SystemExit(2)


if __name__=='__main__':main()
