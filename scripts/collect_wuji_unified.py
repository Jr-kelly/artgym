"""Unchanged fixed-time evaluator plus aligned recurrent imitation evidence.

Each sequence row pairs the pre-action observation and previous executed action
with the expert mean, clipped executed action and physical post-action sample.
The original scorer and reset loop are reused without modification.
"""
import sys,json,hashlib
from pathlib import Path
from scripts import audit_wuji_multigrasp as audit
import numpy as np
import torch

def main():
 original_make=audit.make_player;rows=[];metadata={}
 def make(cfg,checkpoint):
  env,player=original_make(cfg,checkpoint)
  metadata.update(policy_obs_dim=player.model.a2c_network.policy_obs_dim,privileged_obs_dim=player.model.a2c_network.privileged_obs_dim,model=str(player.model),checkpoint_sha256=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),action_mode='deterministic mean clipped[-1,1]',sapg_embedding=50.0)
  def capture(module,args,out):
   rows[-1]['mu']=out['mus'].detach().cpu().numpy().copy()
  player.model.register_forward_hook(capture)
  get=player.get_action;step=player.env_step
  def action(obs,*args,**kw):
   row=dict(obs=obs.detach().cpu().numpy().copy(),previous_action=env.actions.detach().cpu().numpy().copy(),previous_target=env.prev_targets[:,:20].detach().cpu().numpy().copy(),initial_target=env.init_targets[:,:20].detach().cpu().numpy().copy(),active_before=env.eval_active_mask.detach().cpu().numpy().copy())
   rows.append(row);a=get(obs,*args,**kw)
   raw=env.init_targets[:,:20]+a*.04
   raw[:,16:]=env.prev_targets[:,16:20]+a[:,16:]*.025
   row.update(executed_action=a.detach().cpu().numpy().copy(),target_unclipped=raw.detach().cpu().numpy().copy(),target_clipped=env.actions_to_targets(a).detach().cpu().numpy().copy())
   return a
  def env_step(*args,**kw):
   result=step(*args,**kw);rows[-1]['done']=result[2].detach().cpu().numpy().copy();return result
  player.get_action=action;player.env_step=env_step
  metadata.update(joint_lower=env.hand_dof_lower_limits.detach().cpu().tolist(),joint_upper=env.hand_dof_upper_limits.detach().cpu().tolist())
  return env,player
 audit.make_player=make
 audit.main()
 out=Path(sys.argv[sys.argv.index('--output')+1])
 np.savez_compressed(out/'sequences.npz',**{key:np.stack([row[key] for row in rows]) for key in rows[0]})
 metadata.update(steps=len(rows),num_envs=rows[0]['obs'].shape[0],sequence_sha256=hashlib.sha256((out/'sequences.npz').read_bytes()).hexdigest(),collector_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (out/'interface.json').write_text(json.dumps(metadata,indent=2)+'\n')
if __name__=='__main__':main()
