"""Functional tabletop edge-grasp planning with real knife collisions.

Four supporting pads are placed near the overhanging handle end, thumb on
the slider. The object COM remains on the tabletop. CPU geometry, no success claim.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,minimize
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import FINGERS

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--root-inset',type=float,default=.008);p.add_argument('--y',type=float,default=-.25);p.add_argument('--refine',type=Path);p.add_argument('--three-support',action='store_true');p.add_argument('--self-separation',action='store_true');p.add_argument('--positive-end-two-support',action='store_true');p.add_argument('--side-edge-all-support',action='store_true');p.add_argument('--source',type=int,choices=range(4));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    g=DigitGeometry(max_face_axes=24,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;k=G2Kinematics();knife=g.knife_geometry
    world=transform([.30+a.root_inset,a.y,.7561],(Rotation.from_euler('z',0 if a.side_edge_all_support else -90 if a.positive_end_two_support else 90,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());parts=knife.collision_parts(-.03267458688196273)
    table_center=np.array([.60,-.25,.725]);table_half=np.array([.30,.40,.025]);normal=np.array([[0,1.,0]]+[[0,-1.,0]]*4)
    vertices={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()};axes={n:np.concatenate([v for _,v in m]) for n,m in g.meshes.items()}
    seeds=np.load('research/real-size-student-adaptation-20261002/data/real/adapted-seeds.npy')
    target_z=np.array([-.02205,-.015,-.029,-.043,-.055])
    active=np.array([0,1,2,3] if a.three_support else [0,1,2,3,4]);
    if a.three_support:target_z=np.array([-.02205,-.015,-.035,-.055,-.07])
    if a.positive_end_two_support:
        active=np.array([0,1,2]);target_z=np.array([-.02205,.039,.019,-.022,-.047])
    if a.side_edge_all_support:
        active=np.arange(5);target_z=np.array([-.02205,.039,.001,-.022,-.047])
        normal[1:]=np.array([-1.,-1.,0.])/np.sqrt(2)
    def desired_contacts(contact):
        target=np.c_[np.clip(contact[:,0],-.004,.004),[.0092,-.0062,-.0062,-.0062,-.0062],target_z]
        if a.side_edge_all_support:target[1:,0]=-.0082
        return target
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
    def geometry(x):
        wrist=transform(x[:3]);wrist[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();q=x[6:];frames={n:wrist@mat for n,mat in h.forward(q).items()};vs={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in vertices.items()};contact=[];facing=[];clear=[];table=[]
        for f,n in zip(FINGERS,normal):
            name='hand_r_'+f+'_pad_link';v=vs[name];pr=v@n;weights=np.exp(-(pr-pr.min())/.0002);weights/=weights.sum();contact.append(weights@v);facing.append(frames[name][:3,0]@(-n))
        for name,v in vs.items():
            normals=axes[name]@frames[name][:3,:3].T
            for part in parts:
                ax=np.r_[normals,part['normals']];pa=v@ax.T;pb=part['vertices']@ax.T;clear.append(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
            vw=v@world[:3,:3].T+world[:3,3];ax=np.r_[np.eye(3),normals@world[:3,:3].T];pv=(vw-table_center)@ax.T;radius=abs(ax)@table_half;table.append(np.maximum(pv.min(0)-radius,-radius-pv.max(0)).max())
        for n,m in self_pairs:
            ax=np.r_[axes[n]@frames[n][:3,:3].T,axes[m]@frames[m][:3,:3].T];pa=vs[n]@ax.T;pb=vs[m]@ax.T;clear.append(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
        return wrist,q,np.array(contact),np.array(facing),np.array(clear),np.array(table)
    def residual(x,seed):
        w,q,c,f,clear,table=geometry(x);target=desired_contacts(c)
        return np.r_[(c[active]-target[active]).ravel()*250,np.minimum(f[active]-.35,0)*2,np.minimum(clear-.000015,0)*600,np.minimum(table-.0005,0)*800,(q-seed)*.01]
    rows=[]
    if a.refine:seeds=seeds[3:4]
    elif a.source is not None:seeds=seeds[a.source:a.source+1]
    for j,s in enumerate(seeds):
        begin=time.monotonic();w=np.linalg.inv(transform(s[40:43],s[43:47]));x=np.r_[w[:3,3],Rotation.from_matrix(w[:3,:3]).as_rotvec(),s[:20]];lo=np.r_[w[:3,3]-.06,x[3:6]-.8,h.lower+.015];hi=np.r_[w[:3,3]+.06,x[3:6]+.8,h.upper-.015]
        if a.refine:
            prior=json.loads(a.refine.read_text());w=np.asarray(prior['wrist_in_knife']);x=np.r_[w[:3,3],Rotation.from_matrix(w[:3,:3]).as_rotvec(),prior['touch_q']];lo[:3]-=.02;hi[:3]+=.02;lo[3:6]-=.3;hi[3:6]+=.3
        fit=least_squares(residual,np.clip(x,lo+1e-7,hi-1e-7),args=(s[:20],),bounds=(lo,hi),max_nfev=150,diff_step=1e-5);x=fit.x
        def cons(x):
            w,q,c,f,clear,table=geometry(x);target=desired_contacts(c)
            return np.r_[(.001-np.linalg.norm(c[active]-target[active],axis=1))*1000,f[active]-.25,(clear-.000005)*1000,(table-.0003)*1000]
        hard=minimize(lambda v:float((residual(v,s[:20])**2).sum()),x,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=120,ftol=1e-9));x=hard.x
        w,q,c,f,clear,table=geometry(x);armq,err=k.solve(world@w,np.array([.3,-.3,0,-1.3,0,0,0]));passed=bool(cons(x).min()>-1e-4 and err['position_m']<.003 and err['rotation_rad']<.02)
        row=dict(source=j,scope='CPU geometry only; COM inside tabletop, configured edge placement; no physics tested',args=vars(a),active_fingers=[FINGERS[index] for index in active],excluded_fingers=[f for index,f in enumerate(FINGERS) if index not in active],planning_slider_m=-.03267458688196273,use_recorded_table_pose=True,object_world_matrix=world.tolist(),wrist_in_knife=w.tolist(),touch_q=q.tolist(),contact_points=c.tolist(),contact_normals=normal.tolist(),contact_targets=desired_contacts(c).tolist(),pad_facing_cosines=f.tolist(),minimum_knife_gap_m=float(clear.min()),minimum_table_gap_m=float(table.min()),geometric_pass=passed,arm_grasp_q=armq.tolist(),arm_ik=err,optimizer_message=hard.message,seconds=time.monotonic()-begin)
        (a.output/f'functional-edge-{j}.json').write_text(json.dumps(row,default=str,indent=2));rows.append(row);print(json.dumps({key:row[key] for key in ['source','minimum_knife_gap_m','minimum_table_gap_m','geometric_pass','arm_ik','seconds']}),flush=True)
    (a.output/'summary.json').write_text(json.dumps(rows,default=str,indent=2))
if __name__=='__main__':main()
