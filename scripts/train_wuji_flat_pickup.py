"""Targeted PPO development from physically replayed whole-flat starts.
No ideal-grasp reset. Policy consumes explicitly sim_oracle poses.
"""
import argparse,json,time,hashlib,signal
from pathlib import Path
from scripts.wuji_flat_pickup_learning_env import FlatPickupLearning
import torch,numpy as np
from torch import nn
from torch.distributions import Normal
class PickupActor(nn.Module):
 def __init__(self):
  super().__init__();self.actor=nn.Sequential(nn.Linear(116,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,27));self.critic=nn.Sequential(nn.Linear(116,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh(),nn.Linear(128,1));self.logstd=nn.Parameter(torch.full((27,),-.5));nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)
 def forward(self,x):return Normal(self.actor(x),self.logstd.clamp(-2,0).exp()),self.critic(x).squeeze(-1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',default='runs/flat-table-20261006/learning/real-prefix-v76');p.add_argument('--output',type=Path,required=True);p.add_argument('--envs',type=int,default=64);p.add_argument('--rounds',type=int,default=10);p.add_argument('--hand-only',action='store_true');p.add_argument('--resume',type=Path);p.add_argument('--seed',type=int,default=2026100678);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed);stop=[False]
 signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True));e=FlatPickupLearning(a.envs,a.seed,data=a.data);
 if a.hand_only:e.span[:7]=0.
 model=PickupActor().cuda();opt=torch.optim.Adam(model.parameters(),lr=3e-4);
 if a.resume:
  saved=torch.load(a.resume,map_location=e.device);model.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer'])
 cfg=dict(vars(a),actor='sim_oracle30Hz relative pose+q/velocity/issuedtarget/phase/offset; no contact-force state',motor_span=e.span.cpu().tolist(),motor_slew=e.slew.cpu().tolist(),policy_decision_period=5,original_physical_limits=True,prefix_every_episode=True,reset_scope='new whole-flat episode only; none at takeover');cfg['output']=str(a.output);cfg['resume']=str(a.resume) if a.resume else None;(a.output/'config.json').write_text(json.dumps(cfg,indent=2));log=(a.output/'learning.jsonl').open('w',buffering=1);clock=time.time()
 def save(i):
  torch.save(dict(model=model.state_dict(),optimizer=opt.state_dict(),round=i,config=cfg,scope='pickup development only; no A→B or independent validation'),a.output/('round_%03d.pth'%i))
 try:
  for it in range(1,a.rounds+1):
   if stop[0]:break
   obs=e.observation();batch=[];epreturn=torch.zeros(e.n,device=e.device)
   while int(e.age[0])<e.steps:
    with torch.no_grad():dist,value=model(obs);act=dist.sample();oldlog=dist.log_prob(act).sum(-1)
    reward=torch.zeros(e.n,device=e.device);before=int(e.age[0]);period=min(5,e.steps-before)
    for j in range(period):newobs,r,done,info=e.step(act);reward+=r*.995**j
    epreturn+=reward;batch.append((obs,act,oldlog,value,reward,period));obs=newobs
   returns=torch.zeros(e.n,device=e.device);adv=torch.zeros(e.n,device=e.device);nextvalue=torch.zeros_like(adv);advantages=[];targets=[]
   for ob,ac,lp,v,r,period in reversed(batch):
    gamma=.995**period;delta=r+gamma*nextvalue-v;adv=delta+gamma*(.95**period)*adv;advantages.append(adv);targets.append(adv+v);nextvalue=v
   advantages.reverse();targets.reverse();ob=torch.cat([b[0] for b in batch]);ac=torch.cat([b[1] for b in batch]);lp=torch.cat([b[2] for b in batch]);ad=torch.cat(advantages);rt=torch.cat(targets);ad=(ad-ad.mean())/(ad.std()+1e-6)
   for epoch in range(4):
    ids=torch.randperm(len(ob),device=e.device)
    for ix in ids.split(1024):
     dist,v=model(ob[ix]);newlog=dist.log_prob(ac[ix]).sum(-1);ratio=(newlog-lp[ix]).exp();loss=-torch.minimum(ratio*ad[ix],ratio.clamp(.8,1.2)*ad[ix]).mean()+.5*(v-rt[ix]).square().mean()-.001*dist.entropy().sum(-1).mean();opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step()
   row=dict(round=it,elapsed_s=time.time()-clock,episodes=a.envs*it,mean_return=float(epreturn.mean()),best_clearance_m=e.best_clearance.cpu().tolist(),held_frames=e.held_frames.cpu().tolist(),pickup_training_candidates=int((e.held_frames>=30).sum()),failures=int(e.failed.sum()),support_candidates=int((e.support_frames>=30).sum()),support_frames=e.support_frames.cpu().tolist(),scope='training reward/geometry held gate only; native continuous validation still required');log.write(json.dumps(row)+'\n');print(json.dumps({k:v for k,v in row.items() if k not in ['best_clearance_m','held_frames']}),flush=True);save(it)
   if it<a.rounds and not stop[0]:e.reset(torch.arange(e.n,device=e.device))
 finally:e.close();log.close()
if __name__=='__main__':main()
