"""Actual housing-to-pad ring rolling into the functional index/ring grip.

Ring material points are projected onto original collision meshes, allowing a
contact to migrate from the current housing to the pad. This changes only motor
references. Native contacts decide whether the planned support transfer occurs.
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
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for n in ['source','endpoint','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--corner-before-back',action='store_true',help='Keep ring at the existing knife corner until wrist turns; prohibit the observed curled distal branch.')
    p.add_argument('--migrate-index',action='store_true',help='Roll/slide index along the actual knife back to the endpoint longitudinal contact instead of fixing its knife point.')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');c=json.load(a.endpoint.open());q0=s['robot_q'][7:].astype(float);arm0=s['robot_q'][:7].astype(float)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(arm0);F0=g.w.forward(q0)
    trial,native,end=source_contacts(a.source);physics=json.load((trial/'physics.json').open());kp=np.array(physics['kp'])[7:];kd=np.array(physics['kd'])[7:]
    index='hand_r_index_pad_link';ring='hand_r_ring_pad_link';heel='hand_r_ring_link4'
    def contact(n):
        C=[v for r in native if r['time_s']>end-.2 for v in r['contacts'] if v['hand_link']==n]
        return np.mean([v['position_hand_link_m'] for v in C],0)
    mi=contact(index);mr4=contact(heel);T=np.linalg.inv(F0[ring])@F0[heel];mr0=T[:3,:3]@mr4+T[:3,3];mr1=np.array(c['ring_material'])
    thumb_heel='hand_r_thumb_link4';mt=contact(thumb_heel);Tt=L0@F0[thumb_heel];Pt=Tt[:3,:3]@mt+Tt[:3,3]
    Ti=L0@F0[index];Pi=Ti[:3,:3]@mi+Ti[:3,3];Tr=L0@F0[ring];Pr=Tr[:3,:3]@mr0+Tr[:3,3]
    # Each local ray intersects a real original housing or pad collision hull.
    ring_parts=[]
    for n in [heel,ring]:
        T=np.linalg.inv(F0[ring])@F0[n]
        for V,_ in g.meshes[n]:
            V=V@T[:3,:3].T+T[:3,3];ring_parts.append((n,ConvexHull(V).equations))
    def ring_surface(u):
        yz=((1-u)*mr0+u*mr1)[1:];candidates=[]
        for n,H in ring_parts:
            ids=H[:,0]>1e-8
            xvals=-(H[ids,1:3]@yz+H[ids,3])/H[ids,0];j=np.flatnonzero(ids)[np.argmin(xvals)];m=np.r_[xvals.min(),yz]
            if (H[:,:3]@m+H[:,3]).max()<1e-7:candidates.append((m[0],n,m,H[j,:3]))
        if not candidates:raise ValueError('No original ring collision surface on material ray')
        _,n,m,N=max(candidates,key=lambda v:v[0]);return n,m,N
    HI=ConvexHull(g.meshes[index][0][0]).equations;localN=(L0@F0[index])[:3,:3].T@np.array([-1.,0,0]);iface=int(np.argmax(HI[:,:3]@localN))
    index_lo=np.maximum(g.meshes[index][0][0].min(0),mi-.006);index_hi=np.minimum(g.meshes[index][0][0].max(0),mi+.006)
    ids=np.r_[0:8,12:20];initial=np.r_[arm0,q0[ids],mi];endpoint_arm,_=k.solve_near(O@np.array(c['wrist_in_knife']),arm0,max_step=2.,minimum_margin=.06);endvector=np.r_[endpoint_arm,np.array(c['hand_q'])[ids],np.array(c['support_materials'][index])]
    Lend=np.array(c['wrist_in_knife']);rdelta=Rotation.from_matrix(L0[:3,:3].T@Lend[:3,:3]).as_rotvec();previous=initial.copy();rows=[];D=[];checker=HandIntersection()
    oldg={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','ring','thumb']}
    knife_parts=g.knife_geometry.collision_parts(float(s['slider_q']))
    record('functional_ring_contact_gait_start',[str(a.output)],config={'source':str(a.source),'endpoint':str(a.endpoint),'corner_before_back':a.corner_before_back,'uncertainty':'Can the acquired corner hold through early wrist motion before ring rolls to backface and thumb exits?' if a.corner_before_back else 'Can ring housing roll to backpad before thumb exits?','changed':'Keep current ring corner while wrist turns; ring4 monotonic opening bound instead of observed+.575curl; thumb heel retained until backface roll' if a.corner_before_back else 'Actual middle-free source, original ring housing/pad surface ray, ring material migrates3.6mmZ/5.4mmY; thumb preload exits after ring transfer','decision':'Guarded path -> native actual housing-to-pad/support transition; first infeasible node changes support transfer timing/initial grasp'},next_step='Continuous original-surface contact gait then native')
    b=time.time()
    for t in np.linspace(0,10,41):
        u=smooth((t-.5)/8);rollu=smooth((u-.28)/.5) if a.corner_before_back else u;thumbu=smooth((rollu-.15)/.6) if a.corner_before_back else u
        target_i=(1-u)*Pi+u*np.array(c['support_points'][index]) if a.migrate_index else Pi
        part,mr,rn=ring_surface(rollu);target_r=(1-rollu)*Pr+rollu*np.array(c['ring_target']);guide=L0.copy();guide[:3,3]=(1-u)*L0[:3,3]+u*Lend[:3,3];guide[:3,:3]=L0[:3,:3]@Rotation.from_rotvec(rdelta*u).as_matrix();prior=(1-u)*initial+u*endvector
        if a.corner_before_back:prior[19:23]=(1-thumbu)*initial[19:23]+thumbu*endvector[19:23]
        def decode(x):
            h=q0.copy();h[ids]=x[7:23];L=np.linalg.inv(O)@k.forward(x[:7]);return h,L,g.w.forward(h)
        def residual(x):
            h,L,F=decode(x);r=[];mat=x[23:26];values=HI[:,:3]@mat+HI[:,3];r.extend(np.maximum(values,0)*1200);r.append(values[iface]*1200)
            transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in parts] for n,parts in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])}
            spheres={}
            for n,parts in transformed.items():
                for j,(v,_) in enumerate(parts):
                    centre=v.mean(0);spheres[n,j]=(centre,np.linalg.norm(v-centre,axis=1).max())
            Ti=L@F[index];r.extend((Ti[:3,:3]@mat+Ti[:3,3]-target_i)*500)
            Tr=L@F[ring];r.extend((Tr[:3,:3]@mr+Tr[:3,3]-target_r)*500)
            direction=np.array([-1.,0,0])*(1-rollu)+np.array([0.,1,0])*rollu;direction/=np.linalg.norm(direction);r.append(max(0.,.7-(Tr[:3,:3]@rn)@direction)*1.2)
            if a.corner_before_back:
                Tt=L@F[thumb_heel];r.extend((Tt[:3,:3]@mt+Tt[:3,3]-Pt)*450*(1-thumbu))
            r.extend((L[:3,3]-guide[:3,3])*30);r.extend(Rotation.from_matrix(guide[:3,:3].T@L[:3,:3]).as_rotvec()*.5)
            for f in oldg:
                for gap,old in zip(g.gaps(h,L,float(s['slider_q']),f,frames=F,knife_parts=knife_parts),oldg[f]):
                    endpoint=-.0004 if gap['knife_link']=='link_0' and gap['hand_link'] in [index,heel,ring] else .002 if f=='thumb' and gap['knife_link']=='link_0' else .0003
                    release=thumbu if a.corner_before_back and f=='thumb' else smooth((u-.15)/.45) if f=='thumb' else u
                    threshold=(1-release)*min(endpoint,old['gap_lower_bound_m'])+release*endpoint
                    r.append(min(0.,gap['gap_lower_bound_m']-threshold)*1000)
                for v in g.self_gaps(h,f,certify_clearance_m=.0005,frames=F,transformed=transformed,enclosing_spheres=spheres):r.append(min(0.,v['gap_lower_bound_m']-.0005)*250)
            for v in g.pair_gaps(h,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]):r.append(min(0.,v['gap_lower_bound_m']-.0003)*1000)
            r.extend((x-prior)*.03);r.extend((h[16:]-prior[19:23])*.2);return np.array(r)
        if u>0:
            lower=np.r_[k.lower+.06,g.w.lower[ids]+.06,index_lo];upper=np.r_[k.upper-.06,g.w.upper[ids]-.06,index_hi]
            lower[:23]=np.maximum(lower[:23],previous[:23]-.14);upper[:23]=np.minimum(upper[:23],previous[:23]+.14)
            if a.corner_before_back:upper[7+list(ids).index(15)]=min(upper[7+list(ids).index(15)],(1-u)*q0[15]+u*.15)
            fit=least_squares(residual,np.clip(previous,lower+1e-7,upper-1e-7),bounds=(lower,upper),max_nfev=60,diff_step=1e-5);previous=fit.x
        h,L,F=decode(previous);Ti=L@F[index];Tr=L@F[ring];ie=float(np.linalg.norm(Ti[:3,:3]@previous[23:26]+Ti[:3,3]-target_i));re=float(np.linalg.norm(Tr[:3,:3]@mr+Tr[:3,3]-target_r));bad=checker.inspect(h)
        row=dict(time_s=float(t),arm_q=(previous[:7]+s['issued_target'][:7]-arm0).tolist(),hand_q=(h+(s['issued_target'][7:]-q0)*(1-smooth(u/.35))).tolist(),ring_roll_fraction=float(rollu),thumb_release_fraction=float(thumbu))
        if a.corner_before_back:row['hand_q'][16:]=(h[16:]+(s['issued_target'][23:]-q0[16:])*(1-thumbu)).tolist()
        for j in range(16):
            if j not in ids:row['hand_q'][j]=float(s['issued_target'][7+j])
        rows.append(row);d=dict(time_s=float(t),fraction=float(u),planned_arm_q=previous[:7].tolist(),planned_hand_q=h.tolist(),index_material=previous[23:26].tolist(),ring_material=mr.tolist(),ring_original_collision_link=part,ring_normal_local=rn.tolist(),index_error_m=ie,ring_error_m=re,self=bad,expected_object_world=O.tolist());D.append(d);print(json.dumps({k:v for k,v in d.items() if k not in ['planned_arm_q','planned_hand_q','expected_object_world','index_material','ring_material']}),flush=True)
        (a.output/'partial-path.json').write_text(json.dumps(dict(rows=rows,diagnostics=D,source=str(a.source),endpoint=str(a.endpoint),scope='Partial planning checkpoint only, not executable/accepted'),indent=2))
        if max(ie,re)>.001 or bad:break
    guard=dict(complete=len(D)==41,maximum_index_error_m=max(d['index_error_m'] for d in D),maximum_ring_error_m=max(d['ring_error_m'] for d in D),self_frames=sum(bool(d['self']) for d in D),source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),elapsed_s=time.time()-b)
    guard['preflight_pass']=guard['complete'] and max(guard['maximum_index_error_m'],guard['maximum_ring_error_m'])<.0008 and not guard['self_frames']
    (a.output/'path.json').write_text(json.dumps(dict(rows=rows,diagnostics=D,guard=guard,source=str(a.source),endpoint=str(a.endpoint),scope=__doc__),indent=2));e=record('functional_ring_contact_gait_terminal',[str(a.output/'path.json')],config=guard,next_step='Passing geometric gait -> native original forces and contact checks; failed node selects support path change')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(guard)+'\n')
    print(json.dumps(guard));
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
