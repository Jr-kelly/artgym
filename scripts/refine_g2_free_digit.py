"""Bounded collision-aware refinement of one unused acquisition digit.

Geometry only. Preserve the wrist and other support digits, adjust index plus
middle so the unused index is clear of the knife and the middle contact stays
at its original planned location. No simulator or physics settings are changed.
"""
import argparse
import json
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_seating_feedback import ContactCorrection


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous geometry output')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);c=ContactCorrection()
    relative=np.array(d['wrist_in_knife']);normals=np.array(d['contact_normals'])
    originals=[np.array(d[key]) for key in ['open_q','touch_q','close_q']]
    desired=[c.contacts(q,relative,normals)[0][2] for q in originals]
    # One index pose throughout closure; middle contact remains separate at each
    # phase. The contact motor overtravel remains the original source target.
    lo=np.r_[g.w.lower[:4],np.tile(g.w.lower[4:8],3)]
    hi=np.r_[g.w.upper[:4],np.tile(g.w.upper[4:8],3)]
    seed=np.concatenate([np.array([0.,.37,.4,.2])]+[q[4:8] for q in originals])
    def poses(x):
        out=[]
        for i,old in enumerate(originals):
            q=old.copy();q[:4]=x[:4];q[4:8]=x[4+4*i:8+4*i];out.append(q)
        return out
    def residual(x):
        errors=[]
        for i,q in enumerate(poses(x)):
            errors.extend((c.contacts(q,relative,normals)[0][2]-desired[i])*300)
            index_gaps=g.gaps(q,relative,-.032674588,'index')
            errors.extend(min(v['gap_lower_bound_m']-.0041,0)*300 for v in index_gaps)
            pairs=g.self_gaps(q,'index')
            pairs += [v for v in g.self_gaps(q,'middle') if '_ring_' in v['other_link']]
            errors.extend(min(v['gap_lower_bound_m']-.0003,0)*600 for v in pairs)
            frames=g.w.forward(q)
            for name in ['hand_r_index_link1','hand_r_index_link2','hand_r_index_link3','hand_r_index_link4','hand_r_index_pad_link']:
                frame=relative@frames[name]
                for vertices,_ in g.meshes[name]:
                    xyz=vertices@frame[:3,:3].T+frame[:3,3]
                    # Source has been transformed to slider-up knife coordinates,
                    # so physical table lies toward +y for initial slider-down.
                    errors.extend(np.maximum(xyz[:,1]-.0035,0)*300)
            errors.extend((q[4:8]-originals[i][4:8])*.02)
        errors.extend((x[:4]-seed[:4])*.002)
        return np.asarray(errors)
    result=least_squares(residual,np.clip(seed,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=120,diff_step=1e-5)
    rows=[];g=DigitGeometry()
    for i,(key,q) in enumerate(zip(['open_q','touch_q','close_q'],poses(result.x))):
        pairs=g.self_gaps(q,'index')+[v for v in g.self_gaps(q,'middle') if '_ring_' in v['other_link']]
        rows.append(dict(stage=key,middle_point_error_m=float(np.linalg.norm(c.contacts(q,relative,normals)[0][2]-desired[i])),
            index_knife_gap_m=g.minimum_gap(q,relative,-.032674588,'index'),
            minimum_self_pair=min(pairs,key=lambda v:v['gap_lower_bound_m']),q=q.tolist()))
        d[key]=q.tolist()
    d.update(collision_refinement=dict(source=str(a.source),rows=rows,cost=float(result.cost),nfev=result.nfev,
        scope='Geometric refinement only, no physics evidence; other fingers/wrist fixed, same source contact motor target.'),validation='Geometry only; requires whole path and actual continuous pickup validation.')
    a.output.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d['collision_refinement']))


if __name__=='__main__':main()
