"""Check actual training reset pool, noise, action mapping, and finite PPO inputs."""
import argparse,hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
from isaacgymenvs.tasks.artmanip import ArtManip
import numpy as np
import torch
from omegaconf import OmegaConf
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--pool',choices=['small','more'],required=True);p.add_argument('--span',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 source=R/'research/multigrasp-20260928/data'/(a.pool+'.npy');states=np.load(source);counts=[0]*len(states);base=ArtManip.sample_grasps
 def sample(self,ids):
  value=base(self,ids);match=(value[:,None,:]==torch.as_tensor(states,device=value.device)[None,:,:]).all(-1)
  # Construction happens before the custom pool is installed. Audit only after it is installed.
  if hasattr(self,'training_states_sha256'):
   assert match.sum(-1).eq(1).all()
   for i in match.nonzero()[:,1].cpu().tolist():counts[i]+=1
  return value
 ArtManip.sample_grasps=sample
 cfg=configuration('wuji_multigrasp',160,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','test=False','task.env.trainingStates='+str(source),'task.env.supportActionSpan='+str(a.span)],train='wujiAcquisitionSAPG',seed=2026092804)
 (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True));env=make_env(cfg);calls=0;base_map=env.actions_to_targets
 def mapping(action):
  nonlocal calls
  expected=env.init_targets[:,:20]+action*a.span
  expected[:,16:]=env.prev_targets[:,16:20]+action[:,16:]*.025
  expected=torch.maximum(torch.minimum(expected,env.hand_dof_upper_limits),env.hand_dof_lower_limits)
  target=base_map(action);assert torch.equal(expected,target);calls+=1;return target
 env.actions_to_targets=mapping
 try:
  assert torch.equal(env.all_valid_states,torch.as_tensor(states,device=env.device))
  assert env.runtime_grasp_split=='train' and not env.eval_mode
  assert abs(env.dt*env.control_freq_inv-1/30)<1e-7
  for k in range(130):
   if k%30==0:env.reset()
   env.step((torch.rand((160,20),device=env.device)*2-1)*.1)
   assert torch.isfinite(env.obs_buf).all() and torch.isfinite(env.rew_buf).all()
  assert min(counts)>0 and calls==130
  (a.output/'report.json').write_text(json.dumps(dict(status='passed',training_states_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),pool=a.pool,span=a.span,sampled_rows=counts,action_mapping_calls=calls,transitions=20800,noise=OmegaConf.to_container(cfg.task.env.initialPoseNoise),scope='training reset and action interface gate, no policy success'),indent=2)+'\n')
 finally:env.gym.destroy_sim(env.sim);ArtManip.sample_grasps=base
if __name__=='__main__':main()
