"""Bounded short PPO, stopped/continued by actual contact-transfer evidence."""
import argparse,json,time,signal,hashlib
from pathlib import Path
import isaacgym
import torch,numpy as np
from torch import nn
from torch.distributions import Normal
from scripts.wuji_regrasp_learning import RegraspLearning
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_regrasp_contract import PAUSE_TIMING, REWARD_VERSION

class RegraspActor(nn.Module):
    def __init__(self):
        super().__init__();self.actor=nn.Sequential(nn.Linear(149,192),nn.Tanh(),nn.Linear(192,192),nn.Tanh(),nn.Linear(192,28))
        self.critic=nn.Sequential(nn.Linear(149,192),nn.Tanh(),nn.Linear(192,192),nn.Tanh(),nn.Linear(192,1))
        self.logstd=nn.Parameter(torch.full((28,),-.65));nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)
    def forward(self,obs):return Normal(self.actor(obs),self.logstd.clamp(-2.5,-.1).exp()),self.critic(obs).squeeze(-1)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--reference',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--envs',type=int,default=32);p.add_argument('--rounds',type=int,default=50);p.add_argument('--interface-only',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);torch.manual_seed(20261008717);stop=[False];signal.signal(signal.SIGTERM,lambda *_:stop.__setitem__(0,True))
    cfg={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()};cfg.update(action='27 arm/hand motor offsets + pausable phase pacing',
        phase_semantics=PAUSE_TIMING,reward_version=REWARD_VERSION,action_period_frames=5,episode_steps=240,
        phase_action_scope='Actions <= -0.5 pause reference while motor offsets remain active; clock/contact existence does not certify load transfer',
        continuation_rule='Compare sustained carrying, entry proximity/dwell and exploration; isolated deterministic failures or zero full success do not reject learning. Fix ineffective representation/reference/reward before extending it.',
        scope='Actual recorded carrying initialization for sim_oracle transition training; not fresh-table or push success',source_sha256=hashlib.sha256(Path(a.source,'takeover.npz').read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(Path(a.reference).read_bytes()).hexdigest())
    (a.output/'config.json').write_text(json.dumps(cfg,indent=2));record('contact_changing_short_regrasp_started',[str(a.output/'config.json')],cfg,updates={'add_active_jobs':[str(a.output)]},next_step='Verify all actions and pause execute; train only toward an independently usable retained-skill entrance')
    e=None
    try:
        e=RegraspLearning(a.envs,a.source,a.reference);obs=e.observation();assert obs.shape==(a.envs,149),obs.shape
        baseline=e.command_target.clone();acts=torch.zeros((a.envs,28),device=e.device)
        for i in range(min(a.envs,28)):acts[i,i]=.3
        _,_,_,info=e.step(acts)
        report={'obs_shape':list(obs.shape),'all27_motor_offsets_execute':bool((e.offset[:min(a.envs,27)].abs().sum(-1)>0).all()),
                'phase_action_executes':a.envs>=28 and float(e.phase[27])>float(e.phase[26]),
                'environments_with_contacts':int((e.contact_features().sum(-1)>0).sum()),'native_arm_tracking_max_rad':float((e.command_target[:,:7]-e.dof[:,:7,0]).abs().max()),
                'environments_with_knife_contact':int((e.contact[:,e.object_index:e.slider_index+1].norm(dim=-1).sum(-1)>1e-5).sum()),
                'reset_scope':'Training episode initial positions/estimated velocities; no state setter inside step',
                'physical_limits_retained':True,'source_velocity_and_solver_cache_gap_disclosed':True}
        before_phase=e.phase.clone();before_offsets=e.offset.clone()
        paused=torch.zeros((a.envs,28),device=e.device);paused[:,27]=-.75;paused[:,0]=.3
        e.step(paused)
        report.update(phase_semantics=PAUSE_TIMING,phase_pause_executes=bool((e.phase==before_phase).all()),
                      motor_offsets_execute_while_paused=bool((e.offset[:,0]!=before_offsets[:,0]).all()))
        (a.output/'interface.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
        if a.interface_only:return
        assert report['all27_motor_offsets_execute'] and report['phase_action_executes'] and report['phase_pause_executes'] and report['motor_offsets_execute_while_paused'] and report['environments_with_contacts']==a.envs and report['environments_with_knife_contact']==a.envs
        model=RegraspActor().cuda();opt=torch.optim.Adam(model.parameters(),lr=3e-4);log=(a.output/'learning.jsonl').open('w',buffering=1);begin=time.monotonic()
        for it in range(1,a.rounds+1):
            if stop[0]:break
            obs=e.reset(torch.arange(e.n,device=e.device));batch=[];total=torch.zeros(e.n,device=e.device)
            for tick in range(e.steps//cfg['action_period_frames']):
                with torch.no_grad():dist,v=model(obs);act=dist.sample();lp=dist.log_prob(act).sum(-1)
                reward=torch.zeros(e.n,device=e.device)
                for j in range(cfg['action_period_frames']):newobs,r,done,info=e.step(act);reward+=r*.995**j
                total+=reward;batch.append((obs,act,lp,v,reward));obs=newobs
            adv=torch.zeros(e.n,device=e.device);nv=torch.zeros_like(adv);ads=[];rts=[]
            for ob,ac,lp,v,r in reversed(batch):
                period=cfg['action_period_frames'];gamma=.995**period;adv=r+gamma*nv-v+gamma*(.95**period)*adv;ads.append(adv);rts.append(adv+v);nv=v
            ob=torch.cat([x[0] for x in batch]);ac=torch.cat([x[1] for x in batch]);lp=torch.cat([x[2] for x in batch]);ad=torch.cat(list(reversed(ads)));rt=torch.cat(list(reversed(rts)));ad=(ad-ad.mean())/(ad.std()+1e-6)
            for _ in range(4):
                for ix in torch.randperm(len(ob),device=e.device).split(1024):
                    dist,v=model(ob[ix]);ratio=(dist.log_prob(ac[ix]).sum(-1)-lp[ix]).exp()
                    loss=-torch.minimum(ratio*ad[ix],ratio.clamp(.8,1.2)*ad[ix]).mean()+.5*(v-rt[ix]).square().mean()-.001*dist.entropy().sum(-1).mean()
                    opt.zero_grad();loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1);opt.step()
            errors=e.best_entry_error[torch.isfinite(e.best_entry_error)]
            row={'round':it,'elapsed_s':time.monotonic()-begin,'mean_return':float(total.mean()),'surviving':int((~e.failed).sum()),
                 'best_entry_error_min':float(errors.min()) if len(errors) else None,
                 'best_entry_error_median':float(errors.median()) if len(errors) else None,
                 'max_continuous_held_s':float(e.max_held_frames.max()/30),
                 'median_max_continuous_held_s':float(e.max_held_frames.median()/30),
                 'best_entry_dwell_frames':int(e.best_entry_dwell.max()),
                 'ever_entry_1s_candidates':int(e.entry_awarded.sum()),'entry_1s_candidates':int((e.entry_frames>=30).sum()),
                 'pause_steps_fraction':float(e.pause_steps.sum()/(e.n*e.steps)),
                 'phase_fraction_mean':float((e.phase/(len(e.motor_reference)-1)).mean()),
                 'motor_offset_abs_mean_rad':float(e.offset.abs().mean()),
                 'scope':'Training carrying/proximity proxies only; transferred load, hand geometry, retained-skill takeover and full episode not accepted'}
            log.write(json.dumps(row)+'\n');print(json.dumps(row),flush=True)
            if it%10==0 or it==a.rounds or stop[0]:torch.save({'format':'wuji-regrasp-reference-ppo-v2','model':model.state_dict(),'optimizer':opt.state_dict(),'round':it,'config':cfg,'motor_span':e.span.cpu().tolist(),'motor_slew':e.slew.cpu().tolist()},a.output/('round_%03d.pth'%it))
        log.close()
    finally:
        if e is not None:e.close()
        record('contact_changing_short_regrasp_terminal',[str(a.output)],{'interface_only':a.interface_only},updates={'remove_active_jobs':[str(a.output)]},next_step='Read carrying, entry/dwell and exploration trends before choosing continue/representation change; no learning-route rejection from isolated deterministic failures')

if __name__=='__main__':main()
