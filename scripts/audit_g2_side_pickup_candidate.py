"""Read-only exact convex-overlap and G2 reach checks of one side-pickup pose."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull

from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.g2_table_collision import ArmTableCollision


def radius(a,b):
    if np.any(a.max(0)<b.min(0)) or np.any(b.max(0)<a.min(0)):
        return 0.
    eq = np.r_[ConvexHull(a).equations, ConvexHull(b).equations]
    result = linprog([0,0,0,-1],A_ub=np.c_[eq[:,:3],np.ones(len(eq))],b_ub=-eq[:,3],
        bounds=[(None,None)]*3+[(0,None)],method='highs')
    return float(result.x[3]) if result.success else (0. if result.status==2 else None)


def main():
    p=argparse.ArgumentParser()
    for key in ['plan','localization','output']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--knife-spec',type=Path)
    a=p.parse_args();assert not a.output.exists()
    plan=json.loads(a.plan.read_text());loc=json.loads(a.localization.read_text())
    g=DigitGeometry();q=np.asarray(plan['touch_q']);frames=g.w.forward(q);wrist=np.asarray(plan['wrist_in_knife'])
    points={n:np.concatenate([v for v,_ in meshes])@frames[n][:3,:3].T+frames[n][:3,3] for n,meshes in g.meshes.items()}
    graph={}
    for parent,child,_,_,_ in g.w.joints:
        graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
    intersections=[];tested=0
    for i,n in enumerate(sorted(points)):
        near={n}|graph.get(n,set())
        near|=set().union(*(graph.get(v,set()) for v in list(near)))
        for m in sorted(points)[i+1:]:
            if m in near:continue
            tested+=1;r=radius(points[n],points[m])
            if r is None or r>1e-5:intersections.append(dict(pair=[n,m],intersection_inscribed_radius_m=r))
    corners=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])
    boxes={'body':corners*np.array([.0095,.004,.0735]),
        'slider':corners*np.array([.005,.0015,.015])+[0,.0055,.010624586881962734-.03267458826303482]}
    if a.knife_spec:
        from scripts.g2_knife_geometry import KnifeGeometry
        knife=KnifeGeometry(a.knife_spec)
        boxes={part['link']+'-component'+str(part['index']):part['vertices'] for part in knife.collision_parts()}
    body_overlaps=[]
    for n,v in points.items():
        local=v@wrist[:3,:3].T+wrist[:3,3]
        for name,box in boxes.items():
            r=radius(local,box)
            if r is None or r>1e-5:body_overlaps.append(dict(hand_link=n,knife_link=name,intersection_inscribed_radius_m=r))
    arm=G2Kinematics();table=ArmTableCollision(.75)
    object_world=transform(loc['object'][:3],loc['object'][3:]);target=object_world@wrist
    if a.knife_spec:
        object_world=knife.table_pose(object_world);target=object_world@wrist
    qa,err=arm.solve(target,np.asarray(loc['grasp_q']),attempts=1)
    near_limits=[]
    for i,name in enumerate(g.w.names):
        margin=min(q[i]-g.w.lower[i],g.w.upper[i]-q[i])
        if margin<.01:near_limits.append(dict(joint=name,margin_rad=float(margin)))
    result=dict(plan=str(a.plan),scope='One geometric touch pose only, no motor preload/dynamics or path certificate',
        nonadjacent_hand_pairs_tested=tested,excluded='Joint graph distances <=2 for mounting/joint shells only',
        hand_intersections=intersections,knife_intersections=body_overlaps,
        overlap_definition='Radius of a ball inside both convex hulls; not collision penetration depth or measured force',
        g2_ik=err,g2_arm_q=qa.tolist(),g2_arm_table=table.collisions(qa),
        joints_with_less_than_0p01rad_margin=near_limits,
        ready_for_physics=False,outstanding='Touch-only screening. Open/close approach, finger-table path and flip/flatten handoff not validated.')
    if a.knife_spec:result['knife_spec']=str(a.knife_spec)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    main()
