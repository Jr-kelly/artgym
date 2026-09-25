"""Bounded geometric side-pinch candidate for a knife lying flat on a table.

Only plans motor targets; the physics runner is the sole pickup validator.
Coordinates here are knife-local (y up, z length). No scene state is modified.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics,FINGERS
from scripts.g2_kinematics import transform

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--roll',type=float,default=-90);p.add_argument('--grasp',type=int,default=0)
    p.add_argument('--side-normal',action='store_true',help='Require pad support point on opposing side plane, not arbitrary nearest vertex.')
    p.add_argument('--contact-height',type=float,default=.0035)
    p.add_argument('--squeeze',type=float,default=.002,help='Motor target overtravel per side (m), not a state penetration write.')
    p.add_argument('--allow-close-overtravel',action='store_true')
    p.add_argument('--exclude-finger',choices=FINGERS,action='append',default=[],help='Do not require this digit to pinch; retain its table/body clearance terms and report it explicitly.')
    a=p.parse_args();w=WujiKinematics()
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[a.grasp]
    meshes={}
    for n in w.forward(s[:20]):
        path=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
        v=np.array([np.fromstring(l[2:],sep=' ') for l in path.read_text().splitlines() if l.startswith('v ')])
        meshes[n]=v[ConvexHull(v).vertices]
    base=transform(quaternion=Rotation.from_euler('z',a.roll,degrees=True).as_quat())@np.linalg.inv(transform(s[40:43],s[43:47]))
    # Targets on opposing upper side edges. They avoid the slider and table.
    contact=np.array([[.0095,.0035,-.019],[-.0095,.0035,.0385],[-.0095,.0035,.0016],
                      [-.0095,.0035,-.022],[-.0095,.0035,-.047]])
    contact[:,1]=a.contact_height
    lower=np.r_[[-.04,-.02,-.025],[-.35,-.35,-.35],w.lower]
    upper=np.r_[[.04,.05,.025],[.35,.35,.35],w.upper]
    x0=np.r_[np.zeros(6),s[:20]].astype(float)

    def frames(x):
        wrist=base.copy();wrist[:3,3]+=x[:3]
        wrist[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@base[:3,:3]
        links=w.forward(x[6:]);points={}
        for n,t in links.items():
            t=wrist@t;points[n]=meshes[n]@t[:3,:3].T+t[:3,3]
        return wrist,points

    def residual(x,targets,table=True,anchor=None,body_clearance=True):
        wrist,pts=frames(x);errors=[]
        for i,f in enumerate(FINGERS):
            if f in a.exclude_finger:continue
            v=np.concatenate([pts['hand_r_'+f+'_pad_link'],pts['hand_r_'+f+'_link4']])
            # Smooth-ish local vertex minimum, reevaluated per residual call.
            if a.side_normal:
                sign=1 if i==0 else -1
                signed=sign*v[:,0];weights=np.exp(-(signed-signed.min())/.0003);weights/=weights.sum()
                support=(v*weights[:,None]).sum(0)
                errors.extend((support-targets[i])*200)
            else:
                distances=np.linalg.norm(v-targets[i],axis=1);j=distances.argmin()
                errors.extend((v[j]-targets[i])*200)
        for n,v in pts.items():
            if table: errors.extend(np.minimum(v[:,1]+.003,0)*90)
            # Prevent deep knife-body penetration in planned touching pose.
            d=np.abs(v)-np.array([.0095,.004,.0735])
            errors.extend(np.minimum(np.max(d,axis=1)+.0004,0)*(100 if body_clearance else 0))
        errors.extend((x[6:]-s[:20])*.012)
        errors.extend(x[:6]*.15)
        if anchor is not None:errors.extend((x[:6]-anchor[:6])*1000)
        return np.asarray(errors)

    result=least_squares(residual,np.clip(x0,lower+1e-6,upper-1e-6),args=(contact,),bounds=(lower,upper),max_nfev=160,diff_step=1e-5)
    x=result.x;wrist,pts=frames(x)
    touch_errors=[]
    for i,f in enumerate(FINGERS):
        if f in a.exclude_finger:
            touch_errors.append(None);continue
        v=np.concatenate([pts['hand_r_'+f+'_pad_link'],pts['hand_r_'+f+'_link4']])
        touch_errors.append(float(np.linalg.norm(v-contact[i],axis=1).min()))
    # Keep wrist fixed for open/close. A few mm of target overtravel produces
    # force through the existing finite-stiffness drives, not external forces.
    def finger_targets(offset):
        targets=contact.copy();targets[:,0]+=np.array([1,-1,-1,-1,-1])*offset
        def fixed_residual(q):
            return np.r_[residual(np.r_[x[:6],q],targets,True,body_clearance=not(a.allow_close_overtravel and offset<0)),(q-x[6:])*.5]
        r=least_squares(fixed_residual,x[6:],bounds=(np.maximum(w.lower,x[6:]-.5),np.minimum(w.upper,x[6:]+.5)),max_nfev=100,diff_step=1e-5)
        return r.x
    opened=finger_targets(.012);closed=finger_targets(-a.squeeze)
    report=dict(kind='edge_pinch_geometry_candidate',grasp=a.grasp,roll=a.roll,side_normal=a.side_normal,
        excluded_fingers=a.exclude_finger,active_fingers=[f for f in FINGERS if f not in a.exclude_finger],
        squeeze_m=a.squeeze,allow_close_overtravel=a.allow_close_overtravel,
        wrist_in_knife=wrist.tolist(),touch_q=x[6:].tolist(),open_q=opened.tolist(),close_q=closed.tolist(),
        contact_targets=contact.tolist(),contact_error_m=touch_errors,
        min_table_clearance_m=float(min(v[:,1].min()+.004 for v in pts.values())),
        intersecting_links={n:float(v[:,1].min()+.004) for n,v in pts.items() if v[:,1].min()+.004<0},
        optimization_cost=float(result.cost),validation='Not a physical pickup; must execute continuous B trial.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
