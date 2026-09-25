"""Prepare one explicitly hypothetical independentA endpoint, never a B reset."""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.audit_g2_self_clearance import Clearance
from scripts.g2_table_collision import ArmTableCollision


def pose(t):
    from scipy.spatial.transform import Rotation
    return np.r_[t[:3,3],Rotation.from_matrix(t[:3,:3]).as_quat()]


def main():
    p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True)
    p.add_argument('--thumb-screen',type=Path,required=True);p.add_argument('--degrees',type=float,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous candidate')
    geometry=json.loads(a.geometry.read_text());row=next(v for v in geometry['rows'] if v['degrees']==a.degrees)
    if not row['geometric_ok']:raise ValueError('Rejected support geometry')
    screen=json.loads(a.thumb_screen.read_text());thumb=min([v for v in screen['rows'] if v['geometric_candidate']],key=lambda v:v['point_error_m'])
    g=DigitGeometry(max_face_axes=32);full=DigitGeometry();w=g.w;relative=np.array(row['wrist_in_knife'])
    q=np.array(row['nominal_q']);command=np.array(row['command']);q[16:]=thumb['q'];anchor=np.array(thumb['anchor_local'])
    def thumb_point(v):
        qv=q.copy();qv[16:]=v;frame=relative@w.forward(qv)['hand_r_thumb_pad_link'];return frame[:3,:3]@anchor+frame[:3,3]
    target=np.array(thumb['target']);target[1]=.0064
    solved=least_squares(lambda v:np.r_[(thumb_point(v)-target)*250,(v-q[16:])*.01],q[16:],bounds=(w.lower[16:],w.upper[16:]),max_nfev=120,diff_step=1e-5)
    command[16:]=solved.x;thumb_error=float(np.linalg.norm(thumb_point(solved.x)-target))
    opening=[];initial_nominal=q.copy()
    for finger,ids in [('index',[2,3]),('middle',[4,5,6,7]),('ring',[14,15])]:
        original=q.copy();lo=np.maximum(w.lower[ids],q[ids]-.15);hi=np.minimum(w.upper[ids],q[ids]+.15)
        def residual(v):
            candidate=original.copy();candidate[ids]=v
            return np.r_[[min(s['gap_lower_bound_m']-.00015,0)*500 for s in g.gaps(candidate,relative,screen['slider_position_m'],finger)],(v-original[ids])*.01]
        solved=least_squares(residual,np.clip(q[ids],lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5)
        seed_note='local nominal seed'
        if finger=='middle' and min(residual(solved.x)[:10])<-.0001*500:
            # A coordinate precheck found a gap-function local minimum at the
            # nominal link4 pose and clearance after reducing joint1 by0.08rad.
            # One bounded branch retry; no state is executed by this tool.
            seed=original[ids].copy();seed[0]-=.1
            retry=least_squares(residual,np.clip(seed,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=100,diff_step=1e-5)
            if retry.cost<solved.cost:solved=retry;seed_note='single -0.1rad joint1 branch from signed geometric precheck'
        q[ids]=solved.x
        opening.append(dict(finger=finger,delta_rad=(q[ids]-original[ids]).tolist(),seed=seed_note))
    gaps={f:full.minimum_gap(q,relative,screen['slider_position_m'],f) for f in ['thumb','index','middle','ring','pinky']}
    negative={tuple(sorted([s['moving_link'],s['other_link']])) for f in ['thumb','index','middle','ring'] for s in full.self_gaps(q,f) if s['gap_lower_bound_m']<0}
    from scripts.audit_g2_wrist_plan import intersection_radius
    intersections=[dict(pair=pair,initial_radius_m=intersection_radius(g,initial_nominal,*pair),opened_radius_m=intersection_radius(g,q,*pair)) for pair in negative]
    new_intersection=any(v['initial_radius_m'] is None or v['opened_radius_m'] is None or v['opened_radius_m']>v['initial_radius_m']+1e-5 for v in intersections)
    source=json.loads(Path(geometry['source']).read_text());trace=np.load(source['source_trace']);i=source['source_step']
    obj=transform(trace['object'][i,:3],trace['object'][i,3:]);operation=obj@relative;k=G2Kinematics();qa,ik=k.solve(operation,np.array(row['arm_command']))
    arm_self=Clearance().collisions(qa);arm_table=ArmTableCollision(.75).collisions(qa)
    obj_hand=np.linalg.inv(relative);slider_hand=obj_hand@transform([0,.0055,.010624586881962734+screen['slider_position_m']])
    tips=np.concatenate([w.forward(q)[n][:3,3] for n in w.config['track_links']])
    state=np.r_[q,command,pose(obj_hand),pose(slider_hand),screen['slider_position_m'],tips]
    valid=bool(thumb_error<.001 and min(gaps.values())>=-.0001 and not arm_self and not arm_table and ik['position_m']<1e-4 and ik['rotation_rad']<1e-3 and
        np.all(command>=w.lower) and np.all(command<=w.upper) and not new_intersection)
    out=dict(state=state.tolist(),geometry=str(a.geometry),degrees=a.degrees,thumb_screen=str(a.thumb_screen),initial_whole_digit_gap_m=gaps,
        initial_negative_self_pairs=sorted(negative),self_intersection_checks=intersections,thumb_command_contact_error_m=thumb_error,initial_support_opening=opening,
        arm_ik=ik,arm_self=arm_self,arm_table=arm_table,geometric_preflight=valid,
        scope='IndependentA hypothetical geometry, not actual acquisition. Initial joints are opened just clear of knife before first physical step; finite-drive closing commands then settle2s. No state writes after physics starts.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');a.output.with_suffix('.operation.json').write_text(json.dumps(operation.tolist())+'\n');a.output.with_suffix('.arm.json').write_text(json.dumps(qa.tolist())+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='state'}))
    if not valid:raise ValueError('Candidate preflight rejected; do not launch physics')


if __name__=='__main__':main()
