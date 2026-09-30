"""Whole-episode recurrent action BC, fixed inherited normalization, no latent matching."""
import argparse,copy,hashlib,json,time,os
from pathlib import Path
from scripts.wuji_goal_common import configuration
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from omegaconf import OmegaConf
import numpy as np
import torch

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--init',type=Path,required=True);p.add_argument('--data',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--label',choices=['mu','executed'],default='mu');p.add_argument('--resume',action='store_true');p.add_argument('--limit',type=int,default=0);p.add_argument('--epochs',type=int,default=100);p.add_argument('--save-every',type=int,default=25);p.add_argument('--seed',type=int,default=2026093001);p.add_argument('--lr',type=float,default=1e-4);p.add_argument('--perturb',type=float,default=0);p.add_argument('--batch',type=int,default=96);p.add_argument('--segment',type=int,default=100);p.add_argument('--max-seconds',type=int,default=3600);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False);torch.manual_seed(a.seed);np.random.seed(a.seed);started=time.monotonic()
 cfg=configuration('wuji_multigrasp',1,['object=knife_wuji_bridge3_20260922','hand=wuji_paper_official_actuator'],train='wujiAcquisitionSAPG',seed=a.seed)
 player=build_policy_player(cfg,preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),a.init,_infer_expl_num_blocks(a.init),0);model=player.model;model.eval()
 # Actor and its own encoder learn together; critic and observation statistics remain fixed.
 for name,param in model.named_parameters():
  param.requires_grad_(any('a2c_network.'+part in name for part in ['priv_encoder.','a_rnn.','a_layer_norm.','actor_mlp.','mu.']))
 params=[x for x in model.parameters() if x.requires_grad]
 with torch.no_grad():
  for param in params:
   if a.perturb:param.add_(torch.randn_like(param)*param.std().clamp_min(1e-3)*a.perturb)
 opt=torch.optim.Adam(params,lr=a.lr)
 data=[];man=[]
 for directory in a.data:
  with np.load(directory/'sequences.npz') as z:d={k:torch.as_tensor(z[k],device=player.device) for k in z.files}
  if a.limit:d={k:v[:,:a.limit] for k,v in d.items()}
  info=json.loads((directory/'interface.json').read_text());report=json.loads((directory/'report.json').read_text())
  assert d['obs'].shape[0]==600 and d['obs'].shape[1]>=4
  d['lower']=torch.tensor(info['joint_lower'],device=player.device);d['upper']=torch.tensor(info['joint_upper'],device=player.device)
  d['period']=report['protocol']['stage_steps']
  with np.load(directory/'trace.npz') as trace:
   reached=np.abs(trace['slider']-trace['goal'])<.002
   if a.limit:reached=reached[:,:a.limit]
  phase=np.zeros(reached.shape,dtype=np.int64);streak=np.zeros(reached.shape[1],dtype=np.int64)
  for step in range(600):
   if step%d['period']==0:streak[:]=0
   streak=np.where(reached[step],streak+1,0)
   phase[step]=np.where(streak==0,0,np.where(streak<=9,1,2))+(step//d['period']%2)*3
  weights=np.zeros(phase.shape,dtype=np.float32)
  for ep in range(phase.shape[1]):
   active=d['active_before'][:,ep].cpu().numpy().astype(bool)
   for category in range(6):
    mask=(phase[:,ep]==category)&active
    if mask.any():weights[mask,ep]=1./mask.sum()
   weights[:,ep]*=max(1,active.sum())/max(1e-9,weights[:,ep].sum())
  d['phase_weight']=torch.tensor(weights,device=player.device)
  d['phase']=torch.tensor(phase,device=player.device)
  data.append(d);man.append(dict(path=str(directory),sha256=sha(directory/'sequences.npz'),expert=info['checkpoint_sha256']))
 manifest=dict(args={k:str(v) if isinstance(v,Path) else [str(x) for x in v] if k=='data' else v for k,v in vars(a).items()},data=man,init_sha256=sha(a.init),normalization='Inherited from initialization checkpoint, frozen for entire run; experts retain own statistics',sequence='Complete600-step episodes; segments carry detached states; optimizer step only after full episode; reset mask shifted from previous transition',training_interactions=0)
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 base=torch.load(a.init,map_location='cpu');base=base[0] if 0 in base else base
 updates=0
 def save(epoch):
  state=copy.deepcopy(base);state['model']={k:v.detach().cpu() for k,v in model.state_dict().items()};state['running_mean_std']=model.running_mean_std.state_dict();state['bc_optimizer']=opt.state_dict();state['bc_epoch']=epoch;state['bc_updates']=updates;state['bc_manifest']=manifest
  # Existing PPO optimizer belongs to source expert and is explicitly not BC continuation.
  state.pop('optimizer',None);state['training_kind']='offline_sequence_BC_not_resumed_PPO'
  state['bc_torch_rng']=torch.get_rng_state();state['bc_cuda_rng']=torch.cuda.get_rng_state_all();state['bc_numpy_rng']=np.random.get_state()
  target=a.output/f'epoch_{epoch:06d}.pth';temporary=target.with_suffix('.pth.tmp');torch.save(state,temporary);os.replace(temporary,target)
 def pass_data(d,ids,train):
  model.train(train);model.running_mean_std.eval();model.value_mean_std.eval()
  n=len(ids);states=[torch.zeros((x.shape[0],n,x.shape[2]),device=player.device) for x in model.get_default_rnn_state()]
  errors=[];target_errors=[];raw_errors=[];executed_errors=[];phase_metrics=[];loss_sum=0.
  if train:opt.zero_grad(set_to_none=True)
  for start in range(0,600,a.segment):
   end=min(start+a.segment,600);length=end-start
   def flat(key):return d[key][start:end,ids].transpose(0,1).reshape(n*length,-1)
   obs=flat('obs');reset=torch.zeros((600,n),device=player.device,dtype=torch.bool);reset[1:]=d['done'][:-1,ids].bool()
   inp=dict(obs=model.norm_obs(obs),rnn_states=states,seq_length=length,dones=reset[start:end].transpose(0,1).reshape(-1,1).float(),bptt_len=0)
   mu,_,_,states=model.a2c_network(inp);states=[s.detach() for s in states]
   pred=mu.clamp(-1,1);raw=flat('initial_target')+pred*.04;raw[:,16:]=flat('previous_target')[:,16:]+pred[:,16:]*.025
   targets=torch.maximum(torch.minimum(raw,d['upper']),d['lower']);terr=(targets-flat('target_clipped'))/(d['upper']-d['lower'])
   mask=flat('active_before').float().squeeze(-1)
   # Balance open/close x moving/first9-at-target/holding within each trajectory.
   weight=flat('phase_weight').squeeze(-1)
   label=flat('mu') if a.label=='mu' else flat('executed_action')
   err=(mu-label).square().mean(-1);loss=(err*mask*weight).sum()/d['phase_weight'][:,ids].sum().clamp_min(1)
   if train:loss.backward()
   loss_sum+=float(loss.detach())
   errors.append(err.detach()[mask.bool()]);target_errors.append(terr.detach().abs()[mask.bool()])
   raw_errors.append((mu-flat('mu')).detach().square()[mask.bool()]);executed_errors.append((pred-flat('executed_action')).detach().square()[mask.bool()])
   phase_values=d['phase'][start:end,ids].transpose(0,1).reshape(-1)
   for category in ([] if train else range(6)):
    m=mask.bool() & (phase_values==category)
    if m.any():phase_metrics.append(dict(phase=category,n=int(m.sum()),raw_mse=float((mu-flat('mu'))[m].square().mean()),executed_mse=float((pred-flat('executed_action'))[m].square().mean()),thumb_target_rad=float((targets-flat('target_clipped'))[m,16:].abs().mean()),support_target_rad=float((targets-flat('target_clipped'))[m,:16].abs().mean())))
  if train:torch.nn.utils.clip_grad_norm_(params,1.);opt.step()
  te=torch.cat(target_errors);er=torch.cat(errors)
  return dict(raw_mu_mse=float(torch.cat(raw_errors).mean()),executed_action_mse=float(torch.cat(executed_errors).mean()),phase_metrics=phase_metrics,loss=loss_sum,action_mse=float(er.mean()),target_range_mean=float(te.mean()),target_range_p95=float(torch.quantile(te.flatten(),.95)),thumb_mean=float(te[:,16:].mean()),support_mean=float(te[:,:16].mean()))
 def validate(epoch):
  with torch.no_grad():
   metrics=[pass_data(d,torch.arange(int(d['obs'].shape[1]*.75),d['obs'].shape[1],device=player.device),False) for d in data]
   train_metrics=[pass_data(d,torch.arange(min(8,int(d['obs'].shape[1]*.75)),device=player.device),False) for d in data]
  row=dict(epoch=epoch,updates=updates,wall_seconds=time.monotonic()-started,validation=metrics,training_probe=train_metrics)
  with (a.output/'metrics.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(row),flush=True)
 start_epoch=0
 if a.resume:
  assert a.perturb==0 and 'bc_optimizer' in base and 'bc_torch_rng' in base
  opt.load_state_dict(base['bc_optimizer']);updates=base['bc_updates'];start_epoch=base['bc_epoch']
  torch.set_rng_state(base['bc_torch_rng']);torch.cuda.set_rng_state_all(base['bc_cuda_rng']);np.random.set_state(base['bc_numpy_rng'])
  assert a.epochs>start_epoch
  manifest['restored_adam_lr']=[g['lr'] for g in opt.param_groups]
  manifest['resume_updates']=updates
  (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 save(start_epoch);validate(start_epoch)
 for epoch in range(start_epoch+1,a.epochs+1):
  for j in np.random.permutation(len(data)):
   d=data[j];count=int(d['obs'].shape[1]*.75);ids=torch.randperm(count,device=player.device)
   for offset in range(0,count,a.batch):pass_data(d,ids[offset:offset+a.batch],True);updates+=1
  if epoch%a.save_every==0 or epoch==a.epochs:save(epoch);validate(epoch)
  if time.monotonic()-started>a.max_seconds:save(epoch);validate(epoch);break
 (a.output/'completed.json').write_text(json.dumps(dict(epoch=epoch,updates=updates,wall_seconds=time.monotonic()-started,simulation_interactions=0))+'\n')
if __name__=='__main__':main()
