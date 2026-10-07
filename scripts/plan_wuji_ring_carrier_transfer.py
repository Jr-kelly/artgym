"""Transfer from the actual index/thumb clamp to a posterior ring carrier.

The middle is intentionally unloaded to make room. Wrist motion is a motor
planning variable; the object state is never replaced. Native contact and
holding validation is required after the geometric endpoint/path.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for key in ['source','output']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7])
    _,native,end=source_contacts(a.source)
    names=['hand_r_index_pad_link','hand_r_thumb_pad_link'];materials={};points={};normals={}
    for n in names:
        C=[c for r in native if r['time_s']>end-.2 for c in r['contacts'] if c['hand_link']==n]
        m=np.mean([c['position_hand_link_m'] for c in C],0);T=L0@g.w.forward(q0)[n]
        N=np.mean([c['force_normal_contribution_knife_N'] for c in C],0);N/=np.linalg.norm(N)
        materials[n]=m;points[n]=T[:3,:3]@m+T[:3,3];normals[n]=(T[:3,:3].T@N,N)
    ring='hand_r_ring_pad_link';V=g.meshes[ring][0][0];H=ConvexHull(V).equations;face=int(H[:,0].argmax());rn=H[face,:3];rm=V[abs(V@rn+H[face,3])<.00002].mean(0)
    # Middle flexion opens, while its acquired spread remains unchanged.
    qm=q0.copy();qm[6]-=.4;qm[7]=max(qm[7],.22)
    ids=np.r_[0:8,12:20];x0=np.r_[L0[:3,3],np.zeros(3),qm[ids],.003,-.04]
    margin=np.full(20,.08);margin[16:]=.06;margin[14]=.18;margin[13]=.06
    lo=np.r_[L0[:3,3]-.055,[-.8]*3,g.w.lower[ids]+margin[ids],-.0085,-.066]
    hi=np.r_[L0[:3,3]+.055,[.8]*3,g.w.upper[ids]-margin[ids],.0085,-.018]
    for idx in [1,5]:
        j=6+list(ids).index(idx);lo[j]=q0[idx]-.005;hi[j]=q0[idx]+.005
    def decode(x):
        L=L0.copy();L[:3,3]=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3]
        h=q0.copy();h[ids]=x[6:-2];return L,h,g.w.forward(h)
    def residual(x):
        L,h,F=decode(x);r=[]
        for n in names:
            T=L@F[n];r.extend((T[:3,:3]@materials[n]+T[:3,3]-points[n])*800)
            ln,N=normals[n];r.append(max(0.,.95-(T[:3,:3]@ln)@N)*2)
        T=L@F[ring];P=T[:3,:3]@rm+T[:3,3];N=T[:3,:3]@rn
        r.extend((P-[x[-2],-.0044,x[-1]])*500);r.append(max(0.,.8-N[1])*2)
        r.extend((h[4:8]-qm[4:8])*.15)
        for f in ['index','middle','ring','thumb']:
            for v in g.gaps(h,L,float(s['slider_q']),f,frames=F):
                contact=v['hand_link']==ring and v['knife_link']=='link_0' or v['hand_link'] in names and v['knife_link']==('link_1' if f=='thumb' else 'link_0')
                threshold=-.00035 if contact else .0003
                if v['hand_link']=='hand_r_thumb_link2' and v['knife_link']=='link_0':threshold=.003
                r.append(min(0.,v['gap_lower_bound_m']-threshold)*1200)
            for v in g.self_gaps(h,f,certify_clearance_m=.001,frames=F):
                r.append(min(0.,v['gap_lower_bound_m']-.001)*500)
        r.extend((x-x0)*.02);return np.array(r)
    record('ring_carrier_transfer_geometry_start',[str(a.output)],config={'source':str(a.source),'uncertainty':'Both fixed-wrist ring directions fail through middle crowding. Can wrist/index/thumb coordination preserve their actual clamp while middle opens and ring establishes posterior tail support?','changed':'Unload middle, coordinate wrist/retained index-thumb contacts; original dynamics/efforts unchanged','decision':'Endpoint passes -> guarded transfer path/native contact; failure -> change initial functional grasp, no ring fixed-wrist retry'},next_step='One coordinated support transfer endpoint')
    b=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=130,diff_step=1e-5)
    L,h,F=decode(fit.x);T=L@F[ring];P=T[:3,:3]@rm+T[:3,3];N=T[:3,:3]@rn;target=np.array([fit.x[-2],-.0044,fit.x[-1]])
    errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@m+(L@F[n])[:3,3]-points[n])) for n,m in materials.items()}
    arm,ik=k.solve_near(O@L,s['robot_q'][:7].astype(float),max_step=1.)
    result=dict(source=str(a.source),wrist_in_knife=L.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),arm_ik=ik,retained_materials={n:m.tolist() for n,m in materials.items()},retained_points={n:v.tolist() for n,v in points.items()},retained_normals={n:[v.tolist() for v in pair] for n,pair in normals.items()},retained_errors_m=errors,ring_material=rm.tolist(),ring_local_normal=rn.tolist(),ring_point=P.tolist(),ring_target=target.tolist(),ring_error_m=float(np.linalg.norm(P-target)),ring_normal_cosine=float(N[1]),self_intersections=HandIntersection().inspect(h),elapsed_s=time.time()-b,optimizer=dict(nfev=fit.nfev,status=fit.status,optimality=float(fit.optimality)),scope=__doc__)
    result['geometry_permits_path']=result['ring_error_m']<.0005 and max(errors.values())<.0005 and result['ring_normal_cosine']>.79 and not result['self_intersections'] and ik['position_m']<.0005 and ik['rotation_rad']<.01
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));summary={k:v for k,v in result.items() if k not in ['wrist_in_knife','hand_q','arm_q','retained_materials','retained_points','retained_normals','scope']};print(json.dumps(summary),flush=True)
    e=record('ring_carrier_transfer_geometry_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Passed -> build guarded transfer motorpath; blocked -> initial functional grasp change')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    if not result['geometry_permits_path']:raise SystemExit(2)

if __name__=='__main__':main()
