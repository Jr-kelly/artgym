"""Bounded geometric screen of the actual thumb material point over40mm.

No physics or successful-operation claim. Fixed measured hand/body relation;
all other joints held at measured q. Identifies coordinated thumb motion and
clearance risks before deciding the last learning configuration.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry


def matrix(pose):
    t = np.eye(4)
    t[:3,:3] = Rotation.from_quat(pose[3:7]).as_matrix()
    t[:3,3] = pose[:3]
    return t


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--state',type=Path,default=Path('configs/g2_local/S-actual-state.npz'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--normal-weight',type=float,default=.25)
    p.add_argument('--limit-margin',type=float,default=0.)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    d=np.load(args.state)
    print('state keys',list(d))
    geom=DigitGeometry(max_face_axes=32);fk=geom.w
    plan=json.loads(Path('configs/g2_local/prefix/candidate2-thumb-slider-contact-corridor-execution.json').read_text())['thumb_slider_geometry']
    # These source arrays are measured at the actual acquisition frame.
    q=np.array(d['q'],dtype=np.float64)
    assert q.shape == (20,)
    relative=np.linalg.inv(matrix(d['object_rigid_state']))@matrix(d['wrist'])
    anchor=np.array(plan['anchor_local']);link=plan['contact_link']
    def pose(v):
        full=q.copy();full[16:]=v
        f=relative@fk.forward(full)[link]
        return f[:3,:3]@anchor+f[:3,3], f[:3,0]
    seed=q[16:].copy();start,normal=pose(seed);rows=[]
    for shift in np.linspace(0,.04,41):
        target=start+np.array([0,0,shift]);previous=seed.copy()
        def residual(v):
            point,n=pose(v)
            return np.r_[(point-target)*100,(n-normal)*args.normal_weight,(v-previous)*.005]
        lo=fk.lower[16:]+args.limit_margin;hi=fk.upper[16:]-args.limit_margin
        fit=least_squares(residual,np.clip(seed,lo+1e-7,hi-1e-7),
            bounds=(lo,hi),max_nfev=100,diff_step=1e-5)
        seed=fit.x;point,n=pose(seed);full=q.copy();full[16:]=seed
        row=dict(shift_m=float(shift),q_thumb=seed.tolist(),point_error_m=float(np.linalg.norm(point-target)),
            normal_rotation_rad=float(np.arccos(np.clip(n@normal,-1,1))),
            limit_margin_rad=float(np.minimum(seed-fk.lower[16:],fk.upper[16:]-seed).min()))
        if round(shift*1000)%5==0:
            gaps=geom.gaps(full,relative,float(d['slider'])+shift)
            row.update(body_gap_m=min(g['gap_lower_bound_m'] for g in gaps if g['knife_link']=='link_0'),
                slider_gap_m=min(g['gap_lower_bound_m'] for g in gaps if g['knife_link']=='link_1'),
                other_fingers_gap_m=min(g['gap_lower_bound_m'] for g in geom.self_gaps(full,'thumb')))
        rows.append(row)
    result=dict(scope='geometric only; no physics execution or holding evidence',source=str(args.state),
        normal_weight=args.normal_weight,planning_limit_margin_rad=args.limit_margin,
        contact_link=link,anchor_local=anchor.tolist(),point_in_knife_at_start=start.tolist(),
        path='0 to40mm along knife +z, fixed body, material point and approximate normal',rows=rows)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(max_point_error_m=max(v['point_error_m'] for v in rows),start=rows[0],end=rows[-1])))


if __name__=='__main__':main()
