"""Plan the entire rear-bearing approach from this candidate's actual hand.

The endpoint alone is insufficient: a straight joint interpolation crossed
the idle pinky. Ring and pinky now share a collision-constrained approach.
Other loaded digits retain their own issued commands. Planning is not a
native contact or lift result, and does not modify physical states.
"""
import argparse, json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--endpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    s=np.load(a.source/'takeover.npz');end=json.loads(a.endpoint.read_text())
    spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')
    g=DigitGeometry(max_face_axes=10,knife_spec=spec);audit=HandIntersection()
    # Reduced axes can certify positive clearance, but a negative result
    # must not be treated as a real overlap. In D688 the reduced pair
    # geometry falsely excluded the already valid middle/ring link2 pose.
    pair_geometry=audit.g
    q=s['robot_q'][7:].astype(float);issued=s['issued_target'][7:].astype(float)
    W=G2Kinematics().forward(s['robot_q'][:7]);O=transform(s['object_state'][:3],s['object_state'][3:7]);L=np.linalg.inv(O)@W
    ids=np.arange(8,16);goal=q.copy();goal[12:16]=end['diagnostics']['ring_q']
    pairs=[pair for pair in audit.pairs if any('_ring_' in n or '_pinky_' in n for n in pair)]
    record('safe_rear_bearing_path_start',[str(a.source/'manifest.json'),str(a.endpoint)],config=dict(
        grasp_end='D684 actual0.7667s before migration',support_layout='Existing forward I/M+Thumb plus rear Ring',
        control='Collision constrained Ring/Pinky path; own other issued targets retained',
        uncertainty='Feasible rear endpoint had 100 straight-path self intersections; can a whole safe approach acquire it?',
        decision='Geometric path clear -> one native acquisition; blocked geometry -> wrist/contact change'))
    previous=q[ids].copy();rows=[];diag=[]
    for step,t in enumerate(np.linspace(0,3.5,22)):
        prior=(1-smooth(t/3.))*q[ids]+smooth(t/3.)*goal[ids]
        lo=np.maximum(g.w.lower[ids]+.035,previous-.18);hi=np.minimum(g.w.upper[ids]-.035,previous+.18)
        def residual(x):
            h=q.copy();h[ids]=x;F=g.w.forward(h);r=list((x-prior)*.07)
            r.extend(min(0.,v['gap_lower_bound_m']-.0001)*800 for v in pair_geometry.pair_gaps(h,pairs))
            for finger in ['ring','pinky']:
                for gap in g.gaps(h,L,float(s['slider_q']),finger,frames=F):
                    allowed=gap['knife_link']=='link_0' and gap['hand_link'] in ['hand_r_ring_link4','hand_r_ring_pad_link']
                    r.append(min(0.,gap['gap_lower_bound_m']-(-.0006 if allowed else .00015))*650)
                for name,parts in g.meshes.items():
                    if '_'+finger+'_' not in name:continue
                    T=W@F[name]
                    r.extend(min(0.,float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7501))*800 for v,_ in parts)
            r.extend((x[:4]-q[8:12])*.04)
            return np.asarray(r)
        fit=least_squares(residual,np.clip(previous,lo+1e-8,hi-1e-8),bounds=(lo,hi),max_nfev=45,diff_step=1e-5)
        h=q.copy();h[ids]=fit.x;previous=fit.x.copy();cmd=issued.copy();cmd[ids]=h[ids]+issued[ids]-q[ids]
        rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
        diag.append(dict(time_s=float(t),self_intersections=audit.inspect(h),planned_hand_q=h.tolist(),posture_error_rad=float(np.linalg.norm(h[12:16]-goal[12:16]))))
        print(json.dumps(dict(time_s=float(t),self=len(diag[-1]['self_intersections']),posture_error_rad=diag[-1]['posture_error_rad'])),flush=True)
    out=dict(rows=rows,source=str(a.source),endpoint=str(a.endpoint),path_diagnostics=diag,scope=__doc__,physics_relaxed=False)
    (a.output/'motor.json').write_text(json.dumps(out,indent=2))
    result=dict(path_self_frames=sum(bool(r['self_intersections']) for r in diag),terminal_posture_error_rad=diag[-1]['posture_error_rad'])
    record('safe_rear_bearing_path_end',[str(a.output/'motor.json')],config=result,next_step='Read wholepath clearance; native only when approach feasible')


if __name__=='__main__':main()
