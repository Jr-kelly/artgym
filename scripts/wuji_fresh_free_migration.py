"""Explicit v6 to free27 v7 warm start; motor action meanings preserved.

The forced postprefix reference is intentionally removed, phase action is
removed. The selected prefix is the original verified fresh pickup; a longer
carrying prefix was evaluated and rejected because it kept rotating rapidly.
This preserves first27 actor outputs, critic and their Adam moments; it does
not claim unchanged physical trajectories under the new reference contract.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import isaacgym
import torch
from scripts.train_wuji_fresh_regrasp import FreshRegraspActor
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
 old=torch.load(a.source,map_location='cpu');assert old['format']=='wuji-regrasp-fresh-ppo-v6' and 'optimizer' in old;s=copy.deepcopy(old)
 changed=['logstd','actor.4.weight','actor.4.bias']
 for name in changed:s['model'][name]=s['model'][name][:27].clone()
 names=[name for name,_ in FreshRegraspActor(168).named_parameters()];ids=[i for group in s['optimizer']['param_groups'] for i in group['params']]
 for name,index in zip(names,ids):
  if name in changed:
   for key,value in s['optimizer']['state'][index].items():
    if torch.is_tensor(value) and value.ndim and value.shape[0]==28:s['optimizer']['state'][index][key]=value[:27].clone()
 root=Path('runs/flat-table-20261006/direct/preparation/fresh-safe-prefix-free-reference-v823');s['config'].update(free_motor=True,action_dim=27,motor_action_mode='free-motor-v7',phase_semantics='free-motor-hold-v7',reference=str(root/'reference.json'),prefix_trace=str(root/'fresh-prefix-motor-trace.npz'),motor_preamble=str(root/'postA-safe-preamble.npy'),reference_sha256=hashlib.sha256((root/'reference.json').read_bytes()).hexdigest(),prefix_sha256=hashlib.sha256((root/'fresh-prefix-motor-trace.npz').read_bytes()).hexdigest(),reward_version='free-workspace-closedslider-allhand-v7');s['format']='wuji-regrasp-fresh-free-v7';s['motor_span'][:7]=[.6]*7
 before=FreshRegraspActor(168).eval();before.load_state_dict(old['model']);after=FreshRegraspActor(168,27).eval();after.load_state_dict(s['model']);torch.manual_seed(823);x=torch.randn(512,168);checks={}
 for device in ['cpu','cuda']:
  before=before.to(device);after=after.to(device)
  with torch.no_grad():od,ov=before(x.to(device));nd,nv=after(x.to(device))
  checks[device]=dict(first27_actor_max_abs_error=float(abs(od.mean[:,:27]-nd.mean).max()),critic_max_abs_error=float(abs(ov-nv).max()),first27_std_exactly_equal=bool(torch.equal(od.scale[:,:27],nd.scale)))
  assert checks[device]['first27_actor_max_abs_error']<2e-6 and checks[device]['critic_max_abs_error']<2e-6 and checks[device]['first27_std_exactly_equal']
 optimizer=torch.optim.Adam(after.parameters(),lr=3e-4);optimizer.load_state_dict(s['optimizer'])
 for parameter,state in optimizer.state.items():
  assert state['exp_avg'].shape==parameter.shape and state['exp_avg_sq'].shape==parameter.shape
 audit=dict(parent_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),checks=checks,changed='27 freejoint increments around currentissued motor anchor, no forceddenseguide, no phase action, armoffset span.6rad; originaljoint/effort/PD/physics/B unchanged',scope=__doc__);s['migration']=audit;torch.save(s,a.output/'checkpoint.pth');audit['checkpoint_sha256']=hashlib.sha256((a.output/'checkpoint.pth').read_bytes()).hexdigest();(a.output/'audit.json').write_text(json.dumps(audit,indent=2));record('fresh_free27_control_warmstart_migration_verified',[str(a.output/'audit.json'),str(a.output/'checkpoint.pth')],audit,next_step='Fresh actual800motorprefix -> free27 physicallearning -> entireoriginalB sameepisode; independentlyverify native continuation');print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
