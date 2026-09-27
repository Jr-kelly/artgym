"""Compare a local reset to an actual continuous tail without equating success."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--local',type=Path,required=True)
    p.add_argument('--continuous',type=Path,required=True)
    p.add_argument('--frame',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    local=np.load(a.local); original=np.load(a.continuous)
    count=min(len(local['time']),len(original['time'])-a.frame)
    rows=[]
    for step in sorted(set([0,1,3,15,30,60,150,300,count-1])):
        if step>=count:continue
        obj=local['object_rigid_state'][step,0,:7];old=original['object'][a.frame+step]
        rows.append(dict(step=step,time_seconds=step/30,
            measured_q_max_difference_rad=float(abs(local['q'][step,0]-original['q'][a.frame+step]).max()),
            arm_q_max_difference_rad=float(abs(local['all_dof_position'][step,0,:7]-original['all_dof_position'][a.frame+step,:7]).max()),
            object_position_difference_m=float(np.linalg.norm(obj[:3]-old[:3])),
            object_rotation_difference_rad=float((Rotation.from_quat(obj[3:]).inv()*Rotation.from_quat(old[3:])).magnitude()),
            slider_difference_m=float(abs(local['slider'][step,0]-original['slider'][a.frame+step]))))
    result=dict(scope='same controller and initial recorded state, different PhysX contact cache; no exact replay claim',
        local=str(a.local),continuous=str(a.continuous),frame=a.frame,samples=rows)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
