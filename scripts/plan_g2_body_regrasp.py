"""Plan a functional-wrist body grip with the thumb outside the slider track.

An opened slider leaves the cached thumb contact without an opposing surface.
This acquisition-only plan puts the thumb on the body corner. It changes only
finger motor targets; both grasp retention and passive reclosure need physics.
"""
import argparse, json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_seating_feedback import ContactCorrection
from scripts.g2_kinematics import transform, ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--grasp',type=int,default=0);p.add_argument('--squeeze',type=float,default=.002)
    p.add_argument('--thumb-corner',choices=['negative','positive','face'],default='negative')
    p.add_argument('--gap',type=float,default=.012)
    p.add_argument('--wrist-axis-offset',type=float,default=0.,help='Acquisition-only wrist translation along the knife axis; bounded to 5mm. Changes planned motor poses, never physics state.')
    a=p.parse_args();c=ContactCorrection();w=c.w
    assert abs(a.wrist_axis_offset)<=.005
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[a.grasp]
    relative=np.linalg.inv(transform(s[40:43],s[43:47]))
    relative[2,3]+=a.wrist_axis_offset
    normals=np.array([[0.,1.,0.]]+[[0.,-1.,0.]]*4)
    targets=c.contacts(s[:20],relative,normals)[0]
    sign=0 if a.thumb_corner=='face' else (1 if a.thumb_corner=='positive' else -1)
    normals[0]=[sign,1.,0.];normals[0]/=np.linalg.norm(normals[0])
    targets[:,0]=np.clip(targets[:,0],-.007,.007);targets[:,1]=-.004
    targets[0,:2]=[sign*.0095,.004]
    meshes={}
    for name in w.forward(s[:20]):
        mesh=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(name+'.obj')
        meshes[name]=np.array([np.fromstring(line[2:],sep=' ') for line in mesh.read_text().splitlines() if line.startswith('v ')])
    def vertices(q):
        parts=[]
        for name,t in w.forward(q).items():
            t=relative@t;parts.append(meshes[name]@t[:3,:3].T+t[:3,3])
        return np.concatenate(parts)
    def solve(offset,seed):
        desired=targets+normals*offset
        def residual(q):
            points=c.contacts(q,relative,normals)[0]
            return np.r_[(points-desired).ravel()*200,np.maximum(vertices(q)[:,2]-.0725,0)*90,(q-s[:20])*.05]
        result=least_squares(residual,np.clip(seed,w.lower+1e-7,w.upper-1e-7),bounds=(w.lower,w.upper),max_nfev=120,diff_step=1e-5)
        error=np.linalg.norm(c.contacts(result.x,relative,normals)[0]-desired,axis=1)
        if error.max()>.001:
            a.output.with_suffix('.failure.json').write_text(json.dumps(dict(args=vars(a),offset_m=offset,contact_errors_m=error.tolist()),default=str,indent=2)+'\n')
            raise ValueError('Body regrasp IK error '+str(error.max()))
        return result.x,error
    touch,te=solve(0,s[:20]);opened,oe=solve(a.gap,touch);closed,ce=solve(-a.squeeze,touch)
    clearance=min(.0735-vertices(x*(1-f)+y*f)[:,2].max() for x,y in [(opened,touch),(touch,closed)] for f in np.linspace(0,1,21))
    data=dict(kind='body_corner_thumb_acquisition_grasp',grasp=a.grasp,end='positive',wrist_in_knife=relative.tolist(),
        open_q=opened.tolist(),touch_q=touch.tolist(),close_q=closed.tolist(),restore_q=s[20:40].tolist(),
        open_contact_error_m=oe.tolist(),touch_contact_error_m=te.tolist(),close_contact_error_m=ce.tolist(),
        min_table_clearance_m=float(clearance),contact_targets=targets.tolist(),contact_normals=normals.tolist(),
        squeeze_m=a.squeeze,open_gap_m=a.gap,thumb_corner=a.thumb_corner,
        wrist_axis_offset_m=a.wrist_axis_offset,
        validation='Motor target geometry only. Thumb uses body because slider is passively open. No policy success claimed.')
    a.output.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))


if __name__=='__main__':main()
