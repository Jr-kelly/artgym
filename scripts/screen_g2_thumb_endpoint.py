"""Bounded thumb endpoint geometry screen, never a physical feasibility claim.

Use a distal pad material point selected in the verified functional grasp rather
than requiring the entire distal link to lie above an infinite slider plane.
Whole-digit convex gaps are checked after each solve. No simulator is created.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--target-z',type=float,action='append',help='Closed slider top contact longitudinal coordinate; repeated at most3 times.')
    p.add_argument('--anchor-mode',choices=['vertex','face'],default='face');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];g=DigitGeometry();w=g.w
    d=json.loads(a.source.read_text());q=np.array(d['touch_q']);relative=np.array(d['wrist_in_knife'])
    s=np.load(root/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    functional=np.linalg.inv(transform(s[40:43],s[43:47]));link='hand_r_thumb_pad_link'
    vertices=g.meshes[link][0][0];f=functional@w.forward(s[:20])[link]
    reference_target=np.array([0,.007,-.009]);world=vertices@f[:3,:3].T+f[:3,3]
    anchor=vertices[np.linalg.norm(world-reference_target,axis=1).argmin()]
    if a.anchor_mode=='face':
        candidates=[]
        for triangle in world[ConvexHull(world).simplices]:
            x,y,z=triangle;uv=np.linalg.lstsq(np.column_stack([y-x,z-x]),reference_target-x,rcond=None)[0]
            if min(uv)>=0 and uv.sum()<=1:candidates.append(x+uv[0]*(y-x)+uv[1]*(z-x))
            for start,end in [(x,y),(y,z),(z,x)]:
                v=end-start;alpha=np.clip((reference_target-start)@v/(v@v),0,1);candidates.append(start+alpha*v)
        closest=min(candidates,key=lambda v:np.linalg.norm(v-reference_target));anchor=f[:3,:3].T@(closest-f[:3,3])
    rows=[]
    targets=[[0,.0075,z] for z in a.target_z] if a.target_z else [[0,.0075,-.02205],[-.004,.0075,-.02205],[-.015,.015,-.02205]]
    if len(targets)>3:raise ValueError('Bounded screen permits at most3 targets')
    for target in targets:
        for label,seed in [('actual',q[16:]),('functional',s[16:20])]:
            def evaluate(v):
                values=q.copy();values[16:]=v;frames=w.forward(values);points=[]
                for name,meshes in g.meshes.items():
                    if '_thumb_' not in name:continue
                    t=relative@frames[name]
                    for verts,_ in meshes:points.append(verts@t[:3,:3].T+t[:3,3])
                frame=relative@frames[link];point=frame[:3,:3]@anchor+frame[:3,3]
                return values,point,np.concatenate(points)
            def residual(v):
                _,point,points=evaluate(v)
                body=np.max(abs(points)-np.array([.0095,.004,.0735]),axis=1)
                return np.r_[(point-target)*200,np.minimum(body-.0002,0)*400,(v-seed)*.005]
            result=least_squares(residual,np.clip(seed,w.lower[16:]+1e-6,w.upper[16:]-1e-6),bounds=(w.lower[16:],w.upper[16:]),max_nfev=220,diff_step=1e-5)
            values,point,_=evaluate(result.x);gaps=g.gaps(values,relative,-.032674588)
            error=float(np.linalg.norm(point-target));gap=min(r['gap_lower_bound_m'] for r in gaps)
            rows.append(dict(target_m=target,seed=label,q=result.x.tolist(),point_error_m=error,whole_thumb_gap_m=gap,
                             geometric_candidate=bool(error<.001 and gap>=-.0005),gaps=gaps))
    out=dict(source=str(a.source),anchor_link=link,anchor_mode=a.anchor_mode,anchor_local_m=anchor.tolist(),rows=rows,
             limitation='Endpoints only; no swept-path, support, contact-control or policy evidence. Negative convex gaps do not measure penetration depth.')
    a.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in row.items() if k not in ['q','gaps']} for row in rows]))


if __name__=='__main__':main()
