"""Pre-physics tabletop clearance of the three previously trained grasps."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import WujiKinematics

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    w=WujiKinematics();g=G2Kinematics()
    states=np.load(ROOT/'caches/initial_grasp/wuji/knife_wuji_bridge3_20260922/000/train/valid_grasps.npy')
    meshes={}
    for n in w.forward(states[0,:20]):
        path=ROOT/'assets/hands/wuji_artbot/meshes/collision'/(n+'.obj')
        meshes[n]=np.array([np.fromstring(l[2:],sep=' ') for l in path.read_text().splitlines() if l.startswith('v ')])
    records=[]
    for row,s in enumerate(states):
        for face,angle in [('slider_up',90),('slider_down',-90)]:
            obj=transform([.5,-.3,.754 if face=='slider_up' else .757],Rotation.from_euler('x',angle,degrees=True).as_quat())
            wrist=obj@np.linalg.inv(transform(s[40:43],s[43:47]));frames=w.forward(s[:20]);clearance={}
            for n,t in frames.items():
                v=(np.c_[meshes[n],np.ones(len(meshes[n]))]@(wrist@t).T)[:,:3]
                clearance[n]=float(v[:,2].min()-.75)
            q,err=g.solve(wrist)
            records.append(dict(grasp=row,placement=face,min_clearance_m=min(clearance.values()),
                intersecting_links={k:v for k,v in clearance.items() if v<0},wrist_position=wrist[:3,3].tolist(),
                ik=err,arm_q=q.tolist(),warning='Negative clearance is a geometry screen, not a physics pickup result.'))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ['intersecting_links','arm_q']} for r in records]))


if __name__=='__main__':main()
