"""Acquire posterior ring support on the demonstrated functional wrist branch.

Returns to the genuine early lifted clamp, before the corner grip. The previous
successful 25 mm operating grip is only a geometry/posture prior. Its object,
slider and motor states are never used as simulator initial conditions.
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
    for key in ['source','prior-trial','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--roll-retained-materials',action='store_true')
    p.add_argument('--release-middle',action='store_true',help='Retain the opposing index/thumb clamp, free middle to avoid the three-carrier overconstraint.')
    p.add_argument('--thumb-pad-body-contact',action='store_true',help='Allow thumb heel to transfer to its true pad on the body side, instead of locking link4 to its old material.')
    p.add_argument('--thumb-heel-body-contact',action='store_true',help='Design a functional opposed initial clamp with the real acquired thumb heel, allowing its knife longitudinal point to change.')
    p.add_argument('--free-thumb',action='store_true',help='Endpoint ring and index support, with thumb wholly clear for functional cap access.')
    p.add_argument('--index-shift-z',type=float,default=0.,help='Move the index contact along the knife back instead of fixing its old longitudinal point; metres.')
    p.add_argument('--middle-shift-z',type=float,default=0.,help='Longitudinal migration for an acquired middle back support, metres.')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float)
    z=np.load(a.prior_trial/'trace.npz');qp=z['q'][0].astype(float)
    Lp=np.linalg.inv(transform(z['object'][0,:3],z['object'][0,3:7]))@transform(z['wrist'][0,:3],z['wrist'][0,3:7])
    k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7])
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    _,native,end=source_contacts(a.source)
    names=['hand_r_index_pad_link','hand_r_thumb_link4'] if a.release_middle else ['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_link4'];materials={};points={}
    if a.thumb_pad_body_contact or a.thumb_heel_body_contact or a.free_thumb:names.remove('hand_r_thumb_link4')
    for n in names:
        C=[c for r in native if r['time_s']>end-.2 for c in r['contacts'] if c['hand_link']==n]
        m=np.mean([c['position_hand_link_m'] for c in C],0);T=L0@g.w.forward(q0)[n];materials[n]=m;points[n]=T[:3,:3]@m+T[:3,3]
        if n=='hand_r_index_pad_link':points[n][2]+=a.index_shift_z
        if n=='hand_r_middle_pad_link':points[n][2]+=a.middle_shift_z
    ring='hand_r_ring_pad_link';V=g.meshes[ring][0][0];H=ConvexHull(V).equations;face=int(H[:,0].argmax());rn=H[face,:3];rm=V[abs(V@rn+H[face,3])<.00002].mean(0)
    ids=np.r_[0:8,12:20];x0=np.r_[Lp[:3,3],Rotation.from_matrix(Lp[:3,:3]).as_rotvec(),qp[ids],.0,-.05]
    margin=np.full(20,.06);margin[14]=.12;margin[16:]=.06
    lo=np.r_[Lp[:3,3]-.045,x0[3:6]-.6,g.w.lower[ids]+margin[ids],-.008,-.066]
    hi=np.r_[Lp[:3,3]+.045,x0[3:6]+.6,g.w.upper[ids]-margin[ids],.008,-.024]
    # Keep the demonstrably useful ring distal branch, not the curled corner.
    hi[6+list(ids).index(15)]=.15
    free_thumb_q=np.array([.89,-.07,.59,.57])
    newthumb='hand_r_thumb_link4' if a.thumb_heel_body_contact else 'hand_r_thumb_pad_link';thumb_body_base=None
    if a.thumb_pad_body_contact or a.thumb_heel_body_contact:
        TV=g.meshes[newthumb][0][0];TH=ConvexHull(TV).equations;tf=int(TH[:,0].argmax());tn=TH[tf,:3];tm=TV[abs(TV@tn+TH[tf,3])<.00002].mean(0)
        if a.thumb_heel_body_contact:
            C=[v for r in native if r['time_s']>end-.2 for v in r['contacts'] if v['hand_link']==newthumb];tm=np.mean([v['position_hand_link_m'] for v in C],0);force=np.sum([v['force_normal_contribution_knife_N'] for v in C],0);force/=np.linalg.norm(force);direction=(L0@g.w.forward(q0)[newthumb])[:3,:3].T@force;near=np.abs(TH[:,:3]@tm+TH[:,3])<.0006;score=TH[:,:3]@direction;score[~near]=-10.;tf=int(score.argmax());tn=TH[tf,:3];tm=tm-tn*(tn@tm+TH[tf,3])
        thumb_body_base=len(x0);x0=np.r_[x0,0.,0. if a.thumb_heel_body_contact else -.015];lo=np.r_[lo,-.003,-.04];hi=np.r_[hi,.003,.04 if a.thumb_heel_body_contact else .01]
    foot_bases={}
    if a.roll_retained_materials:
        for n in names:
            C=[c for r in native if r['time_s']>end-.2 for c in r['contacts'] if c['hand_link']==n]
            direction=np.sum([c['force_normal_contribution_knife_N'] for c in C],0);direction/=np.linalg.norm(direction)
            # Finger outward normal points towards the knife, as does its
            # normal-force contribution on the knife. Use the native sign.
            ln=(L0@g.w.forward(q0)[n])[:3,:3].T@direction
            VV=np.concatenate([v for v,_ in g.meshes[n]]);HH=ConvexHull(VV).equations;ff=int(np.argmax(HH[:,:3]@ln))
            foot=materials[n]-HH[ff,:3]*(HH[ff,:3]@materials[n]+HH[ff,3]);j=len(x0)
            foot_bases[n]=(j,HH,ff)
            x0=np.r_[x0,foot];lo=np.r_[lo,np.maximum(VV.min(0),materials[n]-.006)];hi=np.r_[hi,np.minimum(VV.max(0),materials[n]+.006)]
    oldg={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','ring','thumb']}
    def decode(x):
        L=transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat());h=q0.copy();h[ids]=x[6:6+len(ids)];return L,h,g.w.forward(h)
    def residual(x):
        L,h,F=decode(x);r=[]
        transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in parts] for n,parts in g.meshes.items() if any('_'+f+'_' in n for f in oldg) or '_pinky_' in n}
        spheres={}
        for n,parts in transformed.items():
            for j,(v,_) in enumerate(parts):
                centre=v.mean(0);spheres[n,j]=(centre,np.linalg.norm(v-centre,axis=1).max())
        for n in names:
            mat=materials[n]
            if n in foot_bases:
                j,HH,ff=foot_bases[n];mat=x[j:j+3];values=HH[:,:3]@mat+HH[:,3];r.extend(np.maximum(values,0)*1500);r.append(values[ff]*1500)
            T=L@F[n];r.extend((T[:3,:3]@mat+T[:3,3]-points[n])*450)
        T=L@F[ring];r.extend((T[:3,:3]@rm+T[:3,3]-[x[22],-.0044,x[23]])*450);r.append(max(0.,.8-(T[:3,:3]@rn)[1])*2)
        if thumb_body_base is not None:
            T=L@F[newthumb];r.extend((T[:3,:3]@tm+T[:3,3]-[-.0098,x[thumb_body_base],x[thumb_body_base+1]])*450);r.append(max(0.,.8-(T[:3,:3]@tn)[0])*2)
        for f in oldg:
            for v,initial in zip(g.gaps(h,L,float(s['slider_q']),f,frames=F),oldg[f]):
                threshold=min(-.00015,initial['gap_lower_bound_m']) if v['hand_link'] in names and v['knife_link']=='link_0' else -.0003 if v['hand_link']==ring and v['knife_link']=='link_0' else .0003
                if thumb_body_base is not None and v['hand_link']==newthumb and v['knife_link']=='link_0':threshold=-.0003
                if a.free_thumb and f=='thumb':threshold=.002 if v['knife_link']=='link_0' else .001
                r.append(min(0.,v['gap_lower_bound_m']-threshold)*1000)
            for v in g.self_gaps(h,f,certify_clearance_m=.0008,frames=F,transformed=transformed,enclosing_spheres=spheres):r.append(min(0.,v['gap_lower_bound_m']-.0008)*300)
        # Native/action checking includes these own palm/thumb pairs; the
        # cross-digit helper excludes the shared palm by design.
        for v in g.pair_gaps(h,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]):
            r.append(min(0.,v['gap_lower_bound_m']-.0003)*1200)
        if a.free_thumb:r.extend((h[16:]-free_thumb_q)*.15)
        r.extend((x[:6]-x0[:6])*.04);r.extend((h[12:16]-qp[12:16])*.04);return np.array(r)
    record('functional_backgrip_endpoint_start',[str(a.output)],config={'source':str(a.source),'prior_trial':str(a.prior_trial),'roll_retained_materials':a.roll_retained_materials,'release_middle':a.release_middle,'thumb_pad_body_contact':a.thumb_pad_body_contact,'free_thumb':a.free_thumb,'uncertainty':'Can early index/ring form a functional backgrip with whole thumb2mm clear?' if a.free_thumb else 'Can thumb body contact transfer from heel to true front pad while retaining index and acquiring functional ring support?' if a.thumb_pad_body_contact else 'Can the actual opposing I/T clamp transfer to the functional ring support while middle unloads?' if a.release_middle else 'Can early actual I/M/thumb acquire functional backgrip support?','changed':'Wholethumb withdraw after Ringback contact transfer; remove old thumb heel constraint, not replace with unreachable thumb-side-pad clamp' if a.free_thumb else 'Replace old thumb link4 material lock with actual thumb frontpad/body-side contact topology' if a.thumb_pad_body_contact else 'Release middle material constraint; keep opposing actual index/thumb clamp and truefacet rolling' if a.release_middle else 'Bounded6mm truefacet rolling instead of three welded material points' if a.roll_retained_materials else 'Return to genuine early19.7s source; functional wrist branch and ring4<=.15, not corner/.77 folded branch','decision':'Feasible -> actual-source contact-gait/native; blocked -> initial functional grasp location change, not seed/gain retry'},next_step='Functional branch support endpoint')
    b=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=120,diff_step=1e-5)
    L,h,F=decode(fit.x);T=L@F[ring];P=T[:3,:3]@rm+T[:3,3];target=np.array([fit.x[22],-.0044,fit.x[23]])
    for n,(j,HH,ff) in foot_bases.items():materials[n]=fit.x[j:j+3].copy()
    errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@m+(L@F[n])[:3,3]-points[n])) for n,m in materials.items()}
    arm,ik=k.solve_near(O@L,s['robot_q'][:7].astype(float),max_step=2.)
    result=dict(source=str(a.source),index_shift_z_m=a.index_shift_z,middle_shift_z_m=a.middle_shift_z,thumb_heel_body_contact=a.thumb_heel_body_contact,wrist_in_knife=L.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),arm_ik=ik,support_materials={n:m.tolist() for n,m in materials.items()},support_points={n:v.tolist() for n,v in points.items()},support_errors_m=errors,ring_material=rm.tolist(),ring_local_normal=rn.tolist(),ring_point=P.tolist(),ring_target=target.tolist(),ring_error_m=float(np.linalg.norm(P-target)),ring_normal_cosine=float((T[:3,:3]@rn)[1]),self_intersections=HandIntersection().inspect(h),elapsed_s=time.time()-b,optimizer=dict(nfev=fit.nfev,status=fit.status,optimality=float(fit.optimality)),scope=__doc__)
    result['geometry_permits_path']=result['ring_error_m']<.0005 and max(errors.values())<.0005 and result['ring_normal_cosine']>.79 and not result['self_intersections'] and ik['position_m']<.0005
    if thumb_body_base is not None:
        T=L@F[newthumb];target=np.array([-.0098,fit.x[thumb_body_base],fit.x[thumb_body_base+1]])
        result.update(thumb_body_material=tm.tolist(),thumb_body_normal=tn.tolist(),thumb_body_target=target.tolist(),thumb_body_error_m=float(np.linalg.norm(T[:3,:3]@tm+T[:3,3]-target)),thumb_body_normal_cosine=float((T[:3,:3]@tn)[0]))
        result['geometry_permits_path'] &= result['thumb_body_error_m']<.0005 and result['thumb_body_normal_cosine']>.79
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));summary={k:v for k,v in result.items() if k not in ['wrist_in_knife','hand_q','arm_q','support_materials','support_points','scope']};print(json.dumps(summary),flush=True)
    e=record('functional_backgrip_endpoint_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Passed -> actual-source transition/native; failed -> change contact holding/initial functional grip')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    if not result['geometry_permits_path']:raise SystemExit(2)

if __name__=='__main__':main()
