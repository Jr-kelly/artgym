"""Read-only measured-envelope comparison and old grasp/thumbnail reach audit."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull

from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.audit_g2_side_pickup_candidate import radius


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    old,new=KnifeGeometry(),KnifeGeometry(a.spec);hand=DigitGeometry();reference=json.loads(a.reference.read_text())
    # Use actual executed q and actual recorded T_hand_object, never motor
    # targets as measured geometry. This audit does not reset a simulation.
    q=np.array(reference['measured_hand_q_rad'])
    r=reference['object_in_hand_xyzw'];t=transform(r[:3],r[3:])
    frames=hand.w.forward(q);wrist=np.linalg.inv(t)
    intersections=[]
    for name,meshes in hand.meshes.items():
        f=wrist@frames[name];v=np.concatenate([v for v,_ in meshes])@f[:3,:3].T+f[:3,3]
        for part in new.collision_parts():
            overlap=radius(v,part['vertices'])
            if overlap is None or overlap>1e-5:intersections.append(dict(hand_link=name,knife_link=part['link'],knife_component=part['index'],intersection_ball_radius_m=overlap))
    thumb=[];h=new.spec['geometry_hypothesis'];joint=new.spec['joint_hypothesis']
    for travel in [0.,joint['operation_excursion_m'],joint['travel_m']]:
        point=np.array([0,h['button_center_y_m']+h['button_base_thickness_m']/2+h['bump_height_m']+.0002,h['button_closed_center_z_m']+travel])
        target=t[:3,:3]@point+t[:3,3];normal=t[:3,:3]@np.array([0.,-1,0])
        solved,error=hand.w.solve_finger('thumb',target,q,normal)
        thumb.append(dict(assumed_slider_displacement_m=travel,thumb_landmark_target_knife=point.tolist(),
            ik_landmark_error_m=error,q=solved.tolist(),joint_margin_min_rad=float(np.minimum(solved-hand.w.lower,hand.w.upper-solved).min()),
            qualification='Only nominal thumb-landmark IK in an old preset frame, not full-pad collision, reach path, holding or slider success'))
    fig,axes=plt.subplots(2,2,figsize=(10,3.5),gridspec_kw={'height_ratios':[2,1]})
    colors=['#8998ae','#414950','#cc993d']
    for col,(knife,title) in enumerate([(old,'Preserved baseline'),(new,'Measured envelope / explicit shape hypothesis')]):
        for row,(indices,ylabel) in enumerate([([2,0],'Width x (mm)'),([2,1],'Thickness y (mm)')]):
            ax=axes[row,col]
            for i,part in enumerate(knife.collision_parts()):
                v=part['vertices'][:,indices]*1000;hull=ConvexHull(v);ax.add_patch(Polygon(v[hull.vertices],facecolor=colors[min(i,2)],edgecolor='black',alpha=.8))
            ax.set_xlim(-90,90);ax.set_ylim((-17,17) if row==0 else (-5,9));ax.set_aspect('equal');ax.set_xlabel('Knife length z (mm)');ax.set_ylabel(ylabel);ax.grid(alpha=.2)
            if row==0:ax.set_title(title,fontsize=10)
    fig.suptitle('Button length45mm is separate from unmeasured travel; raised pad is collision geometry',fontsize=10)
    fig.tight_layout();fig.savefig(a.output/'geometry-comparison.png',dpi=160)
    oldv=np.concatenate([x['vertices'] for x in old.collision_parts()]);newv=np.concatenate([x['vertices'] for x in new.collision_parts()])
    report=dict(scope='CPU geometric audit, no dynamics, no training',old_closed_envelope_xyz_m=np.ptp(oldv,0).tolist(),new_closed_envelope_xyz_m=np.ptp(newv,0).tolist(),
        difference=dict(handle_length_m=.023,max_width_m=.011,button_length_m=.015),
        thickness_caution='Old handle alone8mm plus3mm button gives11mm full envelope. New8mm full envelope includes1mm assumed bump under provisional interpretation. These are different definitions.',
        old_actual_operation_pose_on_new_asset_intersections=intersections,thumbnail_ik=thumb,
        unsupported_claims=['No newasset grasp/hold/flip demonstrated','No stable nonthumb support with thumb released','No complete slider sweep or frozen policy success','No deployment or measured resistance/latch'],
        required_updates=['Replan lateral pads for30mm width instead of19mm','Recompute table initial height/natural settling including bump','Use new convex geometry for all approach/flip/regrasp audits','Re-evaluate thumb transfer and sweep at actual acquired state','Student initialization currently hardcodes six old geometry dimensions; explicit geometry interface audit required before C'],
        uncertainty=new.spec['unmeasured'])
    (a.output/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
