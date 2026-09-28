"""Extract actual pre-lift state for local motor residual diagnostics/learning.
This is explicitly a local reset dataset, NEVER evidence of tabletop pickup.
"""
import hashlib,json,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
 source=ROOT/'runs/g2-functional-v2-20260928/V2-09-B-short-lift-yaw45';out=ROOT/'configs/g2_functional_v2/grip-local-v1';out.mkdir(exist_ok=False)
 d=np.load(source/'partial-trace.npz');first=int(np.flatnonzero(d['phase']=='lift')[0]);idx=first-1;assert idx==269
 keys=['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state','wrist','reference_targets','targets','arm_integral_state','slider','q']
 np.savez_compressed(out/'H-actual-state.npz',**{k:d[k][idx].copy() for k in keys})
 np.savez_compressed(out/'arm-trajectory.npz',reference_targets=d['reference_targets'][first:first+150,:7],expected_translation_m=np.c_[np.zeros(150),np.zeros(150),.03*(10*np.minimum(np.arange(1,151)/120,1)**3-15*np.minimum(np.arange(1,151)/120,1)**4+6*np.minimum(np.arange(1,151)/120,1)**5)])
 physics=json.loads((source/'physics.json').read_text());physics['table_top']=.75;physics['knife_relative_urdf']='assets/objects/knife_wuji_measured_box_20260928_v2/000/mobility.urdf';(out/'physics.json').write_text(json.dumps(physics,indent=2)+'\n');shutil.copy2(source/'frozen-config.yaml',out/'frozen-config.yaml')
 (out/'provenance.json').write_text(json.dumps(dict(source=str(source),trace_sha256=hashlib.sha256((source/'partial-trace.npz').read_bytes()).hexdigest(),frame=idx,scope='Independent local reset from actual closed tabletop state; inherited physical properties, actual q/qd/root velocities/servo integral. Contact solver cache unavailable: compare fixed baseline before learning.',goal='Robot hand residual to keep opposite-side grasp during predefined3cm arm lift and1s hold; no flip/operation learning'),indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
