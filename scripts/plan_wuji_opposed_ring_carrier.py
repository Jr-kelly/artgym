"""An opposing nonthumb front contact from the actual retained grasp.

The acquired wrist and other digit positions remain planning constraints.
Contact force and independent holding must subsequently be checked in physics.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['source','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--posterior-tail',action='store_true',help='Reach the back face at the tail; this is not an opposing front cage.')
    p.add_argument('--distal-opening-branch',action='store_true',help='Require Ring4<=0.15rad for the demonstrated backpad branch rather than the observed curled free-space detour.')
    p.add_argument('--lateral-tail',action='store_true',help='True pad on knife +X side near tail; supplies lateral reaction rather than the previous front/back topology')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    name='hand_r_ring_pad_link';V=g.meshes[name][0][0];H=ConvexHull(V).equations
    i=int(H[:,0].argmax());local=H[i,:3];m=V[abs(V@local+H[i,3])<.00002].mean(0)
    ids=np.arange(12,16)
    def decode(x):
        h=q0.copy();h[ids]=x[:4];T=L@g.w.forward(h)[name]
        return h,T[:3,:3]@m+T[:3,3],T[:3,:3]@local
    T=L@g.w.forward(q0)[name];P0=T[:3,:3]@m+T[:3,3]
    # Allow either tail or distal housing, avoiding the moving cap's interval.
    # A distal straight finger can oppose the acquired curled index carrier.
    target_y=-.0044 if a.posterior_tail else .0044
    desired_normal_y=1. if a.posterior_tail else -1.
    zrange=[-.066,-.018] if a.posterior_tail else [.025,.061]
    axis=1;sign=desired_normal_y;freeaxis=0;fixedposition=target_y;freebounds=[-.0085,.0085]
    if a.lateral_tail:
        if a.posterior_tail:raise ValueError('Choose one carrier face')
        axis=0;sign=-1.;freeaxis=1;fixedposition=.0098;freebounds=[-.003,.003];zrange=[-.066,-.018]
    seed=np.r_[q0[ids],np.clip(P0[freeaxis],*freebounds),np.clip(P0[2],*zrange)]
    margins=np.array([.12,.06,.18,.12])
    lo=np.r_[g.w.lower[ids]+margins,freebounds[0],zrange[0]]
    hi=np.r_[g.w.upper[ids]-margins,freebounds[1],zrange[1]]
    if a.distal_opening_branch:hi[3]=min(hi[3],.15)
    def residual(x):
        h,P,N=decode(x);target=np.zeros(3);target[axis]=fixedposition;target[freeaxis]=x[4];target[2]=x[5]
        r=list((P-target)*500);r.append(max(0.,.8-sign*N[axis])*2)
        for v in g.gaps(h,L,float(s['slider_q']),'ring'):
            threshold=-.00025 if v['hand_link']==name and v['knife_link']=='link_0' else .0003
            r.append(min(0.,v['gap_lower_bound_m']-threshold)*1500)
        for v in g.self_gaps(h,'ring',certify_clearance_m=.003):
            proximal=('link2' in v['moving_link'] and any(k in v['other_link'] for k in ['middle_link2','middle_link3']))
            r.append(min(0.,v['gap_lower_bound_m']-(.003 if proximal else .0002))*500)
        r.extend((x-seed)*.01);return np.array(r)
    record('opposed_ring_carrier_geometry_start',[str(a.output)],config={'source':str(a.source),'uncertainty':'Can true Ring pad supply lateral +X tail reaction without disturbing current I/M/T?' if a.lateral_tail else 'Can the ring true pad reach the posterior tail as in the demonstrated independent I/R support?' if a.posterior_tail else 'Can ring establish opposing front contact?','target_face_axis':axis,'target_face_position_m':fixedposition,'target_z_range_m':zrange,'posterior_tail':a.posterior_tail,'lateral_tail':a.lateral_tail,'decision':'Feasible contact -> collisionfree approach/native then stroke; unreachable -> stop this face family, no seed scan'},next_step='One actual source ring support reach/collision check')
    fit=least_squares(residual,np.clip(seed,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=160,diff_step=1e-5)
    h,P,N=decode(fit.x);target=np.zeros(3);target[axis]=fixedposition;target[freeaxis]=fit.x[4];target[2]=fit.x[5]
    gaps=g.gaps(h,L,float(s['slider_q']),'ring')
    result=dict(source=str(a.source),posterior_tail=a.posterior_tail,lateral_tail=a.lateral_tail,material_link=name,material_point=m.tolist(),local_normal=local.tolist(),hand_q=h.tolist(),point_knife_m=P.tolist(),target_knife_m=target.tolist(),normal_knife=N.tolist(),point_error_m=float(np.linalg.norm(P-target)),normal_cosine=float(sign*N[axis]),self_intersections=HandIntersection().inspect(h),minimum_joint_margin_rad=float(np.minimum(h[ids]-g.w.lower[ids],g.w.upper[ids]-h[ids]).min()),minimum_nonpad_knife_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['hand_link']!=name),optimizer={'nfev':fit.nfev,'status':fit.status,'optimality':float(fit.optimality)},scope=__doc__)
    result['geometry_permits_path']=result['point_error_m']<.0005 and result['normal_cosine']>.79 and not result['self_intersections'] and result['minimum_nonpad_knife_gap_m']>.0001
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));summary={k:v for k,v in result.items() if k not in ['hand_q','scope']};print(json.dumps(summary))
    e=record('opposed_ring_carrier_geometry_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Passed -> physically guarded approach; blocked -> another support mechanism, not gain/seed repetition')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    if not result['geometry_permits_path']:raise SystemExit(2)

if __name__=='__main__':main()
