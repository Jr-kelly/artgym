"""Search palm-backed grasps with the slider facing out from the palm."""
import json
import numpy as np
from scipy.spatial.transform import Rotation

from scripts.build_wuji_knife_demo import GraspBuilder
from scripts.wuji_kinematics import ROOT,FINGERS


def main():
    meta=json.loads((ROOT/'assets/objects/knife_wuji_demo/000/parameters.json').read_text())
    b=GraspBuilder(meta);h=b.hand
    qs,centers,rotations,params,errors=[],[],[],[],[]
    for angle in (60,90,110):
        rot=Rotation.from_euler('y',angle,degrees=True);r=rot.as_matrix()
        for x in (.026,.034,.042):
            for z in (.086,.096,.106):
                center=np.array([x,0,z])
                q=np.clip(np.array([0 if name.endswith('joint2') else 1.1 for name in h.names]),h.lower,h.upper)
                err=[]
                for finger in FINGERS:
                    thumb=finger=='thumb'
                    y=dict(index=.028,middle=.007,ring=-.014,pinky=-.034).get(finger,.025)
                    # Fingers curl around the handle; thumb presses the slider.
                    if thumb:
                        target=center+r@np.array([0,y,meta['handle_size'][2]/2+.006])
                    else:
                        target=center+r@np.array([.009,y,meta['handle_size'][2]/2])
                    q,e=b.solve_surface(finger,target,r[:,2],q,center,r,clearance=-.001)
                    err.append(e)
                qs.append(q);centers.append(center);rotations.append(rot.as_quat());params.append([angle,x,z]);errors.append(err)
                print(len(qs),params[-1],np.round(np.array(err)*1000,2),flush=True)
    np.savez(ROOT/'tmp/knife-demo/side.npz',qpos=qs,centers=centers,rotations=rotations,parameters=params,errors=errors)


if __name__=='__main__':
    main()
