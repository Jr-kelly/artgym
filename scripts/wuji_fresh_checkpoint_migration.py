"""Explicit v3 158D to v6 168D migration; new feature weights/moments zero.

This preserves the original actor/critic functions and Adam state. It changes
the declared observation contract rather than relabeling incompatible weights.
"""
import argparse, copy, hashlib, json
from pathlib import Path
import isaacgym
import torch
from scripts.train_wuji_fresh_regrasp import FreshRegraspActor
from scripts.record_wuji_flat_table_event import record

def expand_tensor(tensor):
 out=tensor.new_zeros((192,168));out[:,:158]=tensor;return out

def migrate(saved):
 assert saved['format']=='wuji-regrasp-fresh-ppo-v3'
 assert 'optimizer' in saved,'Resume migration requires actual training optimizer'
 result=copy.deepcopy(saved)
 for name in ['actor.0.weight','critic.0.weight']:
  assert result['model'][name].shape==(192,158)
  result['model'][name]=expand_tensor(result['model'][name])
 names=[name for name,_ in FreshRegraspActor().named_parameters()]
 ids=[i for group in result['optimizer']['param_groups'] for i in group['params']]
 assert len(names)==len(ids)
 for name,index in zip(names,ids):
  if name in ['actor.0.weight','critic.0.weight']:
   for key,value in result['optimizer']['state'][index].items():
    if torch.is_tensor(value) and value.ndim==2:
     assert value.shape==(192,158)
     result['optimizer']['state'][index][key]=expand_tensor(value)
 result['format']='wuji-regrasp-fresh-ppo-v6'
 result['config'].update(task_geometry=True,observation_dim=168,reward_version='functional-workspace-geometry-closedslider-v6')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 original=torch.load(a.source,map_location='cpu');result=migrate(original)
 torch.manual_seed(812);torch.set_num_threads(1)
 before=FreshRegraspActor().eval();before.load_state_dict(original['model'])
 after=FreshRegraspActor(168).eval();after.load_state_dict(result['model'])
 x=torch.randn(512,158);features=torch.randn(512,10)*100
 checks={}
 for device in ['cpu','cuda']:
  before=before.to(device);after=after.to(device)
  with torch.no_grad():
   old_distribution,old_value=before(x.to(device));new_distribution,new_value=after(torch.cat([x,features],-1).to(device))
  checks[device]=dict(actor_max_abs_error=float((old_distribution.mean-new_distribution.mean).abs().max()),critic_max_abs_error=float((old_value-new_value).abs().max()),std_exactly_equal=bool(torch.equal(old_distribution.scale,new_distribution.scale)))
  assert checks[device]['actor_max_abs_error']<2e-6 and checks[device]['critic_max_abs_error']<2e-6 and checks[device]['std_exactly_equal']
 optimizer=torch.optim.Adam(after.parameters(),lr=3e-4);optimizer.load_state_dict(result['optimizer'])
 for parameter,state in optimizer.state.items():
  for key in ['exp_avg','exp_avg_sq']:
   assert state[key].shape==parameter.shape
 result['migration']=dict(parent_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),parent_format=original['format'],checks=checks,new_weights_and_Adam_moments='Exactly zero for all10 added columns',unchanged='All other parameters, optimizer state, all27 control dimensions, bounds, timing and original B')
 torch.save(result,a.output/'checkpoint.pth')
 audit=dict(result['migration'],checkpoint_sha256=hashlib.sha256((a.output/'checkpoint.pth').read_bytes()).hexdigest(),scope=__doc__)
 (a.output/'audit.json').write_text(json.dumps(audit,indent=2))
 record('fresh_task_geometry_checkpoint_migration_verified',[str(a.output/'audit.json'),str(a.output/'checkpoint.pth')],audit,next_step='Continue fresh actualphysics task geometry learning and sameepisode fullB; unchanged initial actions are not task success')
 print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
