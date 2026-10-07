"""Joint table-side clamp and 25mm operating reach with the palm underneath.

Three actual collision-front pads support the knife back. Separate finite
thumb configurations model initial side gripping, cap entry and stroke end.
All are geometry references, not successful physical grasps or state resets.
"""
import argparse,json,time,functools
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,nnls
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for n in ['source','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--recorded-edge-prior',type=Path,help='Validated original collision vertices nearest existing native back support contacts; no mesh changes.')
    p.add_argument('--operating-only',action='store_true',help='Resolve the underpalm operating grasp and stroke first; the result does not permit an initial table pickup.')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');q0=s['robot_q'][7:].astype(float);g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_pad_link'];digits=['index','middle','ring'];ids=np.r_[0:8,12:16];T='hand_r_thumb_pad_link';H='hand_r_thumb_link4';mats={};normals={}
    for n in names+[T]:
        V=g.meshes[n][0][0];E=ConvexHull(V).equations;j=int(E[:,0].argmax());N=E[j,:3];mats[n]=V[abs(V@N+E[j,3])<.00002].mean(0);normals[n]=N
    cones={}
    if a.recorded_edge_prior:
        for v in json.load(a.recorded_edge_prior.open()):
            n=v['link'];mats[n]=np.array(v['nearest_truevertex']);cones[n]=np.array(v['active_normals'])
    def cone_residual(B,n):
        if n in cones:return nnls(B[:3,:3]@cones[n].T,np.array([0.,1.,0.]))[1]
        return max(0.,.75-(B[:3,:3]@normals[n])[1])
    _,native,end=source_contacts(a.source);C=[v for r in native if r['time_s']>end-.2 for v in r['contacts'] if v['hand_link']==H];m=np.mean([v['position_hand_link_m'] for v in C],0);V=g.meshes[H][0][0];E=ConvexHull(V).equations;F0=g.w.forward(q0);force=np.sum([v['force_normal_contribution_knife_N'] for v in C],0);force/=np.linalg.norm(force);N=(L0@F0[H])[:3,:3].T@force;score=E[:,:3]@N;score[abs(E[:,:3]@m+E[:,3])>.0006]=-10.;j=int(score.argmax());normals[H]=E[j,:3];mats[H]=m-normals[H]*(normals[H]@m+E[j,3])
    nprior=q0[ids].copy();nprior[[3,7,11]]=.3;thumbcap=np.array([.99,.195,.292,.236]);initial=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec(),nprior,q0[16:],thumbcap,thumbcap,.008,0.,0.,.014,-.016,-.045,0.,-.015]
    lower=np.r_[[-.15,-.11,-.18],initial[3:6]-1.2,g.w.lower[ids]+.06,np.tile(g.w.lower[16:]+.06,3),[.007,-.008,-.008],[.005,-.03,-.066],-.003,-.04]
    upper=np.r_[[.035,-.015,-.035],initial[3:6]+1.2,g.w.upper[ids]-.06,np.tile(g.w.upper[16:]-.06,3),[.0085,.008,.008],[.035,-.002,-.025],.0015,.035]
    initial=np.clip(initial,lower+1e-7,upper-1e-7);parts=[g.knife_geometry.collision_parts(float(s['slider_q'])+u) for u in [0.,0.,.025]];tableO=np.array(json.load(open('runs/flat-table-20261006/direct/preparation/current-table-clear-middle-reserve-v362/prefix.json'))['physical_initial_object_world']);tableO=g.knife_geometry.table_pose(tableO)
    @functools.lru_cache(maxsize=96)
    def local_geometry(key):
        h=np.array(key);F=g.w.forward(h);transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in p] for n,p in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])};spheres={}
        for n,p in transformed.items():
            for j,(v,_) in enumerate(p):
                centre=v.mean(0);spheres[n,j]=(centre,np.linalg.norm(v-centre,axis=1).max())
        selfpen=[]
        for f in digits+['thumb']:selfpen.extend(min(0.,v['gap_lower_bound_m']-.0005)*350 for v in g.self_gaps(h,f,certify_clearance_m=.0005,frames=F,transformed=transformed,enclosing_spheres=spheres))
        selfpen.extend(min(0.,v['gap_lower_bound_m']-.0003)*1000 for v in g.pair_gaps(h,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]))
        return F,selfpen
    def decode(x):
        L=transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat());hands=[]
        for j in range(3):
            h=q0.copy();h[ids]=x[6:18];h[16:]=x[18+4*j:22+4*j];hands.append(h)
        return L,hands
    evaluations=[0];best=[float('inf')];started=time.time()
    def residual(x):
        L,hands=decode(x);r=[]
        for pose,h in enumerate(hands):
            F,pen=local_geometry(tuple(h))
            if pose!=0 or not a.operating_only:r.extend(pen)
            if pose==0:
                for j,n in enumerate(names):
                    B=L@F[n];target=np.array([x[30+j],-.0042,x[33+j]]);r.extend((B[:3,:3]@mats[n]+B[:3,3]-target)*500);r.append(cone_residual(B,n)*2.)
                if not a.operating_only:
                    B=L@F[H];r.extend((B[:3,:3]@mats[H]+B[:3,3]-[-.0097,x[36],x[37]])*500);r.append(max(0.,.75-(B[:3,:3]@normals[H])[0])*2.)
                    W=tableO@L
                    for n,p in g.meshes.items():
                        B=W@F[n]
                        for v,_ in p:r.append(min(0.,float((v@B[:3,:3].T+B[:3,3])[:,2].min()-.7502))*1200)
            else:
                B=L@F[T];target=np.array([0.,.0062,-.026+float(s['slider_q'])+(pose-1)*.025]);r.extend((B[:3,:3]@mats[T]+B[:3,3]-target)*500);r.append(max(0.,.75+(B[:3,:3]@normals[T])[1])*2.)
            for f in digits+['thumb']:
                if a.operating_only and pose==0 and f=='thumb':continue
                for v in g.gaps(h,L,float(s['slider_q'])+(pose==2)*.025,f,frames=F,knife_parts=parts[pose]):
                    allowed=(v['hand_link'] in names and v['knife_link']=='link_0') or (pose==0 and v['hand_link']==H and v['knife_link']=='link_0') or (pose>0 and v['hand_link']==T and v['knife_link']=='link_1');threshold=-.0003 if allowed else .0003;r.append(min(0.,v['gap_lower_bound_m']-threshold)*1000)
        r.append(max(0.,.5-L[1,0])*1.5);r.extend((x-initial)*.02);out=np.array(r);evaluations[0]+=1
        if evaluations[0]%300==0:
            cost=float(out@out)
            if cost<best[0]:best[0]=cost;(a.output/'planning-checkpoint.json').write_text(json.dumps(dict(x=x.tolist(),cost=cost,evaluations=evaluations[0],elapsed_s=time.time()-started,scope='Planning only, no execution permit'),indent=2))
            print(json.dumps(dict(evaluations=evaluations[0],cost=cost,elapsed_s=time.time()-started)),flush=True)
        return out
    record('underpalm_functional_joint_grasp_start',[str(a.output)],config={'source':str(a.source),'uncertainty':'Can a table-accessible palm-under wrist combine three trueback carriers, actual Thumbheel sideclamp and25mm Thumbcap reach under original geometry?','changed':'WristKnifeY[-110,-15]mm and palmnormalKnifeY>=.5, three Thumbstates/realmesh/tableconstraints solved together instead of oldwristY+74mm operatingbranch','decision':'Feasible -> fresh initialtableclamp/nativepickup then actualflip/cap; blockedgeometry identifies palm/contact topology limitation, no oldbranch retry'},next_step='Joint actualgeometry functional and table-side clamp solve')
    fit=least_squares(residual,initial,bounds=(lower,upper),max_nfev=100,diff_step=1e-5);L,hands=decode(fit.x);F,_=local_geometry(tuple(hands[0]));supports=[]
    for j,n in enumerate(names):
        B=L@F[n];target=np.array([fit.x[30+j],-.0042,fit.x[33+j]]);res=cone_residual(B,n);supports.append(dict(link=n,material=mats[n].tolist(),normal_local=normals[n].tolist(),target_knife=target.tolist(),error_m=float(np.linalg.norm(B[:3,:3]@mats[n]+B[:3,3]-target)),normal_cosine=float(np.sqrt(max(0.,1-res**2))) if n in cones else float((B[:3,:3]@normals[n])[1]),normal_cone_residual=float(res),normal_scope='Nonnegative cone of incident original facets' if n in cones else 'Single broad frontfacet'))
    thumb=[];checker=HandIntersection()
    for pose,h in enumerate(hands):
        F,_=local_geometry(tuple(h));n=H if pose==0 else T;B=L@F[n];target=np.array([-.0097,fit.x[36],fit.x[37]]) if pose==0 else np.array([0.,.0062,-.026+float(s['slider_q'])+(pose-1)*.025]);thumb.append(dict(link=n,material=mats[n].tolist(),target_knife=target.tolist(),normal_local=normals[n].tolist(),error_m=float(np.linalg.norm(B[:3,:3]@mats[n]+B[:3,3]-target)),normal_cosine=float((B[:3,:3]@normals[n])[0] if pose==0 else -(B[:3,:3]@normals[n])[1]),self=checker.inspect(h)))
    F,_=local_geometry(tuple(hands[0]));W=tableO@L;clearance=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,p in g.meshes.items() for v,_ in p);result=dict(source=str(a.source),operating_only=a.operating_only,recorded_edge_prior=str(a.recorded_edge_prior) if a.recorded_edge_prior else None,wrist_in_knife=L.tolist(),hand_q_side=hands[0].tolist(),hand_q_cap_start=hands[1].tolist(),hand_q_cap_end=hands[2].tolist(),supports=supports,thumb=thumb,initial_table_hand_clearance_m=clearance,palm_front_normal_knife_Y=float(L[1,0]),minimum_joint_margin_rad=float(min(np.minimum(h-g.w.lower,g.w.upper-h).min() for h in hands)),elapsed_s=time.time()-started,optimizer=dict(nfev=fit.nfev,status=fit.status,optimality=float(fit.optimality)),scope=__doc__);checked=thumb[1:] if a.operating_only else thumb;result['geometry_permits_native']=max(v['error_m'] for v in supports+checked)<.0005 and min(v['normal_cosine'] for v in supports+checked)>.74 and not any(v['self'] for v in checked) and (a.operating_only or clearance>.0001) and L[1,0]>.49;result['initial_pickup_permitted']=result['geometry_permits_native'] and not a.operating_only
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));summary={k:v for k,v in result.items() if k not in ['wrist_in_knife','hand_q_side','hand_q_cap_start','hand_q_cap_end','scope']};print(json.dumps(summary),flush=True);e=record('underpalm_functional_joint_grasp_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Passing geometry -> tableapproach/preload and nativepickup; blocked -> inspect specific table/contact reach, no numericalPASS')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(summary)+'\n')
    if not result['geometry_permits_native']:raise SystemExit(2)

if __name__=='__main__':main()
