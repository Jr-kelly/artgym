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
    p.add_argument('--normal-path',choices=['linear','radial'],default='linear')
    p.add_argument('--squeeze-schedule',choices=['linear','hold'],default='linear')
    p.add_argument('--motion',choices=['simultaneous','gait','wave'],default='simultaneous');a=p.parse_args()
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
        fraction=i/a.knots;progress=np.full(5,fraction);wrist_fraction=fraction
        if a.motion=='gait':
            # Thumb/ring are an opposing pair at nearly the same longitudinal
            # location. They hold the knife while the other digits get below.
            progress=np.clip([(fraction-.75)/.25,fraction/.45,(fraction-.15)/.40,(fraction-.75)/.25,(fraction-.30)/.35],0,1)
            wrist_fraction=min(fraction/.65,1.)
        elif a.motion=='wave':
            segment=min(int(fraction*4),3);within=fraction*4-segment
            lead=min(within*2,1);lag=max(within*2-1,0)
            lead=lead*lead*(3-2*lead);lag=lag*lag*(3-2*lag)
            progress=(segment+np.array([lag,lead,lead,lag,lead]))/4
        target=np.empty_like(contact0);directions=[]
        for j,value in enumerate(progress):
            target[j]=contact0[j]+(corner[j]-contact0[j])*min(value/.5,1) if value<.5 else corner[j]+(contact1[j]-corner[j])*((value-.5)/.5)
            angle=value*np.pi/2
            if a.normal_path=='radial':
                corner_angle=np.arctan2(.004,.0095)
                angle=corner_angle*value/.5 if value<.5 else np.arctan2(.004,.0095*(1-(value-.5)/.5))
            if 'contact_normals' in initial:
                normal=np.asarray(initial['contact_normals'][j])*(1 if j==0 else -1)
                initial_angle=np.arctan2(normal[1],normal[0])
                angle=angle+initial_angle*max(1-value/.5,0)
            directions.append(np.array([np.cos(angle),np.sin(angle),0]))
        wrist=np.eye(4);wrist[:3,:3]=interpolate([wrist_fraction]).as_matrix()[0];wrist[:3,3]=p0[:3,3]*(1-wrist_fraction)+p1[:3,3]*wrist_fraction
        anchor=q0*(1-wrist_fraction)+q1*wrist_fraction
        def residual(values,overtravel=0):
            offset=values[:3];values=values[3:]
            actual_wrist=wrist.copy();actual_wrist[:3,3]+=offset
            frames=w.forward(values);errors=[]
            for j,f in enumerate(FINGERS):
                vertices=[]
                for suffix in ['pad_link','link4']:
                    n='hand_r_'+f+'_'+suffix;t=actual_wrist@frames[n];vertices.append(mesh[n]@t[:3,:3].T+t[:3,3])
                v=np.concatenate(vertices);normal=directions[j]*(1 if j==0 else -1)
                projected=v@normal;weights=np.exp(-(projected-projected.min())/.0003);weights/=weights.sum()
                support=(v*weights[:,None]).sum(0)
                travel=float(overtravel[j]) if np.ndim(overtravel) else overtravel
                errors.extend((support-(target[j]-normal*travel))*120)
            errors.extend((values-anchor)*.10);errors.extend((values-q)*.15)
            errors.extend(offset*(10000 if i in [0,a.knots] else 8));errors.extend((offset-last_offset)*5)
            return np.asarray(errors)
        result=least_squares(residual,np.r_[last_offset,np.clip(q,w.lower+1e-6,w.upper-1e-6)],
            bounds=(np.r_[np.full(3,-.03),w.lower],np.r_[np.full(3,.03),w.upper]),max_nfev=120,diff_step=1e-5)
        offset=result.x[:3].copy();q=result.x[3:].copy();touch=q.copy()
        release=fraction
        if a.squeeze_schedule=='hold':
            release=max((fraction-.8)/.2,0);release=release*release*(3-2*release)
        squeeze=initial.get('squeeze_m',.004)*(1-release)+.0004*release
        if a.motion=='gait':
            strong=initial.get('squeeze_m',.008)
            anchor_pressure=strong if fraction<.65 else strong+(0.001-strong)*min((fraction-.65)/.1,1)
            support_pressure=.0015+(strong-.0015)*(1-min(fraction/.1,1))
            squeeze=np.array([anchor_pressure,support_pressure,support_pressure,anchor_pressure,support_pressure])
            squeeze=squeeze*(1-max((fraction-.95)/.05,0))+.0004*max((fraction-.95)/.05,0)
        squeezed=least_squares(lambda v:residual(np.r_[offset,v],squeeze),q,bounds=(np.maximum(w.lower,q-.35),np.minimum(w.upper,q+.35)),max_nfev=60,diff_step=1e-5)
        command=squeezed.x
        if i==0:command=np.asarray(initial['close_q'])
        if i==a.knots:command=s[20:40].copy()
        error=residual(np.r_[offset,touch])[:15].reshape(5,3)/120
        actual_wrist=wrist.copy();actual_wrist[:3,3]+=offset
        rows.append(dict(alpha=fraction,wrist_in_knife=actual_wrist.tolist(),touch_q=touch.tolist(),command_q=command.tolist(),
            contact_targets=target.tolist(),contact_normals=[(n*(1 if j==0 else -1)).tolist() for j,n in enumerate(directions)],
            contact_residual_m=error.tolist(),optimization_cost=float(result.cost)))
        last_offset=offset
        print(json.dumps(dict(knot=i,cost=float(result.cost))),flush=True)
    a.output.write_text(json.dumps(dict(kind='contact_guided_seating',motion=a.motion,normal_path=a.normal_path,squeeze_schedule=a.squeeze_schedule,source_plan=str(a.grasp_plan),grasp=initial['grasp'],waypoints=rows,
        validation='Kinematic motor targets only; no physical success claimed; object must remain free.'),indent=2)+'\n')


if __name__=='__main__':main()
