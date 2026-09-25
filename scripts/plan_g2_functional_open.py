"""Plan an open hand around a cached functional pose for table-supported regrasp."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.g2_seating_feedback import ContactCorrection

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--grasp',type=int,default=0);p.add_argument('--gap',type=float,default=.012)
    p.add_argument('--end',choices=['positive','negative'],default='positive');p.add_argument('--wrist-axis-offset',type=float,default=0.)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    s=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')[a.grasp]
    c=ContactCorrection();w=c.w;relative=np.linalg.inv(transform(s[40:43],s[43:47]));normals=np.array([[0,1,0]]+[[0,-1,0]]*4)
    relative[2,3]+=a.wrist_axis_offset
    q=s[:20].astype(float);points,_,_=c.contacts(q,relative,normals);targets=points+normals*a.gap
    meshes={}
    for n in w.forward(q):
        path=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
        meshes[n]=np.array([np.fromstring(l[2:],sep=' ') for l in path.read_text().splitlines() if l.startswith('v ')])
    def vertices(q):
        vv=[]
        for n,t in w.forward(q).items():
            t=relative@t;vv.append(meshes[n]@t[:3,:3].T+t[:3,3])
        return np.concatenate(vv)
    def residual(q):
        pts,_,_=c.contacts(q,relative,normals);v=vertices(q)
        side=1 if a.end=='positive' else -1
        return np.r_[(pts-targets).ravel()*150,np.maximum(v[:,2]*side-.0725,0)*80,
            np.minimum(np.max(abs(v)-np.array([.0095,.004,.0735]),axis=1)+.0003,0)*80,(q-s[:20])*.08]
    result=least_squares(residual,np.clip(q,w.lower+1e-7,w.upper-1e-7),bounds=(w.lower,w.upper),max_nfev=100,diff_step=1e-5)
    points,_,_=c.contacts(result.x,relative,normals);error=np.linalg.norm(points-targets,axis=1)
    side=1 if a.end=='positive' else -1
    clearance=min(.0735-(vertices(result.x*(1-f)+s[20:40]*f)[:,2]*side).max() for f in np.linspace(0,1,21))
    data=dict(kind='functional_open_close_motor_plan',grasp=a.grasp,wrist_in_knife=relative.tolist(),open_q=result.x.tolist(),close_q=s[20:40].tolist(),
        open_gap_m=a.gap,open_contact_error_m=error.tolist(),min_table_clearance_m=float(clearance),
        end=a.end,wrist_axis_offset_m=a.wrist_axis_offset,
        validation='Geometry only; knife remains free and must be actually standing on its modeled '+a.end+'-z end.')
    a.output.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))

if __name__=='__main__':main()
