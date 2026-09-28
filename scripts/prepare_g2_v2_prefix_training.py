"""Motor prefix from continuous v2 acquisition; no cached hand/object closure."""
import json,hashlib,shutil,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'runs/g2-functional-v2-20260928/V2-09-B-short-lift-yaw45');p.add_argument('--output',type=Path,default=ROOT/'configs/g2_functional_v2/grip-prefix-v2');a=p.parse_args();source=a.source;out=a.output;out.mkdir(exist_ok=False)
 d=np.load(source/'partial-trace.npz');first=int(np.flatnonzero(d['phase']=='lift')[0]);assert first==270
 keys=['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state','wrist','reference_targets','targets','arm_integral_state','slider','q']
 np.savez_compressed(out/'H-actual-state.npz',**{k:d[k][0].copy() for k in keys})
 np.savez_compressed(out/'prefix-trajectory.npz',reference_targets=d['reference_targets'][1:first].copy())
 np.savez_compressed(out/'arm-trajectory.npz',reference_targets=d['reference_targets'][first:first+150,:7].copy())
 physics=json.loads((source/'physics.json').read_text());physics['table_top']=.75;physics['knife_relative_urdf']='assets/objects/knife_wuji_measured_box_20260928_v2/000/mobility.urdf';(out/'physics.json').write_text(json.dumps(physics,indent=2)+'\n');shutil.copy2(source/'frozen-config.yaml',out/'frozen-config.yaml')
 (out/'provenance.json').write_text(json.dumps(dict(source=str(source),sha256=hashlib.sha256((source/'partial-trace.npz').read_bytes()).hexdigest(),initial_frame=0,initial_condition='Flat normal table knife, open hand above it; first recorded30Hz step after scene initialization. No grasp contact.',prefix_frames=[1,269],learned_frames=[270,419],reset_scope='Training episodes only. No state writes after each episode initialization; full physical motor approach and close.',change_from_G1='Same robot/knife/physics/3mm close/lift/reward/observation/motor bounds; initialize unloaded then physically execute prefix. Synchronous finite-horizon lift episodes.'),indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
