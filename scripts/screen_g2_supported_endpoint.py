"""Bounded terminal geometry search from measured support, not acquisition.

Keep two actual knife contact points, vary the wrist by at most25mm per axis
and20deg in total, and seek a functional-branch thumb slider contact. All
outputs are geometry only until independently loaded before a first A step.
"""
import argparse,json,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve prior geometry')
    d=json.loads(a.source.read_text());t=np.load(d['source_trace']);i=d['source_step'];trial=Path(d['source_trace']).parent
    g=DigitGeometry(max_face_axes=32);full=DigitGeometry();w=g.w;q0=np.array(d['touch_q']);r0=np.array(d['wrist_in_knife']);slider=float(t['slider'][i])
    raw=[json.loads(s) for s in (trial/'knife-contact-pairs.jsonl').read_text().splitlines()];anchors=[]
    for finger in ['middle','ring']:
        points=[]
        for row in raw:
            if row['step']!=i:continue
            for side in [0,1]:
                if '_'+finger+'_' in row['body'+str(side)] and row['body'+str(1-side)]=='link_0':
                    points.append((row['body'+str(side)],np.array(row['localPos'+str(side)]),np.array(row['localPos'+str(1-side)])))
        link=max(set(p[0] for p in points),key=lambda v:sum(p[0]==v for p in points));points=[p for p in points if p[0]==link]
        anchors.append((link,np.mean([v[1] for v in points],axis=0),np.mean([v[2] for v in points],axis=0)))
    vertices=g.meshes['hand_r_thumb_pad_link'][0][0];hull=ConvexHull(vertices)
    root=Path(__file__).resolve().parents[1];cache=np.load(root/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[0]
    ids=np.r_[np.arange(8),np.arange(12,20)];z0=.010624586881962734+slider
    lower=np.r_[[-.025]*3,[-.35]*3,w.lower[ids],vertices.min(0),-.0045,z0-.014]
    upper=np.r_[[.025]*3,[.35]*3,w.upper[ids],vertices.max(0),.0045,z0+.014]
    def evaluate(x):
        r=r0.copy();r[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@r0[:3,:3];r[:3,3]+=x[:3]
        q=q0.copy();q[ids]=x[6:22];frames=w.forward(q);contacts=[]
        for link,anchor,target in anchors:
            frame=r@frames[link];contacts.append(frame[:3,:3]@anchor+frame[:3,3]-target)
        frame=r@frames['hand_r_thumb_pad_link'];thumb=frame[:3,:3]@x[22:25]+frame[:3,3]
        return q,r,np.array(contacts),thumb
    rows=[]
    for label,seed in [('functional',cache[16:20]),('actual',q0[16:])]:
        initial=q0.copy();initial[16:]=seed;x0=np.r_[np.zeros(6),initial[ids],vertices.mean(0),0,z0]
        def residual(x):
            q,r,contacts,thumb=evaluate(x)
            gaps=[v for f in ['thumb','middle','ring','index'] for v in g.gaps(q,r,slider,f)]
            selfgaps=[v for f in ['thumb','middle','ring','index'] for v in g.self_gaps(q,f)]
            return np.r_[contacts.ravel()*300,(thumb-[x[25],.0074,x[26]])*300,
                np.maximum(hull.equations[:,:3]@x[22:25]+hull.equations[:,3],0)*500,
                [min(v['gap_lower_bound_m']+.00015,0)*700 for v in gaps],
                [min(v['gap_lower_bound_m'],0)*400 for v in selfgaps],
                max(np.linalg.norm(x[3:6])-.35,0)*30,x[:3]*1.,x[3:6]*.01,(q[16:]-seed)*.004,(q[:16]-q0[:16])*.002]
        solved=least_squares(residual,np.clip(x0,lower+1e-7,upper-1e-7),bounds=(lower,upper),max_nfev=180,diff_step=1e-5)
        x=solved.x;q,r,contacts,thumb=evaluate(x);gaps={f:full.minimum_gap(q,r,slider,f) for f in ['thumb','index','middle','ring','pinky']}
        selfmin=min(v['gap_lower_bound_m'] for f in ['thumb','middle','ring','index'] for v in full.self_gaps(q,f))
        target=np.array([x[25],.0074,x[26]]);error=float(np.linalg.norm(thumb-target));hull_error=float(np.maximum(hull.equations[:,:3]@x[22:25]+hull.equations[:,3],0).max())
        ok=bool(error<.001 and np.linalg.norm(contacts,axis=1).max()<.001 and min(gaps.values())>=-.0005 and selfmin>=-.00005 and hull_error<.0001 and np.linalg.norm(x[3:6])<=.3501)
        row=dict(seed=label,nominal_q=q.tolist(),wrist_in_knife=r.tolist(),wrist_translation_delta_m=x[:3].tolist(),wrist_rotation_delta_rad=x[3:6].tolist(),
            support_errors_m=np.linalg.norm(contacts,axis=1).tolist(),thumb_error_m=error,thumb_anchor=x[22:25].tolist(),thumb_target=target.tolist(),
            whole_digit_gaps_m=gaps,self_min_gap_m=selfmin,anchor_hull_error_m=hull_error,geometric_candidate=ok,nfev=solved.nfev)
        rows.append(row);print(json.dumps(row),flush=True)
        a.output.write_text(json.dumps(dict(source=str(a.source),rows=rows,support_anchors=[dict(link=l,local=v.tolist(),target=p.tolist()) for l,v,p in anchors],
            scope='Bounded two-branch terminal geometry only; no physics, force, arm IK or continuous-path certificate.'),indent=2)+'\n')


if __name__=='__main__':main()
