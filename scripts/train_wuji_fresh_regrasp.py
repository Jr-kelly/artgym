"""Whole wrist/hand incremental PPO from real fresh-table prefix physics."""
import argparse,json,time,signal,hashlib,shutil
from pathlib import Path
import isaacgym
import torch,numpy as np
from torch import nn
from torch.distributions import Normal
from scripts.wuji_fresh_prefix_learning import FreshPrefixRegrasp
from scripts.record_wuji_flat_table_event import record

class FreshRegraspActor(nn.Module):
 def __init__(self,observation_dim=158,action_dim=28):
  super().__init__();self.actor=nn.Sequential(nn.Linear(observation_dim,192),nn.Tanh(),nn.Linear(192,192),nn.Tanh(),nn.Linear(192,action_dim));self.critic=nn.Sequential(nn.Linear(observation_dim,192),nn.Tanh(),nn.Linear(192,192),nn.Tanh(),nn.Linear(192,1));self.logstd=nn.Parameter(torch.tensor([np.log(.12)]*27+([np.log(.52)] if action_dim==28 else []),dtype=torch.float32));nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)
 def forward(self,obs):return Normal(self.actor(obs),self.logstd.clamp(-3.5,-.1).exp()),self.critic(obs).squeeze(-1)

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--rounds',type=int,default=60);p.add_argument('--envs',type=int,default=32);p.add_argument('--resume',type=Path);p.add_argument('--deterministic-only',action='store_true');p.add_argument('--capacity-probe',action='store_true');p.add_argument('--capacity-entry-frames',type=int,default=3);p.add_argument('--functional-workspace',action='store_true');p.add_argument('--long-credit',action='store_true');p.add_argument('--task-geometry',action='store_true');p.add_argument('--free-motor',action='store_true');p.add_argument('--pose-motion',action='store_true');p.add_argument('--fail-on-self-contact',action='store_true');p.add_argument('--functional-contact-reward',action='store_true');p.add_argument('--prefix-motor-trace',type=Path);p.add_argument('--motor-preamble',type=Path);p.add_argument('--action-period-frames',type=int,default=2);a=p.parse_args();assert 1<=a.action_period_frames<=30 and 900%a.action_period_frames==0;assert a.free_motor or a.action_period_frames==2;assert not a.functional_contact_reward or a.fail_on_self_contact;assert not a.fail_on_self_contact or a.pose_motion;assert not a.pose_motion or a.free_motor;assert not a.prefix_motor_trace or a.pose_motion;assert not a.free_motor or a.task_geometry;assert not a.task_geometry or (a.functional_workspace and a.long_credit);a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(20261008801);stop=[False];signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True))
 root=Path('runs/flat-table-20261006/direct');envcfg=dict(source=str(root/'recorded/current-C560-no-extra-load-flip-v565-6p1'),reference=str(root/'preparation/fresh-physical-regrasp-guide-v801/reference.json'),prefix_trace=str(root/'development/current-C560-fresh-no-extra-ring-v743/simulation/trace.npz'),prefix_spec=str(root/'preparation/current-C560-fresh-no-extra-ring-v743/prefix.json'),n=a.envs,free_motor=a.free_motor,task_geometry=a.task_geometry,functional_workspace=a.functional_workspace,linear_potential=a.long_credit,failure_penalty=60. if a.long_credit else 12.,self_bad_penalty=2. if a.long_credit else .5)
 if a.free_motor:
  free_root=root/'preparation/fresh-safe-prefix-free-reference-v823';envcfg.update(reference=str(free_root/'reference.json'),prefix_trace=str(free_root/'fresh-prefix-motor-trace.npz'),workspace_query_distance_m=.010,workspace_cadence_frames=45)
 if a.pose_motion:envcfg['pose_motion_observation']=True
 if a.fail_on_self_contact:envcfg['fail_on_self_contact']=True
 if a.functional_contact_reward:envcfg['functional_contact_reward']=True
 if a.prefix_motor_trace:envcfg['prefix_trace']=str(a.prefix_motor_trace)
 observation_dim=168 if a.task_geometry else 158;action_dim=27 if a.free_motor else 28;checkpoint_format='wuji-regrasp-fresh-free-v10' if a.functional_contact_reward else 'wuji-regrasp-fresh-free-v9' if a.fail_on_self_contact else 'wuji-regrasp-fresh-free-v8' if a.pose_motion else 'wuji-regrasp-fresh-free-v7' if a.free_motor else 'wuji-regrasp-fresh-ppo-v6' if a.task_geometry else 'wuji-regrasp-fresh-ppo-v3'
 cfg=dict(envcfg,action_dim=action_dim,motor_preamble=str(free_root/'postA-safe-preamble.npy') if a.free_motor else None,observation_dim=observation_dim,allheld_geometry=a.task_geometry,geometry_cadence_frames=15,geometry_running_cost=.02 if a.task_geometry else 0.,observation_extras='foot-minus-soft-roof_xyz*100,taildistance*100,full30FKerror*100,selfbad,stage-sliderdelta*100,linearspeed*5,angularspeed,referenceeligible' if a.task_geometry else None,capacity_probe=a.capacity_probe,capacity_entry_frames=a.capacity_entry_frames,action='Free27 incremental arm/hand motor commands around actualissued bearing target; no forced postprefix motion' if a.free_motor else '27 incremental arm/hand motor commands + pausable reference; totalcommand slew clipped',phase_semantics='free-motor-hold-v7' if a.free_motor else 'pause-linear-v2',reward_version=('free-workspace-closedslider-allhand-v7' if a.free_motor else 'functional-workspace-geometry-closedslider-allhand-v6b' if a.task_geometry else 'functional-workspace-linear-credit-v5' if a.long_credit else 'functional-cap-workspace-v4' if a.functional_workspace else 'functional-cap-progress-v3'),frame_gamma=.999 if a.long_credit else .995,frame_lambda=.985 if a.long_credit else .95,motor_action_mode='free-motor-v7' if a.free_motor else 'incremental-v3',native_coordinate_adaptation='joint-anchor',action_period_frames=a.action_period_frames,episode_steps=900,scope='Sim_oracle state-conditioned transition learning from fresh table physics; functional cap/holding proxies, no B/fulltask acceptance',source_sha256=hashlib.sha256(Path(envcfg['source'],'takeover.npz').read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(Path(envcfg['reference']).read_bytes()).hexdigest(),prefix_sha256=hashlib.sha256(Path(envcfg['prefix_trace']).read_bytes()).hexdigest())
 if a.pose_motion:cfg.update(object_motion_sensor='pose-difference-world-30hz-v1',phase_semantics='free-motor-hold-v8',motor_action_mode='free-motor-v8-pose',reward_version='free-workspace-closedslider-allhand-v8-pose')
 if a.fail_on_self_contact:cfg['reward_version']='free-workspace-closedslider-allhand-v9-selfterminal'
 if a.functional_contact_reward:cfg.update(reward_version='free-workspace-closedslider-allhand-v10-functional-contact',functional_contact_costs=dict(tail_pressure_foot_scale_m=.006,cap_distance_scale_m=.004,cap_cost=.75,reserve_cost=2.,scope='Operatingface region remains original773 softprior; no exactqtarget or physicschanges'))
 if a.motor_preamble:cfg['motor_preamble']=str(a.motor_preamble)
 runtime=a.output/'controller-source';runtime.mkdir();source_hashes={}
 for name in ['wuji_pose_motion.py','wuji_fresh_pose_migration.py','train_wuji_fresh_regrasp.py','wuji_fresh_capacity_probe.py','wuji_fresh_checkpoint_migration.py','wuji_fresh_free_migration.py','wuji_motor_reference_preamble.py','check_wuji_action_quality.py','g2_contact_geometry.py','wuji_kinematics.py','g2_kinematics.py','wuji_functional_entry_affordance.py','wuji_fresh_prefix_learning.py','wuji_regrasp_learning.py','wuji_regrasp_contract.py','wuji_robot_gravity.py','g2_continuous_scene.py','wuji_retained_push_skill.py','wuji_measured_hold_reference.py']:
  path=Path('scripts')/name;shutil.copyfile(path,runtime/name);source_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 cfg['source_sha256']=source_hashes;(runtime/'manifest.json').write_text(json.dumps(dict(source_sha256=source_hashes,scope='Exactprelaunch source snapshots; originalphysics/assets/retainedB preserved'),indent=2))
 (a.output/'config.json').write_text(json.dumps(cfg,indent=2));record('fresh_incremental_regrasp_ppo_started',[str(a.output)],cfg,updates={'add_active_jobs':[str(a.output)]},next_step='Compare actualcarry/functionalcap progress then deterministic native fullB; never reinterpret v2 weights')
 e=None
 try:
  e=FreshPrefixRegrasp(**envcfg);assert e.observation().shape==(e.n,observation_dim)
  signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True))
  model=FreshRegraspActor(observation_dim,action_dim).cuda();opt=torch.optim.Adam(model.parameters(),lr=3e-4);previous=0
  if a.resume:
   saved=torch.load(a.resume,map_location='cpu');assert saved['format']==checkpoint_format
   for key in ['motor_action_mode','native_coordinate_adaptation','reference_sha256','prefix_sha256']:assert saved['config'][key]==cfg[key]
   model.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer']);previous=saved['round'];cfg['resume_sha256']=hashlib.sha256(a.resume.read_bytes()).hexdigest();(a.output/'config.json').write_text(json.dumps(cfg,indent=2))
  log=(a.output/'learning.jsonl').open('w',buffering=1);begin=time.monotonic();period=cfg['action_period_frames'];gamma=cfg['frame_gamma']**period;lam=cfg['frame_lambda']**period
  for it in range(1,a.rounds+1):
   if stop[0]:break
   obs=e.observation() if it==1 else e.reset(torch.arange(e.n,device=e.device));prefixvalid=~e.failed;assert int(prefixvalid.sum())>=e.n//2,('Invalid physicalprefix',int(prefixvalid.sum()))
   batch=[];total=torch.zeros(e.n,device=e.device);caps=torch.full((e.n,),float('inf'),device=e.device);states=[];physical=[];noises=[];capacity=None;best_state=None;best_value=float('inf')
   for tick in range(e.steps//period):
    alive=~e.failed
    with torch.no_grad():dist,v=model(obs);act=dist.mean if a.deterministic_only else dist.sample();lp=dist.log_prob(act).sum(-1)
    reward=torch.zeros(e.n,device=e.device)
    if a.capacity_probe:noises.append((act-dist.mean).detach().clone())
    for j in range(period):
     newobs,r,done,info=e.step(act);reward+=r*cfg['frame_gamma']**j
     if a.capacity_probe:
      physical.append((e.dof.clone(),e.command_target.clone(),e.rb[:,e.object_index].clone()))
      errors_now=torch.where(info['held'],info['error'],torch.full_like(info['error'],float('inf')));value,index=torch.min(errors_now,0)
      if float(value)<best_value:
       best_value=float(value);best_state=dict(index=int(index),age=len(physical),dof=e.dof[int(index)].clone(),issued=e.command_target[int(index)].clone(),object=e.rb[int(index),e.object_index].clone())
    total+=reward;batch.append((obs,act,lp,v,reward,alive,~done));obs=newobs;caps=torch.minimum(caps,torch.where(~e.failed,e.cap_distance(),torch.full_like(caps,float('inf'))))
    if a.deterministic_only:states.append([e.dof[:,:27,0].cpu().numpy(),e.command_target.cpu().numpy(),e.rb[:,e.object_index].cpu().numpy()])
    if a.capacity_probe and (e.entry_frames>=a.capacity_entry_frames).any():
     chosen=int(torch.nonzero(e.entry_frames>=a.capacity_entry_frames)[0])
     if a.functional_workspace:
      from scripts.g2_kinematics import transform
      measured=e.rb[chosen,e.object_index].cpu().numpy();current=e.affordance.assess(e.dof[chosen,:27,0].cpu().numpy().astype(float),transform(measured[:3],measured[3:7]),float(e.dof[chosen,27,0]))
      if not current['reference_eligible']:
       e.entry_frames[chosen]=0;e.affordance_cache['eligible'][chosen]=False;e.affordance_cache['self_bad'][chosen]=bool(current['self_intersections']);continue
     candidate=a.output/('candidate_round_%03d_env%02d'%(previous+it,chosen));candidate.mkdir()
     torch.save(dict(format=checkpoint_format,model=model.state_dict(),optimizer=opt.state_dict(),round=previous+it-1,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),candidate/'policy-before-probe.pth')
     noise=torch.stack(noises)[:,chosen].cpu().numpy();np.save(candidate/'action-noise.npy',noise)
     np.savez_compressed(candidate/'actual-regrasp-trace.npz',dof=torch.stack([s[0] for s in physical])[:,chosen].cpu().numpy(),issued=torch.stack([s[1] for s in physical])[:,chosen].cpu().numpy(),object=torch.stack([s[2] for s in physical])[:,chosen].cpu().numpy(),prefix_q_1hz=e.prefix_actual_q_1hz[:,chosen].cpu().numpy(),prefix_object_1hz=e.prefix_actual_object_1hz[:,chosen].cpu().numpy())
     from scripts.wuji_fresh_capacity_probe import probe
     capacity=probe(e,chosen,candidate/'fullB');batch[-1][4][chosen]+=capacity['reward'];total[chosen]+=capacity['reward'];batch[-1][6][chosen]=False
     (candidate/'candidate.json').write_text(json.dumps(dict(round=previous+it,chosen_env=chosen,regrasp_seconds=(tick+1)*period/30,noise_scope='Frozen stochasticnoise added to ORIGINAL preupdate actor mean on actualobservations; original B independent; no physicalstate setters',capacity=capacity),indent=2))
     break
    if e.failed.all():break
   if a.capacity_probe and physical:
    trajectory=a.output/('actual_all_envs_round_%03d'%(previous+it));trajectory.mkdir();torch.save(dict(format=checkpoint_format,model=model.state_dict(),round=previous+it-1,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),trajectory/'policy-before-update.pth')
    np.savez_compressed(trajectory/'actual-regrasp-traces.npz',dof=torch.stack([s[0] for s in physical]).cpu().numpy(),issued=torch.stack([s[1] for s in physical]).cpu().numpy(),object=torch.stack([s[2] for s in physical]).cpu().numpy(),stage_initial_object=e.stage_initial_object.cpu().numpy(),stage_slider_start=e.stage_slider_start.cpu().numpy(),action_noise=torch.stack(noises).cpu().numpy(),prefix_valid=prefixvalid.cpu().numpy(),prefix_q_1hz=e.prefix_actual_q_1hz.cpu().numpy(),prefix_object_1hz=e.prefix_actual_object_1hz.cpu().numpy())
    (trajectory/'scope.json').write_text(json.dumps(dict(scope='AllactualunresetfreshA episodes andfull27 stochasticmotor traces BEFORE PPO update. No idealstate set afterA; no native/video/acceptance claim.',physical_frames=len(physical),action_period_frames=period,capacity_probe_result=capacity),indent=2))
   if best_state is not None and capacity is None and a.functional_workspace:
    chosen=best_state['index'];preview=a.output/('best_functional_round_%03d_env%02d'%(previous+it,chosen));preview.mkdir();torch.save(dict(format=checkpoint_format,model=model.state_dict(),round=previous+it-1,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),preview/'policy-before-update.pth');np.save(preview/'action-noise.npy',torch.stack(noises)[:,chosen].cpu().numpy())
    np.savez_compressed(preview/'actual-regrasp-trace.npz',dof=torch.stack([s[0] for s in physical])[:,chosen].cpu().numpy(),issued=torch.stack([s[1] for s in physical])[:,chosen].cpu().numpy(),object=torch.stack([s[2] for s in physical])[:,chosen].cpu().numpy(),prefix_q_1hz=e.prefix_actual_q_1hz[:,chosen].cpu().numpy(),prefix_object_1hz=e.prefix_actual_object_1hz[:,chosen].cpu().numpy())
    from scripts.g2_kinematics import transform
    actualq=best_state['dof'][:27,0].cpu().numpy().astype(float);actualo=best_state['object'].cpu().numpy();affordance=e.affordance.assess(actualq,transform(actualo[:3],actualo[3:7]),float(best_state['dof'][27,0]));(preview/'best-state.json').write_text(json.dumps(dict(functional_error=best_value,actual_regrasp_age_s=best_state['age']/30,chosen_env=chosen,affordance=affordance,scope='Actuallearnedtrajectory andpreupdatepolicy/frozennoises forindependentnative review; no achievedentry/capacityclaim'),indent=2))
   with torch.no_grad():_,nv=model(obs)
   nv=torch.where(~done,nv,torch.zeros_like(nv));adv=torch.zeros(e.n,device=e.device);ads=[];rts=[]
   for ob,ac,lp,v,r,alive,cont in reversed(batch):
    adv=r+gamma*nv*cont-v+gamma*lam*adv*cont;ads.append(adv);rts.append(adv+v);nv=v
   mask=torch.cat([x[5] for x in batch]);ob=torch.cat([x[0] for x in batch])[mask];ac=torch.cat([x[1] for x in batch])[mask];lp=torch.cat([x[2] for x in batch])[mask];ad=torch.cat(list(reversed(ads)))[mask];rt=torch.cat(list(reversed(rts)))[mask];ad=(ad-ad.mean())/(ad.std()+1e-6)
   if not a.deterministic_only:
    for _ in range(4):
     for ix in torch.randperm(len(ob),device=e.device).split(1024):
      dist,v=model(ob[ix]);ratio=(dist.log_prob(ac[ix]).sum(-1)-lp[ix]).exp();loss=-torch.minimum(ratio*ad[ix],ratio.clamp(.8,1.2)*ad[ix]).mean()+.5*(v-rt[ix]).square().mean()-.001*dist.entropy().sum(-1).mean();opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(list(model.actor.parameters())+[model.logstd],1);nn.utils.clip_grad_norm_(model.critic.parameters(),1);opt.step()
   functional_stats={}
   if a.functional_workspace:
    c=e.affordance_cache;functional_stats=dict(full_path_queries=c['full_path_queries'],best_actual_Hsafe_full30mm_FK_error_min_m=float(c['best_safe_path_error'].min()) if torch.isfinite(c['best_safe_path_error']).any() else None,last_checked_full30mm_FK_error_min_m=float(c['path_error'].min()),last_checked_full30mm_eligible=int(c['eligible'].sum()),last_tail_roof_distance_min_m=float(c['tail_distance'].min()),last_tail_roof_distance_median_m=float(c['tail_distance'].median()),last_checked_self_bad=int(c['self_bad'].sum()))
   errors=e.best_entry_error[torch.isfinite(e.best_entry_error)];finitecaps=caps[torch.isfinite(caps)];row=dict(round=previous+it,elapsed_s=time.monotonic()-begin,prefix_valid=int(prefixvalid.sum()),steps=period*len(batch),alive_samples=len(ob),mean_return=float(total.mean()),surviving=int((~e.failed).sum()),best_entry_error_min=float(errors.min()) if len(errors) else None,best_entry_error_median=float(errors.median()) if len(errors) else None,cap_distance_min_mm=float(finitecaps.min()*1000) if len(finitecaps) else None,cap_distance_median_mm=float(finitecaps.median()*1000) if len(finitecaps) else None,max_continuous_held_s=float(e.max_held_frames.max()/30),median_max_continuous_held_s=float(e.max_held_frames.median()/30),best_entry_dwell_frames=int(e.best_entry_dwell.max()),ever_entry_1s_candidates=int(e.entry_awarded.sum()),entry_1s_candidates=int((e.entry_frames>=30).sum()),pause_steps_fraction=float(e.pause_steps.sum()/(prefixvalid.sum()*period*len(batch))),phase_fraction_mean=float((e.phase/(len(e.motor_reference)-1)).mean()),motor_offset_abs_mean_rad=float(e.offset.abs().mean()),motor_action_std_mean=float(model.logstd[:27].clamp(-3.5,-.1).exp().mean()),functional_stats=functional_stats,capacity_probe_result=capacity,scope=cfg['scope']);log.write(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
   if it%5==0 or it==a.rounds or e.entry_awarded.any() or capacity is not None or stop[0]:torch.save(dict(format=checkpoint_format,model=model.state_dict(),optimizer=opt.state_dict(),round=previous+it,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),a.output/('round_%03d.pth'%(previous+it)))
   if states:np.savez_compressed(a.output/('deterministic_%03d.npz'%(previous+it)),q=np.array([s[0] for s in states]),issued=np.array([s[1] for s in states]),object=np.array([s[2] for s in states]),prefix_final_q=e.prefix_final_q.cpu().numpy(),prefix_final_object=e.prefix_final_object.cpu().numpy())
   if capacity is not None:break
  log.close()
 finally:
  if e:e.close()
  record('fresh_incremental_regrasp_ppo_terminal',[str(a.output)],updates={'remove_active_jobs':[str(a.output)]},next_step='Read learningtrend; actualfunctional entry -> native continuous fullB; diagnose representation/reward ifno progress')
if __name__=='__main__':main()
