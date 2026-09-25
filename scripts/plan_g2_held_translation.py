"""Bounded wrist translation while retaining an actual opposed three-digit grip.

Alternative for the already acquired second candidate: reduce the knife-center
offset before thumb release. This explicitly coordinates held digits with the
G2 wrist; it is not a single-finger gait or an executed/reset physical state.
"""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.audit_g2_wrist_plan import intersection_radius
from scripts.audit_g2_self_clearance import Clearance
from scripts.g2_table_collision import ArmTableCollision


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--distance',type=float,default=.010);p.add_argument('--stage-prefix',default='held_translation')
    p.add_argument('--rotation-degrees',type=float,default=0.,help='Independent <=15deg motion toward functional orientation; requires --distance0 and retains opposed support.')
    a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve old geometry')
    if not ((0<a.distance<=.010 and a.rotation_degrees==0) or (a.distance==0 and 0<a.rotation_degrees<=15)):
        raise ValueError('Choose one bounded motion: <=10mm translation OR <=15deg rotation')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);full=DigitGeometry();w=g.w;k=G2Kinematics();q0=np.array(d['touch_q']);q=q0.copy();cmd0=np.array(d['close_q']);offset=cmd0-q0;r0=np.array(d['wrist_in_knife'])
    root=Path(__file__).resolve().parents[1];cache=np.load(root/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    desired_center=cache[40:43];actual_center=np.linalg.inv(r0)[:3,3];delta=-r0[:3,:3]@(desired_center-actual_center);delta*=min(1,a.distance/np.linalg.norm(delta))
    functional=np.linalg.inv(transform(cache[40:43],cache[43:47]));rotation_vector=Rotation.from_matrix(functional[:3,:3]@r0[:3,:3].T).as_rotvec()
    axis=rotation_vector/max(np.linalg.norm(rotation_vector),1e-10)
    trial=Path(d['source_trial']);t=np.load(d['source_trace']);i=d['source_step'];physics=json.loads((trial/'physics.json').read_text());qa=t['reference_targets'][i,physics['arm_indices']].astype(float);arm0=k.forward(qa);obj=transform(t['object'][i,:3],t['object'][i,3:]);slider=float(t['slider'][i])
    raw=[json.loads(v) for v in (trial/'knife-contact-pairs.jsonl').read_text().splitlines()];anchors=[];fingers=['thumb','middle','ring'];ids=np.r_[np.arange(4,8),np.arange(12,20)]
    for finger in fingers:
        points=[]
        for row in raw:
            if row['step']!=i:continue
            for side in [0,1]:
                if '_'+finger+'_' in row['body'+str(side)] and row['body'+str(1-side)]=='link_0':points.append((row['body'+str(side)],np.array(row['localPos'+str(side)])))
        link=max(set(v[0] for v in points),key=lambda l:sum(v[0]==l for v in points));anchor=np.mean([v[1] for v in points if v[0]==link],axis=0);frame=r0@w.forward(q0)[link]
        anchors.append((link,anchor,frame[:3,:3]@anchor+frame[:3,3]))
    baseline={};intersections={}
    for finger in fingers:
        for s in g.self_gaps(q0,finger):
            key=tuple(sorted([s['moving_link'],s['other_link']]));baseline[key]=min(s['gap_lower_bound_m'],0)
            if baseline[key]<0 and key not in intersections:intersections[key]=intersection_radius(g,q0,*key)
    if any(v is None for v in intersections.values()):raise ValueError('Unresolved initial self geometry')
    initial_gap={f:min(full.minimum_gap(q0,r0,slider,f),-.00045) for f in fingers};inactive_gap={f:min(full.minimum_gap(q0,r0,slider,f),.0041) for f in ['index','pinky']}
    lo=np.maximum(w.lower,w.lower-offset);hi=np.minimum(w.upper,w.upper-offset);rows=[];stages=[];arm_table=ArmTableCollision(.75);arm_self=Clearance()
    for knot in range(1,6):
        rotation=transform(quaternion=Rotation.from_rotvec(axis*np.deg2rad(a.rotation_degrees)*knot/5).as_quat())
        relative=rotation@r0;relative[:3,3]+=delta*knot/5
        def errors(qv):
            frames=w.forward(qv);pts=[]
            for link,anchor,target in anchors:
                f=relative@frames[link];pts.append(f[:3,:3]@anchor+f[:3,3]-target)
            return np.array(pts)
        def residual(v):
            proposed=q.copy();proposed[ids]=v;sg=[]
            for finger in fingers:
                for s in g.self_gaps(proposed,finger):sg.append(min(s['gap_lower_bound_m']-baseline[tuple(sorted([s['moving_link'],s['other_link']]))],0)*700)
            exact=[max(intersection_radius(g,proposed,*pair)-value,0)*10000 for pair,value in intersections.items()]
            return np.r_[errors(proposed).ravel()*300,[min(g.minimum_gap(proposed,relative,slider,f)-initial_gap[f],0)*500 for f in fingers],
                [min(g.minimum_gap(proposed,relative,slider,f)-inactive_gap[f],0)*500 for f in inactive_gap],sg,exact,(v-q[ids])*.005]
        solved=least_squares(residual,np.clip(q[ids],lo[ids]+1e-7,hi[ids]-1e-7),bounds=(lo[ids],hi[ids]),max_nfev=90,diff_step=1e-5);q[ids]=solved.x;command=q+offset
        goal=arm0.copy() if a.rotation_degrees==0 else obj@rotation@np.linalg.inv(obj)@arm0
        goal[:3,3]+=obj[:3,:3]@delta*knot/5;qa,ik=k.solve_near(goal,qa,max_step=.15)
        gaps={f:full.minimum_gap(q,relative,slider,f) for f in fingers+['index','pinky']};badself=[]
        for finger in fingers:
            for s in full.self_gaps(q,finger):
                key=tuple(sorted([s['moving_link'],s['other_link']]))
                if s['gap_lower_bound_m']<0:
                    radius=intersection_radius(g,q,*key)
                    if radius is None or radius>intersections.get(key,0)+1e-5:badself.append(key)
        valid=bool(np.linalg.norm(errors(q),axis=1).max()<.001 and all(gaps[f]>=initial_gap[f]-.0001 for f in fingers) and all(gaps[f]>=inactive_gap[f] for f in inactive_gap) and not badself and not arm_table.collisions(qa) and not arm_self.collisions(qa) and ik['position_m']<.001 and ik['rotation_rad']<.005)
        rows.append(dict(knot=knot,geometric_ok=valid,nominal_q=q.tolist(),command=command.tolist(),arm_command=qa.tolist(),wrist_in_knife=relative.tolist(),gaps_m=gaps,support_errors_m=np.linalg.norm(errors(q),axis=1).tolist(),new_self_intersections=badself,arm_ik=ik))
        stages.append(dict(name=a.stage_prefix+'_'+str(knot),kind='move',seconds=1.,moving_indices=ids.tolist(),target=command[ids].tolist(),arm_target=qa.tolist()))
        if not valid:break
    meta=dict(source=str(a.source),knife_center_in_hand_start_m=actual_center.tolist(),functional_knife_center_in_hand_m=desired_center.tolist(),planned_wrist_translation_in_knife_m=delta.tolist(),
        rotation_degrees=a.rotation_degrees,rotation_axis_in_knife=axis.tolist(),rows=rows,
        geometric_pass=bool(len(rows)==5 and rows[-1]['geometric_ok']),support_anchors=[dict(link=l,local_point=v.tolist(),target=p.tolist()) for l,v,p in anchors],
        actual_support_fingers=fingers,contact_anchors=[dict(link=l,local_point=v.tolist()) for l,v,p in anchors],support_targets_knife=[p.tolist() for l,v,p in anchors],
        scope='Geometry only, <=10mm translation OR <=15deg wrist rotation with three opposed digits. Original command-minus-measured offsets retained; no physics or initial state changes.')
    plan=json.loads(a.prefix.read_text());plan['held_translation_geometry']=meta;plan['stages']+=stages+[dict(name=a.stage_prefix+'_support_hold',kind='hold',seconds=1.,require_contacts=[0,2,3])]
    out=a.output if meta['geometric_pass'] else a.output.with_suffix('.rejected.json');out.write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(dict(output=str(out),translation=delta.tolist(),rows=[{k:v for k,v in row.items() if k not in ['nominal_q','command','arm_command','wrist_in_knife']} for row in rows])))


if __name__=='__main__':main()
