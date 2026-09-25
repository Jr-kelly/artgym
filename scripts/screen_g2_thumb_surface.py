"""Screen arbitrary thumb-pad material points against the closed slider top.

Unlike the functional-anchor screen, the contact point is optimized inside the
pad convex hull. Whole-thumb knife separation and other-digit separation are
checked independently. Positive endpoints are still not trajectory evidence.
"""
import argparse
import json
from pathlib import Path
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve previous screen')
    d=json.loads(a.source.read_text());g=DigitGeometry(max_face_axes=32);full_geometry=DigitGeometry();w=g.w
    q=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife'])
    vertices=g.meshes['hand_r_thumb_pad_link'][0][0];hull=ConvexHull(vertices)
    cache=np.load(Path(__file__).resolve().parents[1]/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    slider=-.032674588;z0=.010624586881962734+slider
    lower=np.r_[w.lower[16:],vertices.min(0),-.0045,z0-.014]
    upper=np.r_[w.upper[16:],vertices.max(0),.0045,z0+.014]
    rows=[]
    def evaluate(x):
        proposed=q.copy();proposed[16:]=x[:4]
        frame=relative@w.forward(proposed)['hand_r_thumb_pad_link']
        point=frame[:3,:3]@x[4:7]+frame[:3,3]
        return proposed,point
    for label,seed in [('actual',q[16:]),('functional',cache[16:20])]:
        x0=np.r_[seed,vertices.mean(0),0.,z0]
        def residual(x):
            proposed,point=evaluate(x);target=np.array([x[7],.0074,x[8]])
            gaps=g.gaps(proposed,relative,slider)
            self_gaps=g.self_gaps(proposed,'thumb')
            return np.r_[(point-target)*250,
                np.maximum(hull.equations[:,:3]@x[4:7]+hull.equations[:,3],0)*400,
                [min(v['gap_lower_bound_m']+.0003,0)*500 for v in gaps],
                [min(v['gap_lower_bound_m']-.0003,0)*200 for v in self_gaps],
                (x[:4]-seed)*.002]
        solved=least_squares(residual,np.clip(x0,lower+1e-7,upper-1e-7),bounds=(lower,upper),max_nfev=120,diff_step=1e-5)
        proposed,point=evaluate(solved.x);gap=full_geometry.minimum_gap(proposed,relative,slider)
        target=np.array([solved.x[7],.0074,solved.x[8]])
        error=float(np.linalg.norm(point-target));hull_error=float(np.maximum(hull.equations[:,:3]@solved.x[4:7]+hull.equations[:,3],0).max())
        self_gap=min(full_geometry.self_gaps(proposed,'thumb'),key=lambda v:v['gap_lower_bound_m'])
        rows.append(dict(seed=label,q=solved.x[:4].tolist(),anchor_local=solved.x[4:7].tolist(),target=target.tolist(),
            point_error_m=error,anchor_hull_violation_m=hull_error,whole_thumb_gap_m=gap,minimum_self_pair=self_gap,
            geometric_candidate=bool(error<.001 and hull_error<.0001 and gap>=-.0005 and self_gap['gap_lower_bound_m']>=0),nfev=solved.nfev))
    out=dict(source=str(a.source),slider_position_m=slider,rows=rows,
        limitation='Two local branches, arbitrary point in pad hull; screening only. Not proof of global reachability or physical support.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))


if __name__=='__main__':main()
