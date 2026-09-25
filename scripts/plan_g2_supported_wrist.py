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
from scipy.spatial.transform import Rotation
from scripts.g2_seating_feedback import ContactCorrection
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_table_collision import ArmTableCollision


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--prefix',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--degrees',type=float,default=-25.);p.add_argument('--seconds',type=float,default=5.)
    p.add_argument('--endpoint-screen',action='store_true',help='Geometry-only extension up to60deg; never emits an executable motor plan.')
    p.add_argument('--thumb-avoidance',action='store_true',help='After the first25deg, allow minimal thumb motor changes to preserve clearance.')
    p.add_argument('--index-support',action='store_true',help='Use an actual established index contact as the third support; rejects absent contacts.')
    a=p.parse_args()
    if a.thumb_avoidance and not a.endpoint_screen:raise ValueError('Thumb avoidance currently emits geometry only')
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
    for finger in supports:
        samples=[]
        for pair in pairs:
            if pair['step']!=step:continue
            for side in [0,1]:
                if '_'+finger+'_' in pair['body'+str(side)]:samples.append((pair['body'+str(side)],pair['localPos'+str(side)]))
        if not samples:raise ValueError('No actual support contact for '+finger)
        link=max({v[0] for v in samples},key=lambda name:sum(v[0]==name for v in samples))
        anchors.append((link,np.mean([v[1] for v in samples if v[0]==link],axis=0)))
    def material_points(candidate,relative):
        frames=w.forward(candidate);points=[]
        for link,local in anchors:
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
            candidate=q.copy();candidate[ids]=v
            point=material_points(candidate,relative)
            gaps=[row for finger in supports for row in g.gaps(candidate,relative,t['slider'][step],finger)]
            index_point=(relative@w.forward(candidate)['hand_r_index_pad_link'])[:3,3]
            index_gaps=g.gaps(candidate,relative,t['slider'][step],'index')
            return np.r_[(point-targets).ravel()*250,
                         (index_point-index_target)*(0 if a.index_support else 150),
                         [min(row['gap_lower_bound_m']-.0041,0)*(0 if a.index_support else 400) for row in index_gaps],
                         [min(row['gap_lower_bound_m']+.00045,0)*400 for row in gaps],(v-q[ids])*.01]
        result=least_squares(residual,np.clip(q[ids],w.lower[ids]+1e-7,w.upper[ids]-1e-7),bounds=(w.lower[ids],w.upper[ids]),max_nfev=90,diff_step=1e-5)
        q[ids]=result.x;point=material_points(q,relative);error=np.linalg.norm(point-targets,axis=1)
        if a.thumb_avoidance and abs(a.degrees*i/count)>25:
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
        ok=bool(error.max()<.001 and gaps['thumb']>=.0041 and all(gaps[f]>=other_clearance[f] for f in inactive) and min(gaps[f] for f in supports)>=-.0008 and
                np.all(command>=w.lower) and np.all(command<=w.upper) and arm_error['position_m']<.001 and arm_error['rotation_rad']<.005)
        rows.append(dict(knot=i,degrees=a.degrees*i/count,support_point_errors_m=error.tolist(),gaps_m=gaps,geometric_ok=ok,
            nominal_q=q.tolist(),command=command.tolist(),arm_command=qa.tolist(),wrist_in_knife=relative.tolist(),arm_error=arm_error))
        stages.append(dict(name='supported_wrist_roll_'+str(i),kind='move',moving_indices=ids.tolist(),target=command[ids].tolist(),arm_target=qa.tolist(),seconds=a.seconds/count))
        if not ok:break
    out=dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),method=__doc__,
        rows=rows,geometric_pass=bool(len(rows)==count and rows[-1]['geometric_ok']),
        support_targets_knife=targets.tolist(),support_material_definition='Mean actual contact material point on each actual contacting link, no force inference.',
        contact_anchors=[dict(link=link,local_point=point.tolist()) for link,point in anchors],
        inactive_index_pinky_min_clearance_m=other_clearance,
        actual_support_fingers=supports,
        command_offset_preserved_rad=offset.tolist(),thumb_motors='Geometry-only avoidance after25deg' if a.thumb_avoidance else 'Held fixed; whole-digit knife clearance checked along wrist path.')
    if a.endpoint_screen:
        out['scope']='Hypothetical endpoint/path geometry only; not a continuous physical state or executable plan.'
        a.output.write_text(json.dumps(out,indent=2)+'\n')
    elif out['geometric_pass']:
        plan=json.loads(a.prefix.read_text());plan['stages']+=stages+[dict(name='supported_wrist_roll_hold',kind='hold',seconds=1.,require_no_contact=0,require_thumb_gap_m=.0041,
            require_contacts=[1,2,3] if a.index_support else [2,3])]
        plan['supported_wrist_geometry']=out;a.output.write_text(json.dumps(plan,indent=2)+'\n')
    else:a.output.with_suffix('.rejected.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out))


if __name__=='__main__':main()
