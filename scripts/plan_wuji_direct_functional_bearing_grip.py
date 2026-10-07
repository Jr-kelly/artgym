"""Joint direct table grasp and 22mm operating grip with load-bearing topology.

Index side clamp, anterior Middle pad, posterior Ring4 surface and separate
thumb heel/operating pad configurations. Unlike the rejected three-pad inverse,
actual link surfaces may roll and the rear knuckle may carry. Geometry only.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--free-support-width',action='store_true')
    p.add_argument('--thumb-prior',type=Path)
    p.add_argument('--seed',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    candidate='D661' if a.free_support_width else 'D660'
    s=np.load(a.source/'takeover.npz');trial,native,end=source_contacts(a.source)
    g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();old=json.loads(Path('runs/flat-table-20261006/direct/development/current-504-pickup-live-flip-candidate-v560/prefix.json').read_text())
    tableO=g.knife_geometry.table_pose(np.asarray(old['physical_initial_object_world']));L0=np.asarray(old['direct_pickup']['wrist_in_knife'])
    q0=np.asarray(old['direct_pickup']['close_q']);ids=np.r_[0:8,12:16];nameT='hand_r_thumb_pad_link';heel='hand_r_thumb_link4'
    V={n:np.concatenate([v for v,_ in g.meshes[n]]) for n in ['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4',nameT,heel]}
    materials={}
    for n in [nameT,heel]:
        cs=[c for r in native for c in r['contacts'] if c['hand_link']==n]
        if cs:materials[n]=np.mean([c['position_hand_link_m'] for c in cs],axis=0)
        else:
            E=ConvexHull(V[n]).equations;i=E[:,0].argmax();materials[n]=V[n][abs(V[n]@E[i,:3]+E[i,3])<.00002].mean(0)
    if a.thumb_prior:
        _,prior_rows,_=source_contacts(a.thumb_prior)
        cs=[c for r in prior_rows for c in r['contacts'] if c['hand_link']==nameT and c['knife_link']=='link_1']
        materials[nameT]=np.mean([c['position_hand_link_m'] for c in cs],axis=0)
    thumbcap=np.array([.9,.25,.6,.2]);x0=np.r_[L0[:3,3],Rotation.from_matrix(L0[:3,:3]).as_rotvec(),q0[ids],q0[16:],thumbcap,thumbcap, .0025,-.049,-.033]
    lower=np.r_[[-.15,-.10,-.15],x0[3:6]-.8,g.w.lower[ids]+.05,np.tile(g.w.lower[16:]+.05,3),-.007,-.063,-.038]
    upper=np.r_[[.04,-.012,-.025],x0[3:6]+.8,g.w.upper[ids]-.05,np.tile(g.w.upper[16:]-.05,3),.015,-.030,-.029]
    if a.seed:
        seed=json.loads(a.seed.read_text());SL=np.asarray(seed['wrist_in_knife'])
        x0=np.r_[SL[:3,3],Rotation.from_matrix(SL[:3,:3]).as_rotvec(),np.asarray(seed['poses'][0]['hand_q'])[ids],
            np.asarray(seed['poses'][0]['hand_q'])[16:],np.asarray(seed['poses'][1]['hand_q'])[16:],np.asarray(seed['poses'][2]['hand_q'])[16:],
            seed['poses'][0]['contacts'][1]['target'][2],seed['poses'][0]['contacts'][2]['target'][2],seed['poses'][1]['thumb_target'][2]]
    if a.free_support_width:
        x0=np.r_[x0,.008,.008,-.003,-.002,-.015]
        lower=np.r_[lower,-.0088,-.0088,-.0042,-.0042,-.04]
        upper=np.r_[upper,.0088,.0088,.003,.003,.035]
    x0=np.clip(x0,lower+1e-7,upper-1e-7);names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4'];started=time.time();calls=[0]
    def decode(x):
        L=transform(x[:3],Rotation.from_rotvec(x[3:6]).as_quat());hs=[]
        for j in range(3):
            h=q0.copy();h[ids]=x[6:18];h[16:]=x[18+4*j:22+4*j];hs.append(h)
        return L,hs
    def surface(L,F,name,axis,side):
        T=L@F[name];points=V[name]@T[:3,:3].T+T[:3,3];proj=side*points[:,axis]
        weights=np.exp((proj-proj.max())/.00012);m=weights@V[name]/weights.sum()
        return T[:3,:3]@m+T[:3,3],m
    def residual(x):
        L,hs=decode(x);r=[]
        for pose,h in enumerate(hs):
            F=g.w.forward(h);shift=.022 if pose==2 else 0.;part=g.knife_geometry.collision_parts(float(s['slider_q'])+shift)
            iy=x[35] if a.free_support_width else 0.;mx=x[33] if a.free_support_width else .0025;rx=x[34] if a.free_support_width else .003
            for n,axis,side,target in [(names[0],0,-1,[.0095,iy,.004]),(names[1],1,1,[mx,-.004,x[30]]),(names[2],1,1,[rx,-.004,x[31]])]:
                P,_=surface(L,F,n,axis,side);r.extend((P-np.asarray(target))*400)
            thumb_name=heel if pose==0 else nameT;T=L@F[thumb_name]
            target=np.array([-.0095,x[36],x[37]]) if pose==0 and a.free_support_width else np.array([-.0095,0.,x[32]]) if pose==0 else np.array([0.,.006,x[32]+shift])
            r.extend((T[:3,:3]@materials[thumb_name]+T[:3,3]-target)*450)
            if pose==0:
                W=tableO@L
                for link,parts in g.meshes.items():
                    T=W@F[link]
                    for v,_ in parts:r.append(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7502))*1000)
            transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in parts] for n,parts in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])}
            spheres={}
            for n,parts in transformed.items():
                for j,(v,_) in enumerate(parts):
                    C=v.mean(0);spheres[n,j]=(C,np.linalg.norm(v-C,axis=1).max())
            for f in ['index','middle','ring','thumb']:
                for gap in g.gaps(h,L,float(s['slider_q'])+shift,f,frames=F,knife_parts=part):
                    allowed=gap['hand_link'] in names and gap['knife_link']=='link_0' or gap['hand_link']==thumb_name and gap['knife_link']==('link_0' if pose==0 else 'link_1')
                    r.append(min(0.,gap['gap_lower_bound_m']-(-.0003 if allowed else .0003))*1000)
                r.extend(min(0.,v['gap_lower_bound_m']-.0002)*250 for v in g.self_gaps(h,f,certify_clearance_m=.0002,frames=F,transformed=transformed,enclosing_spheres=spheres))
            r.extend(min(0.,v['gap_lower_bound_m']-.0003)*1000 for v in g.pair_gaps(h,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]))
        r.append(max(0.,.3-L[1,0])*2.);r.extend((x-x0)*.02);calls[0]+=1
        if calls[0]%300==0:print(json.dumps(dict(calls=calls[0],elapsed_s=time.time()-started,cost=float(np.dot(r,r)))),flush=True)
        return np.asarray(r)
    e=record('direct_functional_bearing_grip_start',[str(a.output)],config=dict(candidate=candidate,source=str(a.source),thumb_prior=str(a.thumb_prior),seed=str(a.seed),free_support_width=a.free_support_width,
        uncertainty='Forwardbearing sliding inC560 stopped659. Can table-accessible initialgrip alreadyestablish anteriorMiddle/posteriorRing4 while Index/Thumbheel sideclamp and22mm Thumbcap reach coexist?',
        support_layout='Indexside, forwardMiddlepad and rearRing4 actualsurfaces; allowsrolling, no threepad broadfacet demand',
        old473_scope='Rejected fixed3frontpad underpalm25mm/fixedfacet designs notrerun; newmixed side/back knucklelayout andproximal22mm functionalstart',
        decision='Geometricallyclear simultaneoustable/function -> nativeinitialclamp; specificfailure -> change bearingmaterial/topology, no seedpool or gain retry'),next_step='One jointinitial/operating topology solve, not restorefailed659 or legacy98')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    fit=least_squares(residual,x0,bounds=(lower,upper),max_nfev=90,diff_step=1e-5);L,hs=decode(fit.x);checker=HandIntersection();poses=[]
    for i,h in enumerate(hs):
        F=g.w.forward(h);n=heel if i==0 else nameT;T=L@F[n];target=np.array([-.0095,fit.x[36],fit.x[37]]) if i==0 and a.free_support_width else np.array([-.0095,0.,fit.x[32]]) if i==0 else np.array([0.,.006,fit.x[32]+(.022 if i==2 else 0.)])
        P=T[:3,:3]@materials[n]+T[:3,3];contacts=[]
        iy=fit.x[35] if a.free_support_width else 0.;mx=fit.x[33] if a.free_support_width else .0025;rx=fit.x[34] if a.free_support_width else .003
        for link,axis,side,tgt in [(names[0],0,-1,[.0095,iy,.004]),(names[1],1,1,[mx,-.004,fit.x[30]]),(names[2],1,1,[rx,-.004,fit.x[31]])]:
            pp,mat=surface(L,F,link,axis,side);contacts.append(dict(link=link,material=mat.tolist(),point=pp.tolist(),target=tgt,error_m=float(np.linalg.norm(pp-tgt))))
        poses.append(dict(hand_q=h.tolist(),contacts=contacts,thumb_link=n,thumb_material=materials[n].tolist(),thumb_point=P.tolist(),thumb_target=target.tolist(),thumb_error_m=float(np.linalg.norm(P-target)),self=checker.inspect(h)))
    W=tableO@L;F=g.w.forward(hs[0]);clear=min(float((v@(W@F[n])[:3,:3].T+(W@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts)
    arm,ik=k.solve_near(W,np.asarray(old['direct_pickup']['initial_arm_q']),max_step=2.,minimum_margin=.06)
    result=dict(candidate=candidate,source=str(a.source),thumb_prior=str(a.thumb_prior),free_support_width=a.free_support_width,wrist_in_knife=L.tolist(),table_object_world=tableO.tolist(),table_wrist_world=W.tolist(),arm_q=arm.tolist(),arm_ik=ik,poses=poses,table_hand_clearance_m=clear,palm_front_normal_knife_Y=float(L[1,0]),elapsed_s=time.time()-started,scope=__doc__)
    result['geometry_permits_native']=clear>.0001 and not any(p['self'] for p in poses) and max(max(c['error_m'] for c in p['contacts']) for p in poses)<.0005 and max(p['thumb_error_m'] for p in poses)<.0005 and ik['position_m']<.0005
    (a.output/'candidate.json').write_text(json.dumps(result,indent=2));summary=dict(geometry_permits_native=result['geometry_permits_native'],table_hand_clearance_m=clear,thumb_errors_m=[p['thumb_error_m'] for p in poses],support_errors_m=[[c['error_m'] for c in p['contacts']] for p in poses],self_poses=sum(bool(p['self']) for p in poses),arm_ik=ik,elapsed_s=result['elapsed_s']);print(json.dumps(summary),flush=True)
    e=record('direct_functional_bearing_grip_terminal',[str(a.output/'candidate.json')],config=summary,next_step='Eligible -> nativeinitialgrasp andsameepisodeflip/Thumb; blocked -> exactmixedsurfacegeometry next, nottableedge route')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(summary)+'\n')


if __name__=='__main__':main()
