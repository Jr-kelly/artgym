"""Acquire an opposing middle side contact while retaining the real old clamp."""
import argparse, json, time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(exist_ok=False)
    s=np.load(a.source/'takeover.npz')
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();q0=s['robot_q'][7:].astype(float)
    O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7])
    _,native,_=source_contacts(a.source)
    names=['hand_r_index_link4','hand_r_index_pad_link','hand_r_ring_link4','hand_r_ring_pad_link','hand_r_thumb_link4']
    materials={n:np.mean([c['position_hand_link_m'] for r in native for c in r['contacts'] if c['hand_link']==n],0) for n in names}
    F0=g.w.forward(q0)
    points={n:(L0@F0[n])[:3,:3]@m+(L0@F0[n])[:3,3] for n,m in materials.items()}
    ids=np.r_[0:8,12:20];name='hand_r_middle_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]])
    x0=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec(),q0[ids],-.035]
    lo=np.r_[x0[:3]-.055,x0[3:6]-1.,g.w.lower[ids]+.06,-.06]
    hi=np.r_[x0[:3]+.055,x0[3:6]+1.,g.w.upper[ids]-.06,-.015]
    gaps0={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']}
    fixedparts=g.knife_geometry.collision_parts(float(s['slider_q']));g.knife_geometry.collision_parts=lambda ignored:fixedparts

    def decode(x):
        L=transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat());q=q0.copy();q[ids]=x[6:-1]
        F=g.w.forward(q);T=L@F[name];v=V@T[:3,:3].T+T[:3,3]
        weights=np.exp((v[:,0]-v[:,0].max())/.00015);P=weights@v/weights.sum()
        return L,q,F,P

    def residual(x):
        L,q,F,P=decode(x);r=[]
        for n,m in materials.items():
            T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-points[n])*350)
        r.extend((P-[-.0096,0,x[-1]])*300)
        for f in ['thumb','index','middle','ring']:
            for gap,initial in zip(g.gaps(q,L,float(s['slider_q']),f),gaps0[f]):
                threshold=min(-.00004,initial['gap_lower_bound_m']) if gap['hand_link'] in materials else -.00004 if gap['hand_link']==name and gap['knife_link']=='link_0' else .0001
                r.append(min(0,gap['gap_lower_bound_m']-threshold)*1000)
            r.extend(min(0,v['gap_lower_bound_m']-.0001)*1000 for v in g.self_gaps(q,f,certify_clearance_m=.0001))
        r.extend((x-x0)*.02)
        return np.array(r)

    record('direct_joint_opposed_middle_plan_start',[str(a.output)],config={
        'uncertainty':'Can actualjointwrist retain all5old index/ring/thumb contactmaterials while middle reaches opposite−Xcenter side belowthumb?',
        'decision':'Clearreachable->middlebackoutside-to-side gait, then actualopposition beforethumbwithdraw; obstruction->specificclamp contactsliding instead ofnewnormalgain',
        'source':str(a.source),'physics':False},next_step='Inspect actualG2 and wholehand endpoint before native')
    began=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=150,diff_step=1e-5)
    L,q,F,P=decode(fit.x);arm,ik=k.solve_near(O@L,s['robot_q'][:7].astype(float),max_step=1.)
    T=L@F[name];m=T[:3,:3].T@(P-T[:3,3])
    errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@mat+(L@F[n])[:3,3]-points[n])) for n,mat in materials.items()}
    out=dict(wrist_in_knife=L.tolist(),hand_q=q.tolist(),arm_q=arm.tolist(),arm_ik=ik,
        carrier_material=m.tolist(),carrier_point=P.tolist(),carrier_target=[-.0096,0,float(fit.x[-1])],
        carrier_error_m=float(np.linalg.norm(P-[-.0096,0,fit.x[-1]])),
        retained_materials={n:m.tolist() for n,m in materials.items()},retained_points={n:m.tolist() for n,m in points.items()},
        retained_errors_m=errors,self=HandIntersection().inspect(q),finger_gaps_m={f:g.minimum_gap(q,L,float(s['slider_q']),f) for f in ['thumb','index','middle','ring']},
        elapsed_s=time.time()-began,scope='Planonly; actualoldclamp retained, no physicswrites or successclaim')
    (a.output/'candidate.json').write_text(json.dumps(out,indent=2))
    summary={k:v for k,v in out.items() if k not in ['wrist_in_knife','hand_q','retained_materials','retained_points']};print(json.dumps(summary),flush=True)
    record('direct_joint_opposed_middle_plan_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Endpointguard guides nextchangedacquisition; fullpath then actualnewopposition, no repeatedthumbclear')


if __name__=='__main__':main()
