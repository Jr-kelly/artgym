"""Bounded geometric audit at the OLD actual functional reference.

This does not execute physics, acquire a grasp, or certify retention. The
unmeasured 50mm travel is a hypothesis, independent of the measured45mm button.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scripts.audit_g2_side_pickup_candidate import radius
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.g2_knife_geometry import KnifeGeometry


def main():
    p=argparse.ArgumentParser()
    for key in ['spec','reference','output']:
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    k=KnifeGeometry(a.spec);g=DigitGeometry(knife_spec=a.spec)
    r=json.loads(a.reference.read_text());q=np.array(r['measured_hand_q_rad'])
    pose=r['object_in_hand_xyzw'];t=transform(pose[:3],pose[3:]);wrist=np.linalg.inv(t)
    h=k.spec['geometry_hypothesis'];j=k.spec['joint_hypothesis']
    thumb_indices=[g.w.names.index('hand_r_thumb_joint'+str(i)) for i in range(1,5)]
    graph={}
    for parent,child,_,_,_ in g.w.joints:
        graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
    rows=[];previous=q.copy()
    for displacement in np.linspace(0,j['travel_m'],26):
        point=np.array([0,h['button_center_y_m']+h['button_base_thickness_m']/2+h['bump_height_m']+.0002,h['button_closed_center_z_m']+displacement])
        target=t[:3,:3]@point+t[:3,3];normal=t[:3,:3]@np.array([0.,-1,0])
        solved,error=g.w.solve_finger('thumb',target,previous,normal)
        frames={n:wrist@f for n,f in g.w.forward(solved).items()}
        vertices={n:np.concatenate([v for v,_ in meshes])@frames[n][:3,:3].T+frames[n][:3,3] for n,meshes in g.meshes.items()}
        self_bad=[];knife_bad=[]
        for n,v in vertices.items():
            if '_thumb_' not in n:continue
            near={n}|graph.get(n,set());near|=set().union(*(graph.get(x,set()) for x in list(near)))
            for m,u in vertices.items():
                if m in near or '_thumb_' in m:continue
                value=radius(v,u)
                if value is None or value>1e-5:self_bad.append(dict(pair=[n,m],intersection_ball_radius_m=value))
            for part in k.collision_parts(k.lower+displacement):
                value=radius(v,part['vertices'])
                if value is None or value>1e-5:knife_bad.append(dict(hand_link=n,knife_link=part['link'],knife_component=part['index'],intersection_ball_radius_m=value))
        gaps=g.gaps(solved,wrist,k.lower+displacement)
        bump_gaps=[x['gap_lower_bound_m'] for x in gaps if x['knife_link']=='link_1' and x['knife_component']==1]
        rows.append(dict(displacement_m=float(displacement),thumb_q=solved[thumb_indices].tolist(),landmark_error_m=error,
            thumb_joint_margin_min_rad=float(np.minimum(solved-g.w.lower,g.w.upper-solved)[thumb_indices].min()),
            thumb_max_joint_step_rad=float(abs(solved-previous)[thumb_indices].max()),
            thumb_self_intersections=self_bad,thumb_knife_intersections=knife_bad,
            bump_gap_lower_bound_m=min(bump_gaps),landmark_target_knife=point.tolist()))
        previous=solved
    out=dict(scope='CPU26sample nominal thumb sweep at old measured functional reference, sequential IK; no dynamics or newly acquired support',
        measured_button_length_m=k.spec['measured']['button_body_length_m'],unmeasured_travel_m=j['travel_m'],
        normal_target='Thumb volar normal toward knife -y, landmark0.2mm above assumed bump top',
        intersections_semantics='Exact convex-hull intersection-ball radius, NOT force or penetration depth',
        gap_semantics='Positive lower bound certifies separation; negative alone is inconclusive',
        reference=str(a.reference),spec=str(a.spec),physics_trials=0,rows=rows,
        full_sampled_geometric_sweep_clear=all(x['landmark_error_m']<.001 and not x['thumb_self_intersections'] and not x['thumb_knife_intersections'] and x['thumb_joint_margin_min_rad']>.005 for x in rows),
        retention_tested=False,slider_control_tested=False,conclusion='Old reference requires independent support adjustment and thumb path validation; no claim of dynamic reach or newasset success')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(samples=len(rows),clear=out['full_sampled_geometric_sweep_clear'],max_error_m=max(x['landmark_error_m'] for x in rows),collision_samples=sum(bool(x['thumb_self_intersections'] or x['thumb_knife_intersections']) for x in rows),joint_margin_min_rad=min(x['thumb_joint_margin_min_rad'] for x in rows))))


if __name__=='__main__':main()
