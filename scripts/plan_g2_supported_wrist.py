"""Plan a small wrist motion relative to a supported, world-fixed knife.

Middle/ring support and the free index compensate for the wrist motion. The already
released thumb follows the wrist with its motors fixed. This is explicitly a
coordinated support/wrist motion, not a single-finger gait or rigid assembly roll.
"""
import argparse
import hashlib
import json
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_seating_feedback import ContactCorrection
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--degrees',type=float,default=-25.);p.add_argument('--seconds',type=float,default=5.)
    p.add_argument('--stage-prefix',default='supported_wrist_roll',help='Use a unique prefix when appending another physical wrist segment.')
    p.add_argument('--endpoint-screen',action='store_true',help='Geometry-only extension up to60deg; never emits an executable motor plan.')
    p.add_argument('--thumb-avoidance',action='store_true',help='After the first25deg, allow minimal thumb motor changes to preserve clearance.')
    p.add_argument('--thumb-avoidance-start-deg',type=float,default=25.,help='Geometry-only onset of free-thumb avoidance; actual thumb clearance may require earlier onset.')
    p.add_argument('--bounded-thumb-avoidance',action='store_true',help='Emit at most20deg of coordinated support/wrist/free-thumb commands; requires a separate sweep audit before physics.')
    p.add_argument('--index-support',action='store_true',help='Use an actual established index contact as the third support; rejects absent contacts.')
    p.add_argument('--self-clearance',action='store_true',help='Penalize new or increased finger intersections while retaining actual material support points.')
    p.add_argument('--rolling-support-screen',action='store_true',help='Geometry only: allow material contacts to move within each original contacting convex hull, at most8mm per local coordinate.')
    a=p.parse_args()
    if a.bounded_thumb_avoidance:
        if abs(a.degrees)>20:raise ValueError('Executable free-thumb avoidance limited to20deg per segment')
        a.thumb_avoidance=True
    if a.thumb_avoidance and not (a.endpoint_screen or a.bounded_thumb_avoidance):raise ValueError('Use the explicit bounded executable avoidance option or geometry-only screening')
    if a.rolling_support_screen and not a.endpoint_screen:raise ValueError('Rolling supports currently geometry only')
    if abs(a.degrees)>(60 if a.endpoint_screen else 30):raise ValueError('Declared geometric range exceeded')
    if a.output.exists():raise ValueError('Preserve previous plan')
    d=json.loads(a.source.read_text());c=ContactCorrection();g=DigitGeometry(max_face_axes=32);w=c.w;k=G2Kinematics()
    q0=np.array(d['touch_q']);cmd0=np.array(d['close_q']);offset=cmd0-q0;r0=np.array(d['wrist_in_knife']);normals=np.array(d['contact_normals'])
    q=q0.copy();ids=np.r_[np.arange(0,8),np.arange(12,16)]
    trial=Path(d['source_trial']);t=np.load(d['source_trace']);step=d['source_step'];physics=json.loads((trial/'physics.json').read_text())
    qa=t['reference_targets'][step,physics['arm_indices']].astype(float);arm_start=k.forward(qa)
    obj=transform(t['object'][step,:3],t['object'][step,3:]);rows=[];stages=[]
    anchors=[]
    pairs=[json.loads(line) for line in (trial/'knife-contact-pairs.jsonl').read_text().splitlines()]
    supports=['index','middle','ring'] if a.index_support else ['middle','ring']
    self_baseline={}
    exact_self_baseline={}
    if a.self_clearance:
        from scripts.audit_g2_wrist_plan import intersection_radius
        for finger in supports:
            for row in g.self_gaps(q0,finger):
                key=(row['moving_link'],row['other_link'])
                self_baseline[key]=min(row['gap_lower_bound_m'],.0005)
                canonical=tuple(sorted(key))
                if row['gap_lower_bound_m']<0 and canonical not in exact_self_baseline:
                    radius=intersection_radius(g,q0,*canonical)
                    if radius is None:raise ValueError('Initial convex intersection check unresolved')
                    exact_self_baseline[canonical]=radius
    for finger in supports:
        samples=[]
        for pair in pairs:
            if pair['step']!=step:continue
            for side in [0,1]:
                if '_'+finger+'_' in pair['body'+str(side)]:samples.append((pair['body'+str(side)],pair['localPos'+str(side)]))
        if not samples:raise ValueError('No actual support contact for '+finger)
        link=max({v[0] for v in samples},key=lambda name:sum(v[0]==name for v in samples))
        anchors.append((link,np.mean([v[1] for v in samples if v[0]==link],axis=0)))
    anchor_initial=np.array([local for _,local in anchors]);anchor_values=anchor_initial.copy()
    anchor_hulls=[ConvexHull(np.concatenate([v for v,_ in g.meshes[link]])) for link,_ in anchors]
    anchor_lower=np.array([np.maximum(h.points.min(0),v-.008) for h,v in zip(anchor_hulls,anchor_initial)])
    anchor_upper=np.array([np.minimum(h.points.max(0),v+.008) for h,v in zip(anchor_hulls,anchor_initial)])
    def material_points(candidate,relative,local_values=None):
        frames=w.forward(candidate);points=[]
        for anchor_index,(link,local) in enumerate(anchors):
            if local_values is not None:local=local_values[anchor_index]
            frame=relative@frames[link];points.append(frame[:3,:3]@local+frame[:3,3])
        return np.array(points)
    targets=material_points(q0,r0);full=DigitGeometry()
    inactive=['pinky'] if a.index_support else ['index','pinky']
    other_clearance={f:min(.0041,full.minimum_gap(q0,r0,t['slider'][step],f)) for f in inactive}
    index_target=(r0@w.forward(q0)['hand_r_index_pad_link'])[:3,3]
    count=max(1,round(abs(a.degrees)/2.5))
    for i in range(1,count+1):
        rotation=transform(quaternion=Rotation.from_euler('z',a.degrees*i/count,degrees=True).as_quat());relative=rotation@r0
        def residual(v):
            candidate=q.copy();candidate[ids]=v[:len(ids)]
            local_values=v[len(ids):].reshape(-1,3) if a.rolling_support_screen else None
            point=material_points(candidate,relative,local_values)
            gaps=[row for finger in supports for row in g.gaps(candidate,relative,t['slider'][step],finger)]
            index_point=(relative@w.forward(candidate)['hand_r_index_pad_link'])[:3,3]
            index_gaps=g.gaps(candidate,relative,t['slider'][step],'index')
            self_errors=[]
            if a.self_clearance:
                for finger in supports:
                    for row in g.self_gaps(candidate,finger):
                        bound=self_baseline[(row['moving_link'],row['other_link'])]
                        self_errors.append(min(row['gap_lower_bound_m']-bound,0)*1500)
                # A face-axis bound alone does not constrain intersection size.
                # Preserve or reduce the actual convex intersection of already
                # touching roots; this is geometry, never a force estimate.
                for pair,bound in exact_self_baseline.items():
                    radius=intersection_radius(g,candidate,*pair)
                    if radius is None:raise ValueError('Convex intersection solver unresolved')
                    self_errors.append(max(radius-bound,0)*20000)
            rolling_errors=[]
            if a.rolling_support_screen:
                rolling_errors=np.r_[np.concatenate([np.maximum(h.equations[:,:3]@v+h.equations[:,3],0)*500 for h,v in zip(anchor_hulls,local_values)]),
                    (local_values-anchor_values).ravel()*5]
            return np.r_[(point-targets).ravel()*250,
                         (index_point-index_target)*(0 if a.index_support else 150),
                         [min(row['gap_lower_bound_m']-.0041,0)*(0 if a.index_support else 400) for row in index_gaps],
                         [min(row['gap_lower_bound_m']+.00045,0)*400 for row in gaps],self_errors,rolling_errors,(v[:len(ids)]-q[ids])*.01]
        x0=q[ids];lo=w.lower[ids];hi=w.upper[ids]
        if a.rolling_support_screen:
            x0=np.r_[x0,anchor_values.ravel()];lo=np.r_[lo,anchor_lower.ravel()];hi=np.r_[hi,anchor_upper.ravel()]
        result=least_squares(residual,np.clip(x0,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=90,diff_step=1e-5)
        q[ids]=result.x[:len(ids)]
        if a.rolling_support_screen:anchor_values=result.x[len(ids):].reshape(-1,3)
        point=material_points(q,relative,anchor_values if a.rolling_support_screen else None);error=np.linalg.norm(point-targets,axis=1)
        anchor_violation=max(float(np.maximum(h.equations[:,:3]@v+h.equations[:,3],0).max()) for h,v in zip(anchor_hulls,anchor_values)) if a.rolling_support_screen else 0.
        if a.thumb_avoidance and abs(a.degrees*i/count)>a.thumb_avoidance_start_deg:
            previous_thumb=q[16:].copy()
            def thumb_residual(v):
                candidate=q.copy();candidate[16:]=v
                return np.r_[[min(row['gap_lower_bound_m']-.0048,0)*400 for row in g.gaps(candidate,relative,t['slider'][step])],
                             [min(row['gap_lower_bound_m']-.001,0)*200 for row in g.self_gaps(candidate,'thumb')],(v-previous_thumb)*.02]
            solved=least_squares(thumb_residual,np.clip(previous_thumb,w.lower[16:]+1e-7,w.upper[16:]-1e-7),bounds=(w.lower[16:],w.upper[16:]),max_nfev=80,diff_step=1e-5)
            q[16:]=solved.x
        command=q+offset;goal=obj@rotation@np.linalg.inv(obj)@arm_start
        qa,arm_error=k.solve_near(goal,qa,max_step=.15)
        gaps={f:g.minimum_gap(q,relative,t['slider'][step],f) for f in ['thumb','index','middle','ring','pinky']}
        for finger in ['thumb']+inactive:
            if gaps[finger]<.0041:gaps[finger]=full.minimum_gap(q,relative,t['slider'][step],finger)
        ok=bool(error.max()<.001 and anchor_violation<.0001 and gaps['thumb']>=.0041 and all(gaps[f]>=other_clearance[f] for f in inactive) and min(gaps[f] for f in supports)>=-.0008 and
                np.all(command>=w.lower) and np.all(command<=w.upper) and arm_error['position_m']<.001 and arm_error['rotation_rad']<.005)
        rows.append(dict(knot=i,degrees=a.degrees*i/count,support_point_errors_m=error.tolist(),gaps_m=gaps,geometric_ok=ok,
            nominal_q=q.tolist(),command=command.tolist(),arm_command=qa.tolist(),wrist_in_knife=relative.tolist(),arm_error=arm_error,
            support_material_points=anchor_values.tolist(),support_anchor_hull_violation_m=anchor_violation))
        command_ids=np.r_[ids,np.arange(16,20)] if a.bounded_thumb_avoidance else ids
        stages.append(dict(name=a.stage_prefix+'_'+str(i),kind='move',moving_indices=command_ids.tolist(),target=command[command_ids].tolist(),
            arm_target=qa.tolist(),seconds=a.seconds/count,require_thumb_gap_m=.0041))
        if not ok:break
    out=dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),method=__doc__,
        rows=rows,geometric_pass=bool(len(rows)==count and rows[-1]['geometric_ok']),
        support_targets_knife=targets.tolist(),support_material_definition='Mean actual contact material point on each actual contacting link, no force inference.',
        contact_anchors=[dict(link=link,local_point=point.tolist()) for link,point in anchors],
        inactive_index_pinky_min_clearance_m=other_clearance,
        actual_support_fingers=supports,
        self_clearance_constraint=a.self_clearance,
        rolling_support_geometry_only=a.rolling_support_screen,
        free_thumb_avoidance_commands=a.bounded_thumb_avoidance,
        command_offset_preserved_rad=offset.tolist(),thumb_motors=((('Bounded executable' if a.bounded_thumb_avoidance else 'Geometry-only')+' avoidance after '+str(a.thumb_avoidance_start_deg)+' degrees') if a.thumb_avoidance else 'Held fixed; whole-digit knife clearance checked along wrist path.'))
    if a.endpoint_screen:
        out['scope']='Hypothetical endpoint/path geometry only; not a continuous physical state or executable plan.'
        a.output.write_text(json.dumps(out,indent=2)+'\n')
    elif out['geometric_pass']:
        plan=json.loads(a.prefix.read_text());plan['stages']+=stages+[dict(name=a.stage_prefix+'_hold',kind='hold',seconds=1.,require_no_contact=0,require_thumb_gap_m=.0041,
            require_contacts=[1,2,3] if a.index_support else [2,3])]
        plan['supported_wrist_geometry']=out;a.output.write_text(json.dumps(plan,indent=2)+'\n')
    else:a.output.with_suffix('.rejected.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))


if __name__=='__main__':main()
