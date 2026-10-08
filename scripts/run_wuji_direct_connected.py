"""One fresh tabletop episode of the direct route, with explicit case inputs."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--dx',type=float,default=0)
    p.add_argument('--dy',type=float,default=0);p.add_argument('--yaw',type=float,default=0)
    p.add_argument('--pose-bias-x',type=float,default=0)
    p.add_argument('--close-camera-direction',type=float,nargs=3,default=[.65,-.4,.8])
    p.add_argument('--support-camera-direction',type=float,nargs=3)
    p.add_argument('--knife-asset',type=Path,default=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf'))
    p.add_argument('--resistance',type=Path,default=Path('research/newknife-20261005/resistance-constant.json'))
    p.add_argument('--uncertainty',required=True);p.add_argument('--decision',required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    prefix=json.loads(a.prefix.read_text());O=np.array(prefix['physical_initial_object_world'])
    O[:3,:3]=Rotation.from_euler('z',a.yaw,degrees=True).as_matrix()@O[:3,:3]
    O[0,3]+=a.dx;O[1,3]+=a.dy
    G=KnifeGeometry(a.knife_asset.parent/'spec.json');O=G.table_pose(O)
    prefix['physical_initial_object_world']=O.tolist();prefix['direct_pickup']['pose_bias_x_m']=a.pose_bias_x
    prefix['direct_pickup']['knife_spec']=str(a.knife_asset.parent/'spec.json')
    prefix['case_inputs']=dict(physical_dx_m=a.dx,physical_dy_m=a.dy,physical_yaw_deg=a.yaw,
        estimate_bias_x_m=a.pose_bias_x,asset=str(a.knife_asset),resistance=str(a.resistance))
    (a.output/'prefix.json').write_text(json.dumps(prefix,indent=2))
    cmd=json.loads(Path('runs/flat-table-20261006/direct/development/center-load-feedback-v8/command.json').read_text());cmd[0]=sys.executable
    for key,value in [('--output',str(a.output/'simulation')),('--flat-table-prefix',str(a.output/'prefix.json')),
                      ('--knife-asset',str(a.knife_asset)),('--newknife-resistance',str(a.resistance))]:
        cmd[cmd.index(key)+1]=value
    cmd += ['--close-camera-direction']+[str(x) for x in a.close_camera_direction]
    if a.support_camera_direction:
        cmd += ['--support-camera-direction']+[str(x) for x in a.support_camera_direction]
    (a.output/'command.json').write_text(json.dumps(cmd,indent=2))
    record('direct_fresh_connected_start',[str(a.output/'command.json'),str(a.output/'prefix.json')],
        config=dict(uncertainty=a.uncertainty,decision=a.decision,seconds=prefix['duration_s'],
            case=prefix['case_inputs'],scope='One fresh episode; no recorded initializer. Prior motor trajectories adapt to current stage observations.'),
        updates={'add_active_jobs':[str(a.output)]},next_step=a.decision)
    try:subprocess.run(cmd,check=True)
    finally:record('direct_fresh_connected_terminal',[str(a.output/'simulation')],updates={'remove_active_jobs':[str(a.output)]},
        next_step='Inspect fullactual stage transitions/contact and video; nominal numerical pass alone is not action acceptance')

if __name__=='__main__':main()
