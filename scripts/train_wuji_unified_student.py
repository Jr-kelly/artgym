"""Frozen-teacher on-policy latent distillation with explicit optimizer-step accounting."""
import argparse,copy,datetime,hashlib,json,random,time
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_player
import numpy as np
import torch
from torch.nn import functional as F
from omegaconf import OmegaConf
from scripts.wuji_student_interface import build_encoder,install_legal_public,install_student_player,legal_policy_observation,tensor_hash,SPEC
from isaacgymenvs.distill import normalize_obs_slice,reset_done_rnn_states
from isaacgymenvs.utils.distill_rollout_utils import distillation_action
from isaacgymenvs.utils.distill_action_loss import frozen_actor_mean


def rng():return dict(torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all(),numpy=np.random.get_state(),python=random.getstate())
def restore_rng(r):
 torch.set_rng_state(r['torch']);torch.cuda.set_rng_state_all(r['cuda']);np.random.set_state(r['numpy']);random.setstate(r['python'])
def atomic_save(payload,p):
 tmp=p.with_suffix('.tmp');torch.save(payload,tmp);tmp.replace(p)
 p.with_suffix('.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n')

def interface_check(player,env,obs,encoder):
 net=player.model.a2c_network
 assert torch.equal(env.proprioception_buf,env.proprioception_buf[:,-1:,:].expand_as(env.proprioception_buf)), 'Reset history must repeat current q and zero action'
 net.actor_encoder_obs_override=env.student_obs_buf.clone()
 incoming=[s.clone() for s in player.states];rs=rng()
 with torch.no_grad():
  a=player.get_action(obs,is_deterministic=True);states=[s.clone() for s in player.states]
  player.states=[s.clone() for s in incoming]
  changed=obs.clone();changed[:,111:137]=torch.linspace(-100,100,26,device=obs.device)
  b=player.get_action(changed,is_deterministic=True)
 assert torch.equal(a,b)
 assert all(torch.equal(x,y) for x,y in zip(states,player.states))
 player.states=incoming;restore_rng(rs);net.actor_encoder_obs_override=None
 return dict(privileged_perturbation_action_max=float((a-b).abs().max()),all_rnn_states_unchanged=True,raw_obs_dim=obs.shape[1],student_obs_dim=env.student_obs_buf.shape[1],teacher_obs_dim=env.teacher_privileged_obs_buf.shape[1],rnn_shapes=[list(x.shape) for x in incoming])

