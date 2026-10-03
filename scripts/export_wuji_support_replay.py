"""Export legal replay inputs from an actual native episode using named mapping.

Current object/contact/load state is not exported. Trace time ends the control
period, so issue clock is time - 1/30, not one physics step earlier.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--episode',type=Path,required=True);p.add_argument('--estimate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix-start-seconds',type=float,default=12.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 physics=json.loads((a.episode/'physics.json').read_text());names=physics['robot_dof_names'];hand=physics['hand_indices'];arm=physics['arm_indices'];hand_names=['hand_r_'+finger+'_joint'+str(i) for finger in ['index','middle','pinky','ring','thumb'] for i in range(1,5)];arm_names=['idx'+str(61+i)+'_arm_r_joint'+str(1+i) for i in range(7)]
 assert [names[i] for i in hand]==hand_names and [names[i] for i in arm]==arm_names
 with np.load(a.episode/'trace.npz') as z:
  clock=np.round((z['time']-1/30)*30)/30;mask=clock>=a.prefix_start_seconds-1e-7
  values=dict(clock_s=clock[mask],hand_measured_q=z['observed_q'][mask],arm_measured_q=z['arm_q'][mask],issued_hand_target=z['target'][mask][:,hand])
 assert len(values['clock_s'])>=50 and np.allclose(np.diff(values['clock_s']),1/30,atol=1e-7)
 np.savez_compressed(a.output/'legal-measurements.npz',**values);shutil.copy2(a.estimate,a.output/'estimate.json')
 receipt=dict(source_episode=str(a.episode),source_trace_sha256=hashlib.sha256((a.episode/'trace.npz').read_bytes()).hexdigest(),fields=list(values),frames=len(values['clock_s']),control_hz=30,hand_joint_names=hand_names,arm_joint_names=arm_names,arm_sampling='Existing trace arm_q is period-end measurement; hand observed_q is period-begin. Do not claim bitwise input equivalence while arm moves.',scope='Legal measured/issued commandlog export only; initial estimate externally supplied, no current object/contact/load arrays. No physics or hardware actions.')
 (a.output/'source.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
if __name__=='__main__':main()
