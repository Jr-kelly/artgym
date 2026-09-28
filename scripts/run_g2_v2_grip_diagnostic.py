"""One independent local3cm grip reset baseline (counted execution)."""
import argparse,json
from pathlib import Path
from scripts.g2_v2_grip_env import GripV2
import numpy as np
import torch
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--prefix',action='store_true');p.add_argument('--checkpoint',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 if a.prefix:
  from scripts.g2_v2_prefix_grip_env import PrefixGripV2
  env=PrefixGripV2(num_envs=1)
 else:env=GripV2(num_envs=1)
 rows=[];model=None
 if a.checkpoint:
  from scripts.train_g2_local import ActorCritic
  saved=torch.load(a.checkpoint,map_location='cpu');assert saved['task_variant'] in ['v2-grip','v2-prefix-grip'];model=ActorCritic(saved['obs_dim'],saved['action_dim']);model.load_state_dict(saved['model']);model.eval()
 try:
  if a.prefix:np.savez_compressed(a.output/'prefix-trace.npz',**{k:np.array([r[k] for r in env.prefix_trace]) for k in env.prefix_trace[0]})
  for i in range(env.steps):
   with torch.no_grad():action=torch.zeros(1,20) if model is None else model.mean_action(env.observation())
   env.step(action,baseline='fixed' if model is None else 'learned');frame=env.frame();frame.update(env.contacts_for_evaluation());rows.append(frame)
  np.savez_compressed(a.output/'trace.npz',**{k:np.array([r[k] for r in rows]) for k in rows[0]});m={k:v.tolist() for k,v in env.metrics().items()};(a.output/'metrics.json').write_text(json.dumps(m,indent=2));print(json.dumps(m))
 finally:env.gym.destroy_sim(env.sim)
if __name__=='__main__':main()
