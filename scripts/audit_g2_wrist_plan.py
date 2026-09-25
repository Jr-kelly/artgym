"""Sample a new supported-wrist suffix before physics; never a dynamics claim."""
import argparse
import json
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision


def intersection_radius(g,q,a,b):
    frames=g.w.forward(q);hulls=[]
    for link in [a,b]:
        vertices=np.concatenate([v for v,_ in g.meshes[link]])
        frame=frames[link];hulls.append(ConvexHull(vertices@frame[:3,:3].T+frame[:3,3]).equations)
    eq=np.concatenate(hulls)
    result=linprog([0,0,0,-1],A_ub=np.c_[eq[:,:3],np.linalg.norm(eq[:,:3],axis=1)],
        b_ub=-eq[:,3],bounds=[(None,None)]*3+[(0,None)],method='highs')
    return float(result.x[3]) if result.success else (0. if result.status==2 else None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=5)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous audit')
    plan=json.loads(a.plan.read_text());meta=plan['supported_wrist_geometry'];source=json.loads(Path(meta['source']).read_text())
    t=np.load(source['source_trace']);i=source['source_step'];physics=json.loads((Path(source['source_trial'])/'physics.json').read_text())
    g=DigitGeometry(max_face_axes=32);full=DigitGeometry();k=G2Kinematics();table=ArmTableCollision(.75)
    q0=np.array(source['touch_q']);q=q0.copy();qa=t['reference_targets'][i,physics['arm_indices']].astype(float)
    relative0=np.array(source['wrist_in_knife']);obj=transform(t['object'][i,:3],t['object'][i,3:])
    actual_wrist0=obj@relative0;command_wrist0=k.forward(qa)
    base_overlap={};rows=[];previous_command=np.array(source['close_q']);peak_hand=0.;peak_arm=0.
    suffix=plan['stages'][-len(meta['rows'])-1:-1]
    for knot,(row,stage) in enumerate(zip(meta['rows'],suffix)):
        q1=np.array(row['nominal_q']);qa1=np.array(row['arm_command']);command=np.array(row['command'])
        peak_hand=max(peak_hand,float(abs(command-previous_command).max()*1.875/stage['seconds']))
        peak_arm=max(peak_arm,float((abs(qa1-qa)*1.875/stage['seconds']/k.velocity).max()))
        for u in np.linspace(0,1,a.samples):
            qs=q*(1-u)+q1*u;arm=qa*(1-u)+qa1*u
            relative=np.linalg.inv(obj)@k.forward(arm)@np.linalg.inv(command_wrist0)@actual_wrist0
            negative={}
            for finger in meta.get('actual_support_fingers',['middle','ring']):
                for pair in g.self_gaps(qs,finger):
                    if pair['gap_lower_bound_m']<0:
                        key=tuple(sorted([pair['moving_link'],pair['other_link']]))
                        if key not in negative:negative[key]=intersection_radius(g,qs,*key)
            if knot==0 and u==0:base_overlap=negative.copy()
            new=[dict(pair=list(pair),radius_m=radius,initial_radius_m=base_overlap.get(pair,0))
                 for pair,radius in negative.items() if radius is None or radius>max(base_overlap.get(pair,0) or 0,0)+1e-5]
            gaps={f:g.minimum_gap(qs,relative,float(t['slider'][i]),f) for f in ['thumb','index','middle','ring','pinky']}
            if gaps['thumb']<.0041:gaps['thumb']=full.minimum_gap(qs,relative,float(t['slider'][i]),'thumb')
            points=[];frames=g.w.forward(qs)
            for anchor in meta['contact_anchors']:
                frame=relative@frames[anchor['link']];points.append(frame[:3,:3]@anchor['local_point']+frame[:3,3])
            rows.append(dict(knot=knot+1,alpha=float(u),gaps_m=gaps,
                material_point_error_max_m=float(np.linalg.norm(np.array(points)-meta['support_targets_knife'],axis=1).max()),
                new_or_increased_intersections=new,arm_table=table.collisions(arm)))
        q=q1;qa=qa1;previous_command=command
    out=dict(plan=str(a.plan),samples=rows,peak_hand_command_rad_s=peak_hand,peak_arm_velocity_limit_fraction=peak_arm,
        thumb_min_gap_m=min(r['gaps_m']['thumb'] for r in rows),
        new_or_increased_self_intersections=sum(bool(r['new_or_increased_intersections']) for r in rows),
        arm_table_samples=sum(bool(r['arm_table']) for r in rows),
        support_material_error_max_m=max(r['material_point_error_max_m'] for r in rows),
        limitation='Sampled nominal joint interpolation with fixed initial arm servo offset. Positive gap conservative; intersection radius is not penetration depth. Physics and contact persistence still required.')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='samples'}))


if __name__=='__main__':main()