def main():
 p=argparse.ArgumentParser();p.add_argument('--teacher',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--kind',choices=['C0','C1','S0','SC'],required=True);p.add_argument('--updates',type=int,default=3200);p.add_argument('--envs',type=int,default=256);p.add_argument('--rollout-steps',type=int,default=4);p.add_argument('--seed',type=int,default=61001);p.add_argument('--resume',type=Path);p.add_argument('--warm-updates',type=int,default=400);p.add_argument('--save-at',type=int,nargs='+',default=[16,400,800,1600,3200,6400,12800]);p.add_argument('--lr',type=float,default=.0003);p.add_argument('--controller-mode',choices=['real','masked'],default='real')
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 assert a.envs%4==0
 overrides=['object=knife_wuji_bridge3_20260922','hand=wuji_paper_official_actuator','task.env.trainingStates=research/unified-student-20261001/data/training-all.npy','task.env.episodeLength=600','task.env.proprioHistoryLen=50','task.env.studentInitObsDim=55','+task.env.enableStudentEncoderObs=True']
 cfg=configuration('wuji_multigrasp',a.envs,overrides,train='wujiAcquisitionSAPG',seed=a.seed)
 (a.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
 env,player=make_player(cfg,a.teacher);net=player.model.a2c_network
 for param in player.model.parameters():param.requires_grad_(False)
 player.model.eval();teacher=copy.deepcopy(net.priv_encoder).eval()
 frozen=lambda:{k:v for k,v in player.model.state_dict().items() if not k.startswith('a2c_network.priv_encoder.')}
 frozen_hash=tensor_hash(frozen());teacher_hash=tensor_hash(teacher.state_dict())
 install_legal_public(env);install_student_player(player)
 # Each slot stays in one source stratum; no source information enters policy inputs.
 nsource=len(env.all_valid_states)//4;source=torch.arange(a.envs,device=env.device)%4
 sample_counts=torch.zeros(4,device=env.device,dtype=torch.long)
 def sample(ids):
  group=source[ids];sample_counts.add_(torch.bincount(group,minlength=4))
  rows=group*nsource+torch.randint(nsource,(len(ids),),device=env.device)
  return env.all_valid_states[rows]
 env.sample_grasps=sample
 if a.kind=='SC':
  from scripts.wuji_known_controller import install_known_controller
  install_known_controller(env,a.controller_mode)
 torch.manual_seed(a.seed);torch.cuda.manual_seed_all(a.seed);np.random.seed(a.seed);random.seed(a.seed)
 encoder=build_encoder(a.kind).to(player.device);encoder.eval();net.priv_encoder=encoder
 optimizer=None if a.kind=='C0' else torch.optim.Adam(encoder.parameters(),lr=a.lr)
 start_update=0;total_interactions=0;sum_latent=torch.zeros(16,device=player.device,dtype=torch.float64);label_count=0
 if a.resume:
  restored=torch.load(a.resume,map_location='cpu')
  expanding=a.kind=='SC' and restored['kind']=='S0'
  assert restored['kind']==a.kind or expanding
  state=copy.deepcopy(restored['student_encoder']);optstate=copy.deepcopy(restored['optimizer'])
  if expanding:
   key='init_encoder.0.weight';state[key]=F.pad(state[key],(0,21))
   index=[name for name,_ in encoder.named_parameters()].index(key)
   pid=optstate['param_groups'][0]['params'][index]
   for k in ['exp_avg','exp_avg_sq']:optstate['state'][pid][k]=F.pad(optstate['state'][pid][k],(0,21))
  encoder.load_state_dict(state);optimizer.load_state_dict(optstate)
  start_update=restored['optimizer_steps'];total_interactions=restored['interactions'];restore_rng(restored['rng'])
  assert restored['frozen_hash']==frozen_hash and restored['teacher_encoder_hash']==teacher_hash
  assert tensor_hash(encoder.state_dict())==tensor_hash(state)
  (a.output/'resume-audit.json').write_text(json.dumps(dict(parent=str(a.resume),parent_sha256=hashlib.sha256(a.resume.read_bytes()).hexdigest(),restored_optimizer_steps=start_update,adam_steps=sorted(set(int(v['step']) for v in optimizer.state.values())),encoder_hash=tensor_hash(encoder.state_dict()),frozen_hash=frozen_hash,rng_restored=True,controller_columns_expanded=expanding,physics='new episode reset after RNG restore'),indent=2))
 # Resume starts a declared new physics episode. Optimizer/RNG are preserved; no claim of PhysX bitwise continuation.
 obs=player.env_reset(player.env)
 if a.resume and expanding:
  saved_rng=rng();old=build_encoder('S0').to(player.device);old.load_state_dict(restored['student_encoder']);old.eval()
  with torch.no_grad():
   x=env.student_obs_buf
   difference=float((encoder(x)-old(x[:,:2055])).abs().max())
  (a.output/'controller-upgrade-parity.json').write_text(json.dumps(dict(max_latent_difference=difference,tolerance=1e-5,extra_columns='zero weights and Adam moments',controller_mode=a.controller_mode),indent=2))
  assert difference<1e-5
  del old;restore_rng(saved_rng)
 check=interface_check(player,env,obs,encoder)
 check.update(input_schema=dict(history=2000,initial=55,known_controller=21 if a.kind=='SC' else 0),controller_mode=a.controller_mode if a.kind=='SC' else None,reset_history_consistent=True,frozen_hash=frozen_hash,teacher_encoder_hash=teacher_hash,spec={**SPEC,'init_dim':76 if a.kind=='SC' else 55},kind=a.kind,seed=a.seed,resume_episode_reset=bool(a.resume),source_sampling='fixed balanced slot strata, random training rows within source',warm_schedule='linear1to0 for first400 absolute optimizer updates; afterwards0',gradient_dropout=False)
 (a.output/'interface.json').write_text(json.dumps(check,indent=2))
 begin=time.monotonic();initial_hash=tensor_hash(encoder.state_dict());duration_counts={60:0,150:0};reset_count=0;max_target_error=0.
 teacher_sha=hashlib.sha256(a.teacher.read_bytes()).hexdigest()
 def save(u):
  assert tensor_hash(frozen())==frozen_hash and tensor_hash(teacher.state_dict())==teacher_hash
  if optimizer:assert all(int(v['step'])==u for v in optimizer.state.values())
  payload=dict(format='wuji-unified-student-v1',kind=a.kind,controller_mode=a.controller_mode if a.kind=='SC' else None,spec={**SPEC,'init_dim':76 if a.kind=='SC' else 55},student_encoder=encoder.state_dict(),optimizer=None if optimizer is None else optimizer.state_dict(),optimizer_steps=u if optimizer else 0,collection_updates=u,interactions=total_interactions,rng=rng(),teacher_sha256=teacher_sha,frozen_hash=frozen_hash,teacher_encoder_hash=teacher_hash,args=vars(a),scope='initial calibration conditional; current q/actions, URDF FK and external command; no current object truth',resume_contract='Optimizer/RNG restored; simulator starts new episodes; no bitwise PhysX state restore')
  atomic_save(payload,a.output/('step_%06d.pth'%u))
 try:
  for u0 in range(start_update,a.updates):
   u=u0+1;losses=[];targets=[];raws=[];clipped=[];by_source=[]
   if optimizer:optimizer.zero_grad(set_to_none=True)
   for step in range(a.rollout_steps):
    x=env.student_obs_buf.detach().clone();priv=env.teacher_privileged_obs_buf.detach().clone()
    with torch.no_grad():label=teacher(normalize_obs_slice(player.model,priv,111))
    incoming=[s.clone() for s in player.states]
    fraction=1. if a.kind=='C0' else max(0.,1-u0/max(a.warm_updates,1)) if a.warm_updates else 0.
    with torch.no_grad():action=distillation_action(player,obs,x,teacher,False,True,True,fraction,label if fraction else None)
    if a.kind=='C0':
     sum_latent+=label.double().sum(0);label_count+=len(label);encoder.latent.copy_((sum_latent/label_count).float())
     pred=encoder(x)
    else:
     pred=encoder(x);loss=F.mse_loss(pred,label);(loss/a.rollout_steps).backward()
    losses.append(float(F.mse_loss(pred,label)));by_source.append([float(((pred-label)**2).mean(1)[source==s].mean()) for s in range(4)])
    if u%25==0 or u<=2:
     with torch.no_grad():
      mus=frozen_actor_mean(player,legal_policy_observation(obs),pred.detach(),incoming)
      mut=frozen_actor_mean(player,legal_policy_observation(obs),label,incoming)
      raws.append(float(F.mse_loss(mus,mut)));clipped.append(float(F.mse_loss(mus.clamp(-1,1),mut.clamp(-1,1))))
      targets.append(float(F.mse_loss(env.actions_to_targets(mus.clamp(-1,1)),env.actions_to_targets(mut.clamp(-1,1)))))
    predicted_target=env.actions_to_targets(action).clone()
    duration=env.command_deadline-env.progress_buf
    for d in duration_counts:duration_counts[d]+=int((duration==d).sum())
    obs,_,done,_=player.env_step(player.env,action);total_interactions+=a.envs
    # Exclude freshly reset slots whose targets intentionally changed.
    alive=~done.bool()
    if alive.any():max_target_error=max(max_target_error,float((env.cur_targets[alive,:20]-predicted_target[alive]).abs().max()))
    reset_done_rnn_states(player,done);reset_count+=int(done.sum())
    assert all(not z.requires_grad for z in player.states)
   grad=0.
   if optimizer:
    grad=float(torch.nn.utils.clip_grad_norm_(encoder.parameters(),1.));assert np.isfinite(grad);optimizer.step()
   if u==16:
    assert a.kind=='C0' or tensor_hash(encoder.state_dict())!=initial_hash
    assert max_target_error<1e-5
   row=dict(update=u,optimizer_steps=u if optimizer else 0,interactions=total_interactions,wall_seconds=time.monotonic()-begin,latent_mse=float(np.mean(losses)),source_mse=np.mean(by_source,axis=0).tolist(),raw_mean_mse=float(np.mean(raws)) if raws else None,clipped_action_mse=float(np.mean(clipped)) if clipped else None,target_mse_rad2=float(np.mean(targets)) if targets else None,grad_norm=grad,teacher_fraction=fraction,resets=reset_count,source_reset_counts=sample_counts.tolist(),duration_counts=duration_counts,fk_max_error_m=env.student_fk_max_error,target_mapping_max_error_rad=max_target_error,known_controller_max_error_rad=getattr(env,'known_controller_max_error',None))
   with (a.output/'learning.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
   if u%25==0 or u<=2:print(json.dumps(row),flush=True)
   if u in a.save_at or u==a.updates:save(u)
  (a.output/'complete.json').write_text(json.dumps(row,indent=2))
 finally:env.gym.destroy_sim(env.sim)
if __name__=='__main__':main()
