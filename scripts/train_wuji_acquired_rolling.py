"""Bounded all-arm/all-hand learning of a short actual contact transfer.

Actual recorded initialization only, missing raw velocities/contact caches;
short reward and contact-tensor components do not certify original B or full A.
Original geometry, friction, mass, effort, PD and passive brake are retained.
"""
import argparse,json,time,hashlib,signal,shutil
from pathlib import Path
import isaacgym
import numpy as np,torch
from scripts.wuji_regrasp_learning import RegraspLearning
from scripts.train_wuji_regrasp import RegraspActor
from scripts.wuji_regrasp_contract import phase_increment
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_conjugate,quat_mul

class AcquiredRolling(RegraspLearning):
 def __init__(self,n,source,reference,guided_incremental=False):
  self.guided_incremental=guided_incremental;self.extra_ready=False
  super().__init__(n,source,reference,physx_buffer_multiplier=16,clear_contact_cache_on_reset=True,safe_reset_order=True)
  self.back_patch_target=self.recipe.get('back_patch_target_knife_m');self.patch_vertices=None
  if self.back_patch_target is not None:
   from scripts.g2_contact_geometry import DigitGeometry
   g=DigitGeometry();self.patch_vertices=self.tensor(np.concatenate([v for v,normals in g.meshes['hand_r_ring_pad_link']]));self.patch_index=self.rb_names.index('hand_r_ring_pad_link')
  self.H=HandIntersection();self.hbad=torch.zeros(n,device=self.device,dtype=torch.bool);self.ring_ids=[i for i,name in enumerate(self.rb_names)if '_ring_'in name];self.extra_ready=True;self.reset(torch.arange(n,device=self.device),perturb=False)
 def reset(self,ids,perturb=False):
  result=super().reset(ids,perturb=False)
  if self.extra_ready:
   self.hbad[:]=False;self.initial_object=self.rb[:,self.object_index].clone();self.previous_potential=self.metrics()['potential'];self.best_rotation=torch.ones(self.n,device=self.device)*float('inf');self.best_bearing=torch.zeros(self.n,device=self.device);self.safe_steps=torch.zeros(self.n,device=self.device)
  return result
 def metrics(self):
  m=super().entry_metrics()
  if not self.extra_ready:return m
  obj=self.rb[:,self.object_index];reaction=-self.contact[:,self.ring_ids].sum(1);body=quat_apply(quat_conjugate(obj[:,3:7]),reaction);back=body[:,1];m['ring_back_component_N']=back
  # The short curriculum asks for relative movement and a new back bearing,
  # not an exact finger target or a geometrical substitute for B capacity.
  error=m['position_m']/.02+m['rotation_rad']/.3+2*((.12-back).clamp(min=0)/.12).clamp(max=2)+.05*m['q_rms_rad']/.5
  if self.patch_vertices is not None:
   pad=self.rb[:,self.patch_index];rot=quat_mul(quat_conjugate(obj[:,3:7]),pad[:,3:7]);pos=quat_apply(quat_conjugate(obj[:,3:7]),pad[:,:3]-obj[:,:3]);nv=len(self.patch_vertices);vertices=quat_apply(rot[:,None,:].expand(-1,nv,-1).reshape(-1,4),self.patch_vertices[None].expand(self.n,-1,-1).reshape(-1,3)).reshape(self.n,nv,3)+pos[:,None,:];weights=torch.softmax(vertices[:,:,1]/.0002,1);foot=(weights[:,:,None]*vertices).sum(1);patch_error=(foot-self.tensor(self.back_patch_target)).norm(dim=-1);error+=2*patch_error/.01;m.update(ring_patch_position_knife_m=foot,ring_patch_error_m=patch_error,ring_patch_max_Y_m=vertices[:,:,1].max(1).values)
  held=m['held']&~self.hbad;potential=torch.where(held,(1-error/10).clamp(0,1),torch.zeros_like(error));m.update(held=held,potential=potential,error=error);return m
 def step(self,action):
  action=action.detach().clamp(-1,1);active=~self.failed;change=action[:,:27]*self.slew if self.guided_incremental else (action[:,:27]*self.span-self.offset).clamp(-self.slew,self.slew);self.offset=torch.where(active[:,None],(self.offset+change).clamp(-self.span,self.span),self.offset);self.phase=torch.where(active,(self.phase+phase_increment(action[:,27])).clamp(max=len(self.motor_reference)-1.0001),self.phase);target=self.guide_targets()+self.offset;target=self.command_target+(target-self.command_target).clamp(-self.slew,self.slew);self.servo(torch.where(active[:,None],target,self.command_target));self.age+=1
  if int(self.age[0])%15==0:
   for i in torch.nonzero(~self.failed).flatten().cpu().tolist():self.hbad[i]=bool(self.H.inspect(self.dof[i,7:27,0].cpu().numpy().astype(float)))
  m=self.metrics();new_failure=~self.failed&((m['clearance_m']<.025)|~m['finite']|self.hbad);self.failed|=new_failure;held=m['held']&~self.failed;potential=torch.where(held,m['potential'],torch.zeros_like(m['potential']));reward=150*(.999*potential-self.previous_potential)-.05*held.float()-60*new_failure.float();reward=torch.where(active,reward,torch.zeros_like(reward));self.previous_potential=potential;self.best_rotation=torch.minimum(self.best_rotation,torch.where(held,m['rotation_rad'],torch.full_like(m['rotation_rad'],float('inf'))));self.best_bearing=torch.maximum(self.best_bearing,torch.where(held,m['ring_back_component_N'],torch.zeros_like(m['ring_back_component_N'])));self.safe_steps+=held.float();return self.observation(),reward,self.failed.clone(),m

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--incremental-motor',action='store_true');p.add_argument('--rounds',type=int,default=10);p.add_argument('--envs',type=int,default=32);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(2026100892);stop=[False];signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True));cfg=dict(motor_action_semantics='guided-incremental-v1' if a.incremental_motor else 'absolute-offset-v2',task_stroke_m=.03,source=str(a.source),reference=str(a.reference),source_sha256=hashlib.sha256((a.source/'takeover.npz').read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(a.reference.read_bytes()).hexdigest(),phase_semantics='pause-linear-v2',action_period_frames=5,episode_steps=240,reward_version='actual-cleared-patch-wholegrip-bearing-v2'if json.loads(a.reference.read_text()).get('back_patch_target_knife_m')is not None else 'actual-four-contact-relative15-backbearing-v1',B_task_stroke_m=.03,scope=__doc__,continuation_rule=str(a.rounds)+' bounded short rounds; actual safe new back bearing -> frozen native proof; no progress -> change load-control representation, no unboundedrepeat')
 runtime=a.output/'controller-source';runtime.mkdir();cfg['source_sha256s']={}
 for name in ['train_wuji_acquired_rolling.py','wuji_regrasp_learning.py','train_wuji_regrasp.py','wuji_regrasp_reference_policy.py','wuji_regrasp_contract.py','check_wuji_action_quality.py','wuji_robot_gravity.py','g2_continuous_scene.py']:
  path=Path('scripts')/name;shutil.copyfile(path,runtime/name);cfg['source_sha256s'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 (a.output/'config.json').write_text(json.dumps(cfg,indent=2));record('actual_acquired_reference_guided_short_learning_started_'+('v893'if a.incremental_motor else 'v892'),[str(a.output/'config.json')],cfg,updates={'add_active_jobs':[str(a.output)]},next_step='Judgeheldrelative15andactualRingbackreaction fromshortrealstate; frozennativebeforeanyfullA repeat')
 e=None
 try:
  e=AcquiredRolling(a.envs,a.source,a.reference,a.incremental_motor);model=RegraspActor().cuda();opt=torch.optim.Adam(model.parameters(),lr=3e-4)
  with torch.no_grad():model.logstd[:27].fill_(np.log(.12));model.logstd[27]=np.log(.35)
  begin=time.monotonic();log=(a.output/'learning.jsonl').open('w',buffering=1)
  for it in range(1,a.rounds+1):
   if stop[0]:break
   obs=e.reset(torch.arange(e.n,device=e.device));batch=[];physical=[];noise=[];contact_states=[];total=torch.zeros(e.n,device=e.device);start=e.entry_metrics()['rotation_rad'].clone()
   for tick in range(48):
    with torch.no_grad():dist,v=model(obs);act=dist.sample();lp=dist.log_prob(act).sum(-1);noise.append((act-dist.loc).cpu());alive=~e.failed
    reward=torch.zeros(e.n,device=e.device)
    for _ in range(5):new,r,done,m=e.step(act);reward+=r;physical.append((e.dof.clone().cpu(),e.command_target.clone().cpu(),e.rb[:,e.object_index].clone().cpu()));contact_states.append(e.contact.clone().cpu())
    total+=reward;batch.append((obs,act,lp,v,reward,alive,~done));obs=new
    if done.all():break
   ads=[];rts=[];adv=torch.zeros(e.n,device=e.device);nv=torch.zeros_like(adv)
   for ob,ac,lp,v,r,alive,cont in reversed(batch):adv=r+.999**5*nv*cont-v+.999**5*.985**5*adv*cont;ads.append(adv);rts.append(adv+v);nv=v
   mask=torch.cat([x[5]for x in batch]);ob=torch.cat([x[0]for x in batch])[mask];ac=torch.cat([x[1]for x in batch])[mask];lp=torch.cat([x[2]for x in batch])[mask];ad=torch.cat(list(reversed(ads)))[mask];rt=torch.cat(list(reversed(rts)))[mask];ad=(ad-ad.mean())/(ad.std()+1e-6)
   trajectory=a.output/('actual_round_%03d'%it);trajectory.mkdir();torch.save(dict(format='wuji-regrasp-reference-ppo-v2',model=model.state_dict(),round=it-1,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),trajectory/'policy-before-update.pth');np.savez_compressed(trajectory/'actual-traces.npz',dof=torch.stack([x[0]for x in physical]).numpy(),issued=torch.stack([x[1]for x in physical]).numpy(),object=torch.stack([x[2]for x in physical]).numpy(),action_noise=torch.stack(noise).numpy(),decision_observations=torch.stack([x[0].detach().cpu()for x in batch]).numpy(),decision_actions=torch.stack([x[1].detach().cpu()for x in batch]).numpy(),contact_tensor=torch.stack(contact_states).numpy());row=dict(round=it,elapsed_s=time.monotonic()-begin,initial_short_rotation_deg=float(start.mean()*180/np.pi),best_short_rotation_deg=float(e.best_rotation.min()*180/np.pi),median_best_short_rotation_deg=float(e.best_rotation.median()*180/np.pi),mean_return=float(total.mean()),surviving=int((~e.failed).sum()),H_failed=int(e.hbad.sum()),median_safe_s=float(e.safe_steps.median()/30),best_back_component_N=float(e.best_bearing.max()),max_motor_std=float(model.logstd[:27].exp().max()),scope='Shortlearningproxies/allactualtraces, no B/freshsuccess');
   if e.patch_vertices is not None:row.update(best_final_patch_error_m=float(m['ring_patch_error_m'].min()),min_final_patch_max_Y_m=float(m['ring_patch_max_Y_m'].min()))
   log.write(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
   for _ in range(4):
    for ix in torch.randperm(len(ob),device=e.device).split(1024):
     dist,v=model(ob[ix]);ratio=(dist.log_prob(ac[ix]).sum(-1)-lp[ix]).exp();loss=-torch.minimum(ratio*ad[ix],ratio.clamp(.8,1.2)*ad[ix]).mean()+.5*(v-rt[ix]).square().mean()-.001*dist.entropy().sum(-1).mean();opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);opt.step()
   torch.save(dict(format='wuji-regrasp-reference-ppo-v2',model=model.state_dict(),optimizer=opt.state_dict(),round=it,config=cfg,motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist()),a.output/('round_%03d.pth'%it))
  log.close()
 finally:
  if e:e.close()
  record('actual_acquired_reference_guided_short_learning_terminal_'+('v893'if a.incremental_motor else 'v892'),[str(a.output)],updates={'remove_active_jobs':[str(a.output)]},next_step='Readshortsafeprogress andfreezeusefulactualcandidate; replaynativebeforefullA continuation')
if __name__=='__main__':main()
