"""Contact-guided, bounded in-air wrist/finger motor path toward cached function grasp.

The object is a reference frame for planning only. The runner never constrains
or sets its pose, and must validate every path against free-body dynamics.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation,Slerp
from scripts.wuji_kinematics import WujiKinematics,FINGERS
from scripts.g2_kinematics import transform

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--grasp-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--knots',type=int,default=24)
    p.add_argument('--normal-path',choices=['linear','radial'],default='linear');a=p.parse_args()
    initial=json.loads(a.grasp_plan.read_text());w=WujiKinematics()
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[initial['grasp']]
    p0=np.asarray(initial['wrist_in_knife']);p1=np.linalg.inv(transform(s[40:43],s[43:47]));q0=np.array(initial['touch_q']);q1=s[:20].astype(float)
    interpolate=Slerp([0,1],Rotation.from_matrix([p0[:3,:3],p1[:3,:3]]))
    mesh={}
    for f in FINGERS:
        for suffix in ['pad_link','link4']:
            n='hand_r_'+f+'_'+suffix;file=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
            v=np.array([np.fromstring(l[2:],sep=' ') for l in file.read_text().splitlines() if l.startswith('v ')]);mesh[n]=v[ConvexHull(v).vertices]
    contact0=np.array(initial['contact_targets']);contact1=np.array([[.0026,.007,-.009],[.003,-.004,.0445],[0,-.004,.0016],[.0085,-.004,-.022],[.003,-.004,-.05]])
    corner=contact0.copy();corner[:,1]=[.004,-.004,-.004,-.004,-.004]
    q=q0.copy();rows=[];last_offset=np.zeros(3)
    for i in range(a.knots+1):
        fraction=i/a.knots;target=contact0+(corner-contact0)*min(fraction/.5,1) if fraction<.5 else corner+(contact1-corner)*((fraction-.5)/.5)
        wrist=np.eye(4);wrist[:3,:3]=interpolate([fraction]).as_matrix()[0];wrist[:3,3]=p0[:3,3]*(1-fraction)+p1[:3,3]*fraction
        angle=fraction*np.pi/2
        if a.normal_path=='radial':
            corner_angle=np.arctan2(.004,.0095)
            angle=corner_angle*fraction/.5 if fraction<.5 else np.arctan2(.004,.0095*(1-(fraction-.5)/.5))
        direction=np.array([np.cos(angle),np.sin(angle),0])
        anchor=q0*(1-fraction)+q1*fraction
        def residual(values,overtravel=0):
            offset=values[:3];values=values[3:]
            actual_wrist=wrist.copy();actual_wrist[:3,3]+=offset
            frames=w.forward(values);errors=[]
            for j,f in enumerate(FINGERS):
                vertices=[]
                for suffix in ['pad_link','link4']:
                    n='hand_r_'+f+'_'+suffix;t=actual_wrist@frames[n];vertices.append(mesh[n]@t[:3,:3].T+t[:3,3])
                v=np.concatenate(vertices);normal=direction*(1 if j==0 else -1)
                projected=v@normal;weights=np.exp(-(projected-projected.min())/.0003);weights/=weights.sum()
                support=(v*weights[:,None]).sum(0)
                errors.extend((support-(target[j]-normal*overtravel))*120)
            errors.extend((values-anchor)*.10);errors.extend((values-q)*.15)
            errors.extend(offset*(10000 if i in [0,a.knots] else 8));errors.extend((offset-last_offset)*5)
            return np.asarray(errors)
        result=least_squares(residual,np.r_[last_offset,np.clip(q,w.lower+1e-6,w.upper-1e-6)],
            bounds=(np.r_[np.full(3,-.03),w.lower],np.r_[np.full(3,.03),w.upper]),max_nfev=120,diff_step=1e-5)
        offset=result.x[:3].copy();q=result.x[3:].copy();touch=q.copy()
        squeeze=initial.get('squeeze_m',.004)*(1-fraction)+.0004*fraction
        squeezed=least_squares(lambda v:residual(np.r_[offset,v],squeeze),q,bounds=(np.maximum(w.lower,q-.35),np.minimum(w.upper,q+.35)),max_nfev=60,diff_step=1e-5)
        command=squeezed.x
        if i==a.knots:command=s[20:40].copy()
        error=residual(np.r_[offset,touch])[:15].reshape(5,3)/120
        actual_wrist=wrist.copy();actual_wrist[:3,3]+=offset
        rows.append(dict(alpha=fraction,wrist_in_knife=actual_wrist.tolist(),touch_q=touch.tolist(),command_q=command.tolist(),
            contact_residual_m=error.tolist(),optimization_cost=float(result.cost)))
        last_offset=offset
        print(json.dumps(dict(knot=i,cost=float(result.cost))),flush=True)
    a.output.write_text(json.dumps(dict(kind='contact_guided_seating',normal_path=a.normal_path,source_plan=str(a.grasp_plan),grasp=initial['grasp'],waypoints=rows,
        validation='Kinematic motor targets only; no physical success claimed; object must remain free.'),indent=2)+'\n')


if __name__=='__main__':main()
