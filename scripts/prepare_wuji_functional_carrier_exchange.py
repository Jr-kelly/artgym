"""Actual I/M/thumb carriers hold while a freed Ring enters the backface.

All object poses are planning references. Only finite motor commands are
executed; original native dynamics determine support and contact transfer.
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
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');c=json.load(a.endpoint.open());q0=s['robot_q'][7:].astype(float);arm0=s['robot_q'][:7].astype(float)
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7]);L0=np.linalg.inv(O)@k.forward(arm0);F0=g.w.forward(q0)
    _,native,end=source_contacts(a.source)
    I='hand_r_index_pad_link';M='hand_r_middle_pad_link';T='hand_r_thumb_link4';R='hand_r_ring_pad_link';names=[I,M,T];materials={};points={};hulls={};facets={};lofoot=[];hifoot=[]
    for n in names:
        C=[v for r in native if r['time_s']>end-.2 for v in r['contacts'] if v['hand_link']==n];m=np.mean([v['position_hand_link_m'] for v in C],0);force=np.sum([v['force_normal_contribution_knife_N'] for v in C],0);force/=np.linalg.norm(force);V=np.concatenate([v for v,_ in g.meshes[n]]);H=ConvexHull(V).equations;N=(L0@F0[n])[:3,:3].T@force
        eligible=np.abs(H[:,:3]@m+H[:,3])<.0006;score=H[:,:3]@N;score[~eligible]=-10.;f=int(score.argmax());m=m-H[f,:3]*(H[f,:3]@m+H[f,3]);materials[n]=m;hulls[n]=H;facets[n]=f;B=L0@F0[n];points[n]=B[:3,:3]@m+B[:3,3];lofoot.extend(np.maximum(V.min(0),m-.008));hifoot.extend(np.minimum(V.max(0),m+.008))
    rm=np.array(c['ring_material']);rn=np.array(c['ring_local_normal']);B=L0@F0[R];startR=B[:3,:3]@rm+B[:3,3];goalR=np.array(c['ring_target']);viaR=np.array([.002,min(startR[1],-.025),goalR[2]])
    ids=np.r_[0:8,12:20];initial=np.r_[arm0,q0[ids],np.concatenate([materials[n] for n in names])];Lend=np.array(c['wrist_in_knife']);endarm,_=k.solve_near(O@Lend,arm0,max_step=2.,minimum_margin=.06);priorend=np.r_[endarm,np.array(c['hand_q'])[ids],np.concatenate([np.array(c['support_materials'].get(n,materials[n])) for n in names])];delta=Rotation.from_matrix(L0[:3,:3].T@Lend[:3,:3]).as_rotvec();previous=initial.copy();rows=[];D=[];checker=HandIntersection();oldg={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','ring','thumb']};knife_parts=g.knife_geometry.collision_parts(float(s['slider_q']))
    record('functional_free_ring_exchange_start',[str(a.output)],config={'source':str(a.source),'endpoint':str(a.endpoint),'uncertainty':'Can actual I/M/T clamp remain while freed Ring approaches true backpad without forced corner rolling?','changed':'Native464 wholly Ringfree, Middleback0.436N; true retained facets allow8mm rolling, I/M migrate+15/+8mmZ; Ring free detour outside back, thumb exits only after Ring approach','decision':'First geometric blockage changes carrier/route; full guarded path -> original native contact support test'},next_step='Free Ringback carrier path then native')
    began=time.time()
    for t in np.linspace(0,10,41):
        u=smooth((t-.5)/8);ru=smooth(u/.8);tu=smooth((u-.8)/.2);targetR=(1-ru)**2*startR+2*(1-ru)*ru*viaR+ru**2*goalR;guide=L0.copy();guide[:3,3]=(1-u)*L0[:3,3]+u*Lend[:3,3];guide[:3,:3]=L0[:3,:3]@Rotation.from_rotvec(delta*u).as_matrix();prior=(1-u)*initial+u*priorend
        targets={I:(1-u)*points[I]+u*np.array(c['support_points'][I]),M:(1-u)*points[M]+u*np.array(c['support_points'][M]),T:points[T]+np.array([0.,0.,.008*u])}
        def decode(x):
            h=q0.copy();h[ids]=x[7:23];L=np.linalg.inv(O)@k.forward(x[:7]);return h,L,g.w.forward(h)
        def residual(x):
            h,L,F=decode(x);r=[];transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in parts] for n,parts in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])};spheres={}
            for n,parts in transformed.items():
                for j,(v,_) in enumerate(parts):
                    centre=v.mean(0);spheres[n,j]=(centre,np.linalg.norm(v-centre,axis=1).max())
            for j,n in enumerate(names):
                m=x[23+3*j:26+3*j];H=hulls[n];value=H[:,:3]@m+H[:,3];r.extend(np.maximum(value,0)*1200);r.append(value[facets[n]]*1200);B=L@F[n];r.extend((B[:3,:3]@m+B[:3,3]-targets[n])*500*(1-tu if n==T else 1.))
            B=L@F[R];r.extend((B[:3,:3]@rm+B[:3,3]-targetR)*(70+430*smooth((u-.55)/.25)));direction=(1-ru)*(L0@F0[R])[:3,:3]@rn+ru*np.array([0.,1.,0.]);direction/=np.linalg.norm(direction);r.append(max(0.,.75-(B[:3,:3]@rn)@direction)*1.2)
            r.extend((L[:3,3]-guide[:3,3])*35);r.extend(Rotation.from_matrix(guide[:3,:3].T@L[:3,:3]).as_rotvec()*.7)
            for f in oldg:
                for gap,old in zip(g.gaps(h,L,float(s['slider_q']),f,frames=F,knife_parts=knife_parts),oldg[f]):
                    if f=='ring':
                        threshold=.001*(1-smooth((u-.55)/.25))+(-.0004 if gap['hand_link']==R and gap['knife_link']=='link_0' else .0003)*smooth((u-.55)/.25)
                    elif f=='thumb':threshold=(1-tu)*min(.0001,old['gap_lower_bound_m'])+tu*(.002 if gap['knife_link']=='link_0' else .001)
                    else:threshold=min(-.0003,old['gap_lower_bound_m']) if gap['hand_link'] in [I,M] and gap['knife_link']=='link_0' else (1-u)*min(.0003,old['gap_lower_bound_m'])+u*.0003
                    r.append(min(0.,gap['gap_lower_bound_m']-threshold)*1000)
                r.extend(min(0.,v['gap_lower_bound_m']-.0005)*250 for v in g.self_gaps(h,f,certify_clearance_m=.0005,frames=F,transformed=transformed,enclosing_spheres=spheres))
            for v in g.pair_gaps(h,[('hand_r_base_link','hand_r_thumb_link3'),('hand_r_base_link','hand_r_thumb_link4'),('hand_r_base_link','hand_r_thumb_pad_link')]):r.append(min(0.,v['gap_lower_bound_m']-.0003)*1000)
            r.extend((x-prior)*.035);return np.array(r)
        if u>0:
            lower=np.r_[k.lower+.06,g.w.lower[ids]+.06,lofoot];upper=np.r_[k.upper-.06,g.w.upper[ids]-.06,hifoot];lower[:23]=np.maximum(lower[:23],previous[:23]-.14);upper[:23]=np.minimum(upper[:23],previous[:23]+.14)
            fit=least_squares(residual,np.clip(previous,lower+1e-7,upper-1e-7),bounds=(lower,upper),max_nfev=45,diff_step=1e-5);previous=fit.x
        h,L,F=decode(previous);errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@previous[23+3*j:26+3*j]+(L@F[n])[:3,3]-targets[n])) for j,n in enumerate(names)};B=L@F[R];re=float(np.linalg.norm(B[:3,:3]@rm+B[:3,3]-targetR));bad=checker.inspect(h)
        command=h+(s['issued_target'][7:]-q0)*(1-smooth(u/.35));command[16:]=h[16:]+(s['issued_target'][23:]-q0[16:])*(1-tu);rows.append(dict(time_s=float(t),arm_q=(previous[:7]+s['issued_target'][:7]-arm0).tolist(),hand_q=command.tolist(),ring_roll_fraction=float(smooth((u-.6)/.2)),thumb_release_fraction=float(tu)))
        d=dict(time_s=float(t),fraction=float(u),planned_arm_q=previous[:7].tolist(),planned_hand_q=h.tolist(),index_material=previous[23:26].tolist(),middle_material=previous[26:29].tolist(),thumb_heel_material=previous[29:32].tolist(),ring_material=rm.tolist(),ring_normal_local=rn.tolist(),index_error_m=errors[I],middle_error_m=errors[M],thumb_error_m=errors[T],ring_error_m=re,self=bad,expected_object_world=O.tolist());D.append(d);print(json.dumps(dict(time_s=float(t),fraction=float(u),support_errors_m=errors,ring_error_m=re,self=bad)),flush=True);(a.output/'partial-path.json').write_text(json.dumps(dict(rows=rows,diagnostics=D,source=str(a.source),endpoint=str(a.endpoint)),indent=2))
        if max(errors[I],errors[M],errors[T]*(1-tu))>.001 or (u>.7 and re>.001) or bad:break
    guard=dict(complete=len(D)==41,maximum_index_error_m=max(v['index_error_m'] for v in D),maximum_middle_error_m=max(v['middle_error_m'] for v in D),terminal_ring_error_m=D[-1]['ring_error_m'],self_frames=sum(bool(v['self']) for v in D),source_jump_rad=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max()),elapsed_s=time.time()-began);guard['preflight_pass']=guard['complete'] and max(guard['maximum_index_error_m'],guard['maximum_middle_error_m'],guard['terminal_ring_error_m'])<.0008 and not guard['self_frames'];out=dict(rows=rows,diagnostics=D,guard=guard,source=str(a.source),endpoint=str(a.endpoint),scope=__doc__);(a.output/'path.json').write_text(json.dumps(out,indent=2));e=record('functional_free_ring_exchange_terminal',[str(a.output/'path.json')],config=guard,next_step='Passed -> normaltransport/leveling motor guard then native; failed -> actual carrier capacity or free route change')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+str(a.output)+' '+json.dumps(guard)+'\n')
    print(json.dumps(guard),flush=True)
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
