"""Functional tabletop edge-grasp planning with real knife collisions.

Three supporting pads are placed near the overhanging handle end, thumb on
the slider. The object COM remains on the tabletop. CPU geometry, no success claim.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,minimize
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import FINGERS

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--thumb-contact-axis',choices=['x','z'],default='x',help='Explicit authored pad face-axis geometry hypothesis; not real material calibration')
    p.add_argument('--thumb-axis-facing-min',type=float,default=.5,help='Declared geometric face-axis alignment for start/full40 endpoint; original contact/limits retained')
    p.add_argument('--seed-contact-topology',action='store_true',help='Use matched source contact directions and finite axial region centers instead of legacy named-layout directions; wrist remains source-bounded');p.add_argument('--index-under-support',action='store_true',help='Distinct measured-contact topology: index distal pad on underside with optional adjacent link region, preserve original40mm thumb and collisions');p.add_argument('--clip-wrap-facets',action='store_true',help='Use original true facet clipped against objectface rectangle instead of global representative point for additional regions');p.add_argument('--longitudinal-recenter',type=float,default=0.,help='Distinct held wrap regime: shift wrist alongknife axis before fitting, bounded12mm region; preserve40mmthumb task');p.add_argument('--wrap-regions',type=Path,help='Additional actual link/region contacts including multiple links per finger or palm; original meshes and collision constraints unchanged');p.add_argument('--front-thumb-contact',action='store_true',help='Require thumb authored pad+X face towards cap, at start and40mmendpoint, instead of any hullfacet; anatomicalgeometry hypothesis, notforce');p.add_argument('--front-pad-support',action='store_true',help='Require support distal pad authored front-axis alignment, rather than relaxed edge contact; geometric hypothesis only');p.add_argument('--retain-pickup-support',type=Path,help='Keep wrist and middle/pinky touch coordinates from a working actualpickup, change index contact topology and thumbstroke; originalcollisions unchanged');p.add_argument('--support-contact-link',choices=['pad_link','link3'],default='pad_link',help='Support using actual authored distalpads or proximalfinger collisionmeshes; thumbalwaysoriginalpad, no geometry changes');p.add_argument('--table-preform',action='store_true',help='Pick up with new wrist/side topology but underside fingers at exposedtableedge; originaltableconstraint remains active');p.add_argument('--support-joint-margin',type=float,default=.015);p.add_argument('--support-axial-half-span',type=float,default=.015);p.add_argument('--revision',type=int,choices=[2,3,4],default=2);p.add_argument('--layout',choices=['deep','opposed','rolled','bilateral','proximal'],required=True);p.add_argument('--held-only',action='store_true');p.add_argument('--output',type=Path,required=True);p.add_argument('--root-inset',type=float,default=.008);p.add_argument('--y',type=float,default=-.25);p.add_argument('--refine',type=Path);p.add_argument('--three-support',action='store_true');p.add_argument('--self-separation',action='store_true');p.add_argument('--positive-end-two-support',action='store_true');p.add_argument('--side-edge-all-support',action='store_true');p.add_argument('--source',type=int,choices=range(4));p.add_argument('--maximum-pad-gap',type=float,default=0.);p.add_argument('--thumb-joint-margin',type=float,default=.015);p.add_argument('--thumb-contact-x',type=float);p.add_argument('--longside-three-support',action='store_true');p.add_argument('--under-edge-support',action='store_true',help='Support the exposed lower knife face with opposed vertical normals; all table/self collisions retained');p.add_argument('--stroke-span',type=float,default=0.,help='Jointly screen a second thumb configuration at declared slider travel; geometric hypothesis only');p.add_argument('--preload-plan',type=Path,help='Offline fixed nominal motor preload offsets; constrain loaded table/self geometry, original limits, then recompute force equilibrium and test physics');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    g=DigitGeometry(max_face_axes=24,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;k=G2Kinematics();knife=g.knife_geometry
    wrap_regions=json.loads(a.wrap_regions.read_text()) if a.wrap_regions else []
    preload=None
    if a.preload_plan:
        loaded=json.loads(a.preload_plan.read_text());preload=np.array(loaded.get('post_lift_close_q',loaded['close_q']))-loaded['touch_q']
    world=transform([.30+a.root_inset,a.y,.7561],(Rotation.from_euler('z',0 if a.side_edge_all_support else -90 if a.positive_end_two_support else 90,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());parts=knife.collision_parts(-.03267458688196273)
    table_center=np.array([.60,-.25,.725]);table_half=np.array([.30,.40,.025]);normal=np.array([[0,1.,0]]+[[0,-1.,0]]*4)
    contact_links={f:'hand_r_'+f+'_'+('pad_link' if f=='thumb' else a.support_contact_link) for f in FINGERS}
    vertices={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};axes={n:np.concatenate([v for _,v in m]) for n,m in g.meshes.items()}
    if a.refine:
        seed_plan=json.loads(a.refine.read_text());seed_relative=np.linalg.inv(np.asarray(seed_plan['wrist_in_knife']));seed=np.r_[seed_plan['touch_q'],seed_plan['touch_q'],seed_relative[:3,3],Rotation.from_matrix(seed_relative[:3,:3]).as_quat()];seeds=np.tile(seed,(4,1))
    else:
        seeds=np.load('research/real-size-student-adaptation-20261002/data/real/adapted-seeds.npy')
    target_z=np.array([-.02205,-.015,-.029,-.043,-.055])
    active=np.array([0,1,2,3] if a.three_support else [0,1,2,3,4]);
    if a.three_support:target_z=np.array([-.02205,-.015,-.035,-.055,-.07])
    if a.positive_end_two_support:
        active=np.array([0,1,2]);target_z=np.array([-.02205,.039,.019,-.022,-.047])
    if a.side_edge_all_support:
        active=np.array([0,1,2,4]) if a.longside_three_support else np.arange(5);target_z=np.array([-.02205,.039,.001,-.022,-.047])
        normal[1:]=np.array([0.,-1.,0.]) if a.under_edge_support else np.array([-1.,-1.,0.])/np.sqrt(2)
    # Three different contact relationships, not millimetre variants of one underside pattern.
    if a.layout=='deep':
        active=np.array([0,1,2,3,4]);target_z=np.array([-.02205,.035,.007,-.020,-.046])
        normal[1:]=np.array([[0.,-1.,0.],[0.,-1.,0.],[1.,0.,0.],[1.,0.,0.]])
    elif a.layout=='opposed':
        active=np.array([0,1,2,3,4]);target_z=np.array([-.02205,.038,.012,-.012,-.044])
        normal[1:]=np.array([[-1.,0.,0.],[0.,-1.,0.],[1.,0.,0.],[0.,-1.,0.]])
    elif a.layout in ['bilateral','proximal']:
        active=np.array([0,1,2,4]);target_z=np.array([-.02205,.035,.005,-.020,-.045]);normal[1:]=np.array([[0.,-1.,0.],[-1.,0.,0.],[0.,-1.,0.],[1.,0.,0.]])
    else:
        active=np.array([0,1,2,4]);target_z=np.array([-.02205,.025,-.010,-.030,-.054])
        normal[1:]=np.array([[-1.,0.,0.],[0.,-1.,0.],[0.,-1.,0.],[1.,0.,0.]])
    if a.revision>=3:
        active=np.array([0,1,2,4]) # Ring is optional, not a mandatory target.
        if a.layout=='rolled':normal[1:]=np.array([[1.,0.,0.],[0.,-1.,0.],[0.,-1.,0.],[0.,-1.,0.]])
    if a.seed_contact_topology:
        assert a.refine and a.layout in ['bilateral','proximal']
        normal=np.asarray(seed_plan['contact_normals'],dtype=float).copy();target_z=np.asarray(seed_plan['contact_points'])[:,2].copy();target_z[0]=-.02205
    if a.index_under_support:normal[1]=np.array([0.,-1.,0.])
    facing_target=np.full(5,.35);facing_floor=np.full(5,.25)
    if a.side_edge_all_support:
        # Body supports may use a pad edge. Only the operating thumb must face the slider.
        facing_target[1:]=0.;facing_floor[1:]=0.
    if a.front_pad_support:
        facing_target[1:]=.65;facing_floor[1:]=.5
    assert .5<=a.thumb_axis_facing_min<=.85
    if a.front_thumb_contact:facing_target[0]=min(.95,max(.65,a.thumb_axis_facing_min+.1));facing_floor[0]=a.thumb_axis_facing_min
    retained_points=np.array(json.loads(a.retain_pickup_support.read_text())['contact_points']) if a.retain_pickup_support else None
    def desired_contacts(contact):
        target=np.c_[np.clip(contact[:,0],-.004,.004),[.0092,-.0062,-.0062,-.0062,-.0062],target_z]
        if a.side_edge_all_support:target[1:,0]=-.006 if a.under_edge_support else -.0082
        if a.thumb_contact_x is not None:target[0,0]=a.thumb_contact_x
        for i in range(1,5):
            if abs(normal[i,0])>.5:target[i,:2]=[normal[i,0]*.0082,-.0035 if a.layout in ['bilateral','proximal'] else -.001]
            else:target[i,:2]=[-.0062 if a.table_preform else -.003 if a.layout in ['bilateral','proximal'] else 0.,-.0062]
        if a.revision>=3:
            # Axial location is free inside separate finite support regions: this screens wrapping, not exact fingertips.
            target[1:,2]=np.clip(contact[1:,2],target_z[1:]-a.support_axial_half_span,target_z[1:]+a.support_axial_half_span)
            if a.thumb_contact_x is None:target[0,0]=np.clip(contact[0,0],-.0035,.0035)
        if retained_points is not None:
            for f in ['middle','pinky']:target[FINGERS.index(f)]=retained_points[FINGERS.index(f)]
        return target
    contact_hulls={}
    for finger in FINGERS:
        v=vertices[contact_links[finger]];hull=ConvexHull(v);contact_hulls[finger]=(v[hull.simplices].mean(1),hull.equations[:,:3])
    self_pairs=[]
    if a.self_separation:
        names=list(vertices)
        def digit(name):return next((f for f in FINGERS if '_'+f+'_' in name),None)
        for i,n in enumerate(names):
            for m in names[i+1:]:
                if digit(n)==digit(m):continue
                other=m if digit(n) is None else n if digit(m) is None else None
                if other is not None and other.endswith(('link1','link2')):continue
                self_pairs.append((n,m))
    def geometry(x,collision_parts=None):
        wrist=transform(x[:3]);wrist[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();q=x[6:26];frames={n:wrist@mat for n,mat in h.forward(q).items()};vs={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in vertices.items()};contact=[];facing=[];clear=[];table=[];pad_gap=np.full(5,np.inf)
        for f,n in zip(FINGERS,normal):
            name=contact_links[f];v=vs[name];pr=v@n;weights=np.exp(-(pr-pr.min())/.0002);weights/=weights.sum();contact.append(weights@v);facing.append(frames[name][:3,0]@(-n))
        if a.revision>=4:
            # Proximal links do not share the distal pad's local-X contact
            # axis. Use the actual supporting hull facets for those meshes.
            for index,finger in enumerate(FINGERS):
                if index and a.support_contact_link=='pad_link':continue
                centers,normals=contact_hulls[finger];frame=frames[contact_links[finger]];projection=(centers@frame[:3,:3].T+frame[:3,3])@normal[index];support=projection<=(vs[contact_links[finger]]@normal[index]).min()+.0004
                facing[index]=float((normals@frame[:3,:3].T@(-normal[index]))[support].max()) if support.any() else -1.
        if a.front_thumb_contact:facing[0]=float(frames[contact_links['thumb']][:3,0 if a.thumb_contact_axis=='x' else 2]@(-normal[0]))
        for name,v in vs.items():
            normals=axes[name]@frames[name][:3,:3].T
            for part in parts if collision_parts is None else collision_parts:
                ax=np.r_[normals,part['normals']];pa=v@ax.T;pb=part['vertices']@ax.T;gap=np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max();clear.append(gap)
                for index,finger in enumerate(FINGERS):
                    if name==contact_links[finger] and part['link']==('link_1' if index==0 else 'link_0'):pad_gap[index]=min(pad_gap[index],gap)
            vw=v@world[:3,:3].T+world[:3,3];ax=np.r_[np.eye(3),normals@world[:3,:3].T];pv=(vw-table_center)@ax.T;radius=abs(ax)@table_half;table.append(np.maximum(pv.min(0)-radius,-radius-pv.max(0)).max())
        for n,m in self_pairs:
            ax=np.r_[axes[n]@frames[n][:3,:3].T,axes[m]@frames[m][:3,:3].T];pa=vs[n]@ax.T;pb=vs[m]@ax.T;clear.append(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
        return wrist,q,np.array(contact),np.array(facing),np.array(clear),np.full(len(table),.1) if a.held_only else np.array(table),pad_gap
    region_hulls={r['link']:ConvexHull(vertices[r['link']]) for r in wrap_regions}
    def region_geometry(x):
        wrist=transform(x[:3]);wrist[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();frames={n:wrist@m for n,m in h.forward(x[6:26]).items()};out=[]
        for region in wrap_regions:
            name=region['link'];n=np.array(region['normal_knife']);frame=frames[name];v=vertices[name]@frame[:3,:3].T+frame[:3,3];projection=v@n;weights=np.exp(-(projection-projection.min())/.0002);weights/=weights.sum();point=weights@v;lo=np.array(region['point_lower_m']);hi=np.array(region['point_upper_m']);target=np.clip(point,lo,hi)
            if region.get('authored_pad_front',False):facing=float(frame[:3,0]@(-n))
            else:
                hull=ConvexHull(vertices[name]);centers=vertices[name][hull.simplices].mean(1)@frame[:3,:3].T+frame[:3,3];mask=(centers@n)<=projection.min()+.0005;facings=hull.equations[:,:3]@frame[:3,:3].T@(-n);facing=float(facings[mask].max()) if mask.any() else -1.
            if a.clip_wrap_facets:
                from scripts.wuji_contact_region_geometry import surface_region
                hull=region_hulls[name];clipped=surface_region(v,hull.simplices,hull.equations[:,:3]@frame[:3,:3].T,n,lo,hi,region.get('facing_cosine_min',.5))
                if clipped is not None:point,facing=clipped;target=np.clip(point,lo,hi)
            out.append(dict(link=name,point=point,target=target,error=float(np.linalg.norm(point-target)),facing=facing))
        return out
    def loaded_table_self(x):
        shifted=x.copy();shifted[6:26]+=preload
        loaded_w,loaded_q,_,_,_,loaded_table,_=geometry(shifted)
        frames=h.forward(loaded_q);vs={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in vertices.items()};gaps=[]
        for n,m in self_pairs:
            ax=np.r_[axes[n]@frames[n][:3,:3].T,axes[m]@frames[m][:3,:3].T];pa=vs[n]@ax.T;pb=vs[m]@ax.T;gaps.append(float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()))
        return loaded_table,np.array(gaps)
    thumb_indices=[h.names.index('hand_r_thumb_joint'+str(index)) for index in range(1,5)]
    stroke_parts=knife.collision_parts(-.03267458688196273+a.stroke_span)
    def stroke_geometry(x):
        endpoint=x[:26].copy();endpoint[6+np.array(thumb_indices)]=x[26:30];return geometry(endpoint,stroke_parts)
    def residual(x,seed):
        w,q,c,f,clear,table,pad_gap=geometry(x);target=desired_contacts(c)
        value=np.r_[(c[active]-target[active]).ravel()*250,np.minimum(f[active]-facing_target[active],0)*2,np.minimum(clear-.000015,0)*600,np.minimum(table-.0005,0)*800,(q-seed)*.01]
        for region,r in zip(wrap_regions,region_geometry(x)):
            value=np.r_[value,(r['point']-r['target'])*250,min(r['facing']-region.get('facing_cosine_min',.5),0)*2]
        if preload is not None:
            loaded_table,loaded_self=loaded_table_self(x);value=np.r_[value,np.minimum(loaded_table-.0005,0)*800,np.minimum(loaded_self-.000015,0)*600]
        if a.maximum_pad_gap:value=np.r_[value,np.maximum(pad_gap[active]-a.maximum_pad_gap,0)*800]
        if a.stroke_span:
            _,_,endc,endf,endclear,_,endgap=stroke_geometry(x);endtarget=desired_contacts(c)[0]+np.array([0,0,a.stroke_span])
            endpoint_error=endc[0]-endtarget
            if a.revision>=4:endpoint_error[0]=endc[0,0]-np.clip(endc[0,0],-.0045,.0045)
            value=np.r_[value,endpoint_error*250,min(endf[0]-(facing_target[0] if a.front_thumb_contact else .35),0)*2,np.minimum(endclear-.000015,0)*600,max(endgap[0]-.0001,0)*800]
        return value
    rows=[]
    if a.refine:
        source=a.source if a.source is not None else 3;seeds=seeds[source:source+1]
    elif a.source is not None:seeds=seeds[a.source:a.source+1]
    for j,s in enumerate(seeds):
        begin=time.monotonic();w=np.linalg.inv(transform(s[40:43],s[43:47]));x=np.r_[w[:3,3],Rotation.from_matrix(w[:3,:3]).as_rotvec(),s[:20]];lo=np.r_[w[:3,3]-.06,x[3:6]-.8,h.lower+.015];hi=np.r_[w[:3,3]+.06,x[3:6]+.8,h.upper-.015]
        if a.refine:
            prior=json.loads(a.refine.read_text());w=np.asarray(prior['wrist_in_knife']);x=np.r_[w[:3,3],Rotation.from_matrix(w[:3,:3]).as_rotvec(),prior['touch_q']];lo[:3]-=.02;hi[:3]+=.02;lo[3:6]-=.3;hi[3:6]+=.3
        # Distinct wrist regimes fixed as nominal planning constraints; no runtime truth selection.
        old_w=np.asarray(json.loads(Path('research/robust-knife-family-20261003/functional-side-edge-under-support-v6/functional-edge-0.json').read_text())['wrist_in_knife']) if a.revision>=3 else w.copy()
        if a.layout=='deep':
            center=old_w[:3,3].copy();center[0]+=.022;center[1]-=.012
            x[:3]=center;lo[:3]=center-.012;hi[:3]=center+.012
            # Keep wrist materially deeper than original layout.
            lo[0]=old_w[0,3]+.014;hi[0]=old_w[0,3]+.035
        elif a.layout=='rolled':
            rot=Rotation.from_euler('z',-25 if a.revision>=3 else 35,degrees=True).as_matrix();new=rot@old_w[:3,:3]
            x[3:6]=Rotation.from_matrix(new).as_rotvec();lo[3:6]=x[3:6]-.18;hi[3:6]=x[3:6]+.18
            x[2]=old_w[2,3]+.018;lo[2]=old_w[2,3]+.010;hi[2]=old_w[2,3]+.030
        else:
            lo[:3]=w[:3,3]-.03;hi[:3]=w[:3,3]+.03
        thumb_indices=[h.names.index('hand_r_thumb_joint'+str(index)) for index in range(1,5)]
        support_indices=[i for i in range(20) if i not in thumb_indices]
        lo[6+np.array(support_indices)]=h.lower[support_indices]+a.support_joint_margin;hi[6+np.array(support_indices)]=h.upper[support_indices]-a.support_joint_margin
        lo[6+np.array(thumb_indices)]=h.lower[thumb_indices]+a.thumb_joint_margin;hi[6+np.array(thumb_indices)]=h.upper[thumb_indices]-a.thumb_joint_margin
        if preload is not None:
            lo[6:26]=np.maximum(lo[6:26],h.lower+.005-preload);hi[6:26]=np.minimum(hi[6:26],h.upper-.005-preload)
            assert np.all(lo<hi),'Loaded motor reserve incompatible with original limits'
        if a.longitudinal_recenter:
            assert a.held_only and abs(a.longitudinal_recenter)<=.04
            center=x[2]+a.longitudinal_recenter;x[2]=center;lo[2]=center-.012;hi[2]=center+.012
        if a.retain_pickup_support:
            retained=json.loads(a.retain_pickup_support.read_text());wt=np.array(retained['wrist_in_knife']);fixed=np.r_[wt[:3,3],Rotation.from_matrix(wt[:3,:3]).as_rotvec(),retained['touch_q']]
            ids=np.r_[np.arange(6),[6+h.names.index('hand_r_'+f+'_joint'+str(j)) for f in ['middle','pinky'] for j in range(1,5)]]
            x[ids]=fixed[ids];lo[ids]=fixed[ids]-1e-8;hi[ids]=fixed[ids]+1e-8
        if a.stroke_span:
            endpoint_seed=np.array(prior['stroke_endpoint']['thumb_q']) if a.refine and 'stroke_endpoint' in prior else x[6+np.array(thumb_indices)]
            x=np.r_[x,endpoint_seed];lo=np.r_[lo,h.lower[thumb_indices]+.015];hi=np.r_[hi,h.upper[thumb_indices]-.015]
        fit=least_squares(residual,np.clip(x,lo+np.minimum(1e-7,(hi-lo)*.25),hi-np.minimum(1e-7,(hi-lo)*.25)),args=(s[:20],),bounds=(lo,hi),max_nfev=90,diff_step=1e-5);x=fit.x
        def cons(x):
            w,q,c,f,clear,table,pad_gap=geometry(x);target=desired_contacts(c)
            value=np.r_[(.001-np.linalg.norm(c[active]-target[active],axis=1))*1000,f[active]-facing_floor[active],(clear-.000005)*1000,(table-.0003)*1000]
            for region,r in zip(wrap_regions,region_geometry(x)):
                value=np.r_[value,(.001-r['error'])*1000,r['facing']-region.get('facing_cosine_min',.5)]
            if preload is not None:
                loaded_table,loaded_self=loaded_table_self(x);value=np.r_[value,(loaded_table-.0003)*1000,(loaded_self-.000005)*1000]
            if a.maximum_pad_gap:value=np.r_[value,(a.maximum_pad_gap-pad_gap[active])*1000]
            if a.stroke_span:
                _,_,endc,endf,endclear,_,endgap=stroke_geometry(x);endtarget=desired_contacts(c)[0]+np.array([0,0,a.stroke_span])
                contact_constraint=np.array([.001-np.linalg.norm(endc[0]-endtarget)])
                if a.revision>=4:contact_constraint=np.array([.0045-abs(endc[0,0]),.00015-abs(endc[0,1]-endtarget[1]),.0005-abs(endc[0,2]-endtarget[2])])
                value=np.r_[value,contact_constraint*1000,endf[0]-(facing_floor[0] if a.front_thumb_contact else .25),(endclear-.000005)*1000,(.0001-endgap[0])*1000]
            return value
        hard=minimize(lambda v:float((residual(v,s[:20])**2).sum()),x,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=90,ftol=1e-9));x=hard.x
        w,q,c,f,clear,table,pad_gap=geometry(x);armq,err=k.solve(world@w,np.array([.3,-.3,0,-1.3,0,0,0]));passed=bool(cons(x).min()>-1e-4 and err['position_m']<.003 and err['rotation_rad']<.02)
        row=dict(source=j,scope='Structural functionalgrasp nominal geometry only; held-only candidates ignore table and require actual acquisition/handover integration; no physics success',args=vars(a),active_fingers=[FINGERS[index] for index in active],excluded_fingers=[f for index,f in enumerate(FINGERS) if index not in active],planning_slider_m=-.03267458688196273,use_recorded_table_pose=True,object_world_matrix=world.tolist(),wrist_in_knife=w.tolist(),touch_q=q.tolist(),contact_points=c.tolist(),contact_normals=normal.tolist(),contact_targets=desired_contacts(c).tolist(),pad_facing_cosines=f.tolist(),contact_link_by_finger=contact_links,selected_contact_gaps_m=pad_gap.tolist(),selected_pad_gaps_m=pad_gap.tolist() if a.support_contact_link=='pad_link' else None,thumb_joint_margins_rad=np.minimum(q[thumb_indices]-h.lower[thumb_indices],h.upper[thumb_indices]-q[thumb_indices]).tolist(),minimum_knife_gap_m=float(clear.min()),minimum_table_gap_m=float(table.min()),geometric_pass=passed,arm_grasp_q=armq.tolist(),arm_ik=err,optimizer_message=hard.message,seconds=time.monotonic()-begin)
        row['wrap_regions']=wrap_regions;row['wrap_region_geometry']=[dict(link=r['link'],point_knife_m=r['point'].tolist(),target_knife_m=r['target'].tolist(),error_m=r['error'],actual_facet_facing_cosine=r['facing']) for r in region_geometry(x)]
        if preload is not None:
            loaded_table,loaded_self=loaded_table_self(x);row['loaded_motor_geometry']=dict(offsets_rad=preload.tolist(),minimum_table_gap_m=float(loaded_table.min()),minimum_self_gap_m=float(loaded_self.min()),scope='Fixed nominal old-posture torque offsets used for geometry hypothesis only; recompute equilibrium for new Jacobian, original limits and full lift audit before actual physics')
        if a.stroke_span:
            _,_,endc,endf,endclear,_,endgap=stroke_geometry(x);row['stroke_endpoint']=dict(travel_m=a.stroke_span,thumb_q=x[26:30].tolist(),thumb_point_m=endc[0].tolist(),thumb_pad_gap_m=float(endgap[0]),minimum_collision_gap_m=float(endclear.min()),point_error_m=float(np.linalg.norm(endc[0]-(desired_contacts(c)[0]+np.array([0,0,a.stroke_span])))),scope='Endpoints only, intermediate continuous path and physics remain unverified')
        (a.output/f'functional-edge-{j}.json').write_text(json.dumps(row,default=str,indent=2));rows.append(row);print(json.dumps({key:row[key] for key in ['source','minimum_knife_gap_m','minimum_table_gap_m','geometric_pass','arm_ik','seconds']}),flush=True)
    (a.output/'summary.json').write_text(json.dumps(rows,default=str,indent=2))
if __name__=='__main__':main()
