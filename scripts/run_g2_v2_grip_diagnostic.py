"""One independent local3cm grip reset baseline (counted execution)."""
import argparse,json
from pathlib import Path
from scripts.g2_v2_grip_env import GripV2
import numpy as np
import torch
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);env=GripV2(num_envs=1);rows=[]
 try:
  for i in range(env.steps):env.step(torch.zeros(1,20),baseline='fixed');rows.append(env.frame())
  np.savez_compressed(a.output/'trace.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]});m={k:v.tolist() for k,v in env.metrics().items()};(a.output/'metrics.json').write_text(json.dumps(m,indent=2));print(json.dumps(m))
 finally:env.gym.destroy_sim(env.sim)
if __name__=='__main__':main()
