"""Acquire backside ring support while retaining three actual loaded carriers.

Coordinates the wrist and digits around the fixed-wrist ring abduction barrier.
All geometry is a motor reference; native contact and tracking must follow.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser()
    for n in ['source','endpoint','output']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--endpoint-only',action='store_true')
    p.add_argument('--reverse-endpoint',type=Path)
    p.add_argument('--knots',type=int,default=65)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');c=json.loads(a.endpoint.read_text());k=G2Kinematics()
    g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    O=transform(s['object_state'][:3],s['object_state'][3:7]);arm0=s['robot_q'][:7].astype(float);q0=s['robot_q'][7:].astype(float);W0=k.forward(arm0);L0=np.linalg.inv(O)@W0
    _,native,_=source_contacts(a.source);carrier_ids={'hand_r_index_pad_link':[0,1,2,3],'hand_r_middle_pad_link':[4,5,6,7],'hand_r_thumb_link4':[16,17,18,19]}
    materials={n:np.mean([v['position_hand_link_m'] for r in native for v in r['contacts'] if v['hand_link']==n and v['knife_link']=='link_0'],axis=0) for n in carrier_ids}
    F0=g.w.forward(q0);targets={n:(L0@F0[n])[:3,:3]@m+(L0@F0[n])[:3,3] for n,m in materials.items()}
    normals={n:(L0@F0[n])[:3,0] for n in materials}
    ring='hand_r_ring_pad_link';V=np.concatenate([v for v,_ in g.meshes[ring]])
    gaps0={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','thumb','ring','pinky']}
    def decode(x):
        h=x[7:];W=k.forward(x[:7]);L=np.linalg.inv(O)@W;F=g.w.forward(h);T=L@F[ring];v=V@T[:3,:3].T+T[:3,3];w=np.exp((v[:,1]-v[:,1].max())/.00015)
        return h,W,L,F,w@v/w.sum()
    initial=np.r_[arm0,q0];P0=decode(initial)[-1];end=np.r_[arm0,c['hand_q']];seed=end.copy() if a.endpoint_only else initial.copy();rows=[];D=[];checker=HandIntersection()
    if a.reverse_endpoint:
        endpoint=json.loads(a.reverse_endpoint.read_text())['diagnostics'][-1]
        end=np.r_[endpoint['planned_arm_q'],endpoint['planned_hand_q']];seed=end.copy()
    knife_parts=g.knife_geometry.collision_parts(float(s['slider_q']))
    record('direct_coordinated_underpad_path_start',[str(a.output)],config={'source':str(a.source),'uncertainty':'Fixedwrist ring -Y waypoint reaches joint2 planningbound; can wrist coordinate while actual I/M/thumb material contacts remain?', 'fixed_carriers':list(materials),'free_ring_body_clearance_m':.002},next_step='Fullguard before one native; acquired backside ring then actual supportedthumbcap')
    times=np.array([8.]) if a.endpoint_only else np.linspace(0,8,a.knots)
    if a.reverse_endpoint:times=times[::-1]
    for t in times:
        u=smooth((t-.5)/6);previous=seed.copy();prior=initial*(1-u)+end*u;target=P0*(1-u)+np.array(c['target'])*u
        def threshold(gap,old,finger):
            if finger=='ring':
                free=.0002+.0018*smooth(u/.25)*(1-smooth((u-.75)/.2))
                finish=-.001 if gap['hand_link']==ring and gap['knife_link']=='link_0' else .0002
                release=smooth(u/.25);approach=smooth((u-.75)/.25)
                return (1-release)*min(.0002,old['gap_lower_bound_m'])+release*((1-approach)*free+approach*finish)
            return min(.0001,old['gap_lower_bound_m']) if finger!='pinky' else .0002
        def residual(x):
            h,W,L,F,P=decode(x);r=[]
            transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],normals@F[n][:3,:3].T) for v,normals in meshes] for n,meshes in g.meshes.items() if any('_'+f+'_' in n for f in gaps0)}
            spheres={}
            for n,parts in transformed.items():
                for i,(v,_) in enumerate(parts):
                    centre=v.mean(0);spheres[n,i]=(centre,np.linalg.norm(v-centre,axis=1).max())
            for n,m in materials.items():
                T=L@F[n];r.extend((T[:3,:3]@m+T[:3,3]-targets[n])*350);r.extend((T[:3,0]-normals[n])*.2)
            r.extend((P-target)*(30+320*smooth((u-.85)/.15)))
            for finger in gaps0:
                for v,old in zip(g.gaps(h,L,float(s['slider_q']),finger,frames=F,knife_parts=knife_parts),gaps0[finger]):r.append(min(0,v['gap_lower_bound_m']-threshold(v,old,finger))*1500)
                r.extend(min(0,v['gap_lower_bound_m']-.0001)*180 for v in g.self_gaps(h,finger,certify_clearance_m=.0001,frames=F,transformed=transformed,enclosing_spheres=spheres))
            r.extend((W[:3,3]-W0[:3,3])*10);r.extend(Rotation.from_matrix(W0[:3,:3].T@W[:3,:3]).as_rotvec()*.3)
            r.extend((x-prior)*.02);r.extend((h[8:12]-q0[8:12])*.2);r.extend((h[12:16]-prior[19:23])*.2)
            return np.array(r)
        if u==0 and a.reverse_endpoint:seed=initial.copy()
        if u>0:
            lo=np.maximum(np.r_[k.lower+.06,g.w.lower+.06],previous-.13);hi=np.minimum(np.r_[k.upper-.06,g.w.upper-.06],previous+.13)
            lo[15:19]=np.maximum(lo[15:19],q0[8:12]-.3);hi[15:19]=np.minimum(hi[15:19],q0[8:12]+.3)
            fit=least_squares(residual,np.clip(seed,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100 if a.endpoint_only else 55,diff_step=1e-5);seed=fit.x
        h,W,L,F,P=decode(seed);support_errors={n:float(np.linalg.norm((L@F[n])[:3,:3]@m+(L@F[n])[:3,3]-targets[n])) for n,m in materials.items()}
        violations=[]
        for finger in gaps0:
            violations.extend(max(0,threshold(v,old,finger)-v['gap_lower_bound_m']) for v,old in zip(g.gaps(h,L,float(s['slider_q']),finger),gaps0[finger]))
        command=h.copy();command+=s['issued_target'][7:]-q0;command[8:16]=h[8:16]+(s['issued_target'][15:23]-q0[8:16])*(1-smooth(u/.25))
        rows.append(dict(time_s=float(t),arm_q=(seed[:7]+s['issued_target'][:7]-arm0).tolist(),hand_q=command.tolist()))
        d=dict(time_s=float(t),fraction=float(u),thumb_error_m=0.,ring_error_m=float(np.linalg.norm(P-np.array(c['target']))),ring_point_m=P.tolist(),support_errors_m=support_errors,maximum_gap_violation_m=max(violations),self_intersections=checker.inspect(h),planned_hand_q=h.tolist(),planned_arm_q=seed[:7].tolist(),expected_object_world=O.tolist(),planned_support_materials={n:m.tolist() for n,m in materials.items()})
        D.append(d);print(json.dumps({key:value for key,value in d.items() if key not in ['planned_hand_q','planned_arm_q','expected_object_world','planned_support_materials']}),flush=True)
        if max(support_errors.values())>.001 or max(violations)>.00015 or d['self_intersections']:break
    rows.sort(key=lambda v:v['time_s']);D.sort(key=lambda v:v['time_s'])
    adjacent=float(np.abs(np.diff(np.array([np.r_[d['planned_arm_q'],d['planned_hand_q']] for d in D]),axis=0)).max()) if len(D)>1 else 0.
    guard=dict(complete=len(D)==len(times),maximum_support_error_m=max(max(d['support_errors_m'].values()) for d in D),maximum_gap_violation_m=max(d['maximum_gap_violation_m'] for d in D),self_frames=sum(bool(d['self_intersections']) for d in D),terminal_ring_error_m=D[-1]['ring_error_m'],largest_adjacent_joint_step_rad=adjacent)
    guard['preflight_pass']=guard['complete'] and guard['maximum_support_error_m']<.0008 and guard['terminal_ring_error_m']<.0005 and not guard['self_frames'] and adjacent<.18
    (a.output/'motor.json').write_text(json.dumps(dict(rows=rows,diagnostics=D,guard=guard,source=str(a.source),scope=__doc__),indent=2));(a.output/'carriers.json').write_text(json.dumps([dict(material_link=n,material_point=m.tolist(),digit_indices=carrier_ids[n],knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json') for n,m in materials.items()],indent=2))
    record('direct_coordinated_underpad_path_terminal',[str(a.output/'motor.json')],config=guard,next_step='Passing actualcarrier path -> preloadtransport/native8s; reject exact first constraint without changing physicallimits')
    print(json.dumps(guard))
    if not guard['preflight_pass']:raise SystemExit(2)

if __name__=='__main__':main()
