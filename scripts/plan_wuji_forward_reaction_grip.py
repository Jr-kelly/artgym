"""Joint grip adjustment placing the Middle bearing ahead of the thumb.

Starts from current measured contacts. Other bearings may roll longitudinally;
this is a geometric preparation, never a physical state or acceptance result.
"""
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
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--spec',type=Path);a=p.parse_args()
    spec=json.loads(a.spec.read_text()) if a.spec else {}
    a.output.mkdir(exist_ok=False,parents=True)
    s=np.load(a.source/'takeover.npz');trial,native,end=source_contacts(a.source)
    g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
    k=G2Kinematics();O=transform(s['object_state'][:3],s['object_state'][3:7])
    L0=np.linalg.inv(O)@k.forward(s['robot_q'][:7]);q0=s['robot_q'][7:].astype(float)
    ids=np.r_[0:8,12:20];materials={};points={};normals={};F0=g.w.forward(q0)
    names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_link4','hand_r_thumb_pad_link']
    names+=spec.get('additional_material_links',[])
    for name in names:
        cs=[c for r in native for c in r['contacts'] if c['hand_link']==name]
        if not cs:raise ValueError('Missing actual bearing '+name)
        material=np.mean([c['position_hand_link_m'] for c in cs],0)
        N=np.sum([c['force_normal_contribution_knife_N'] for c in cs],0);N/=np.linalg.norm(N)
        T=L0@F0[name];materials[name]=material
        points[name]=T[:3,:3]@material+T[:3,3];normals[name]=(T[:3,:3].T@N,N)
    targets={n:P.copy() for n,P in points.items()}
    overrides=spec.get('targets',{'hand_r_middle_pad_link':[.0025,-.004,.003]})
    for name,target in overrides.items():targets[name]=np.array(target)
    exact=spec.get('exact_links',['hand_r_middle_pad_link','hand_r_thumb_pad_link'])
    rolling=spec.get('axial_rolling_range_m',.008)
    for name,normal in spec.get('normal_targets',{}).items():
        local,_=normals[name];normal=np.asarray(normal);normals[name]=(local,normal/np.linalg.norm(normal))
    initial_gaps={f:g.gaps(q0,L0,float(s['slider_q']),f) for f in ['index','middle','ring','thumb']}
    lo=np.r_[[-.015]*3,[-.15]*3,g.w.lower[ids]+.04]
    hi=np.r_[[.015]*3,[.15]*3,g.w.upper[ids]-.04]
    x0=np.r_[np.zeros(6),q0[ids]]

    def decode(x):
        L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3]
        q=q0.copy();q[ids]=x[6:];return L,q,g.w.forward(q)

    def residual(x):
        L,q,F=decode(x);r=[]
        for name in names:
            T=L@F[name];P=T[:3,:3]@materials[name]+T[:3,3];d=P-targets[name]
            if name in exact:r.extend(d*350)
            else:
                r.extend(d[:2]*350);r.append(d[2]*10)
                r.append(max(0.,abs(d[2])-rolling)*1000)
            local,normal=normals[name]
            r.extend((T[:3,:3]@local-normal)*spec.get('normal_weight',.3))
        transformed={n:[(v@F[n][:3,:3].T+F[n][:3,3],nn@F[n][:3,:3].T) for v,nn in meshes]
                     for n,meshes in g.meshes.items() if any('_'+f+'_' in n for f in ['index','middle','ring','thumb','pinky'])}
        spheres={}
        for n,parts in transformed.items():
            for i,(v,_) in enumerate(parts):
                C=v.mean(0);spheres[n,i]=(C,np.linalg.norm(v-C,axis=1).max())
        for finger in ['index','middle','ring','thumb']:
            for i,gap in enumerate(g.gaps(q,L,float(s['slider_q']),finger,frames=F)):
                threshold=-.0004 if gap['hand_link'] in names else .0001
                if finger!='middle' and gap['knife_link']=='link_0':
                    threshold=min(threshold,initial_gaps[finger][i]['gap_lower_bound_m'])
                if finger=='thumb' and gap['knife_link']=='link_0':threshold=.0003
                r.append(min(0.,gap['gap_lower_bound_m']-threshold)*500)
            r.extend(min(0.,gap['gap_lower_bound_m']-.0002)*250
                     for gap in g.self_gaps(q,finger,certify_clearance_m=.0002,frames=F,
                                           transformed=transformed,enclosing_spheres=spheres))
        r.extend(x[:3]*3);r.extend(x[3:6]*.1);r.extend((x[6:]-q0[ids])*.015)
        return np.array(r)

    e=record('current_forward_reaction_jointgrip_planning_start',[str(a.output)],config={
        'candidate':spec.get('candidate','C560-R10'),'source':str(a.source),'target_overrides':overrides,
        'support_layout':spec.get('support_layout','Actual Ipad/Ring4/Thumbcap retained transversely; I/R axialrolling8mm allowed; Middle moved forward'),
        'uncertainty':spec.get('uncertainty','Middle-only forwardbearing blocked; does a small jointwrist/grip adjustment open forward reaction lever?'),
        'decision':spec.get('decision','Feasible -> one causalacquisition, otherwise change supporttopology rather than forcebias'),
        'scope':'Planning only, original physics and joints retained'},next_step='Currentcontact constrained jointgrip, no historicalrerun or native until geometrysupports it')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
    started=time.time();fit=least_squares(residual,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=100,diff_step=1e-5)
    L,q,F=decode(fit.x);arm,ik=k.solve_near(O@L,s['robot_q'][:7].astype(float),max_step=1.,minimum_margin=.06)
    actual_L=np.linalg.inv(O)@k.forward(arm);errors={};actual_points={}
    for name in names:
        T=actual_L@F[name];P=T[:3,:3]@materials[name]+T[:3,3];actual_points[name]=P.tolist();errors[name]=float(np.linalg.norm(P-targets[name]))
    bad=HandIntersection().inspect(q)
    r=dict(source=str(a.source),arm_q=arm.tolist(),hand_q=q.tolist(),wrist_in_knife=actual_L.tolist(),
           materials={n:m.tolist() for n,m in materials.items()},targets={n:m.tolist() for n,m in targets.items()},
           planned_points=actual_points,point_errors_m=errors,self_intersections=bad,arm_ik=ik,
           wrist_translation_delta_m=fit.x[:3].tolist(),wrist_rotation_delta_rad=fit.x[3:6].tolist(),
           minimum_hand_margin_rad=float(np.minimum(q-g.w.lower,g.w.upper-q).min()),
           elapsed_s=time.time()-started,nfev=fit.nfev,scope=__doc__,spec=spec)
    r['permits_path']=not bad and all(errors[n]<.0005 for n in exact) and all(np.linalg.norm(np.array(actual_points[n])[:2]-targets[n][:2])<.0005 and abs(actual_points[n][2]-targets[n][2])<rolling+.0005 for n in names if n not in exact)
    (a.output/'endpoint.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
    e=record('current_forward_reaction_jointgrip_planning_terminal',[str(a.output/'endpoint.json')],config=r,
             next_step='Feasible -> causal movingbearing path and native; blocked -> layout/topology change with exact geometric bottleneck')
    with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')


if __name__=='__main__':main()
