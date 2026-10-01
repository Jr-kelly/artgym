"""Replay recorded actions from known reset commands; never correct memory from targets."""
import json
from pathlib import Path
import isaacgym
import numpy as np
import torch
from scripts.wuji_known_controller import KnownWujiController
from scripts.wuji_kinematics import WujiKinematics

def main():
 torch.set_num_threads(2);root=Path('runs/unified-student-20261001');hand=WujiKinematics();lower=torch.tensor(hand.lower,dtype=torch.float32);upper=torch.tensor(hand.upper,dtype=torch.float32);results=[]
 for name in ['teacher-official-S2','teacher-official-S5','S0-800-development/S0-800-S2','S0-800-development/S0-800-S5']:
  report=json.loads((root/name/'report.json').read_text());states=np.load('research/unified-student-20261001/data/development-all.npy')[report['initial_state_rows']]
  z=np.load(root/name/'trace.npz');t={k:z[k] for k in z.files};z.close();controller=KnownWujiController(lower,upper,len(states));controller.reset(torch.arange(len(states)),torch.tensor(states[:,20:40]));maximum=0.
  for k in range(len(t['action'])):
   predicted=controller.step(torch.tensor(t['action'][k])).numpy();mask=t['active'][k]
   if mask.any():maximum=max(maximum,float(abs(predicted[mask]-t['target'][k][mask]).max()))
  results.append(dict(run=name,steps=len(t['action']),cpu_replay_max_target_difference_rad=maximum,target_feedback=False,initialization='declared reset commands from state20:40',scope='CPU replay of actual GPU actions; separate same-device live audit still required'))
 p=Path('research/unified-student-20261001/known-controller-cpu-replay.json');p.write_text(json.dumps(results,indent=2));print(json.dumps(results))
if __name__=='__main__':main()
