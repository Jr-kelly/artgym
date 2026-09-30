"""Audited SAPG training, serializing Adam/counters and RNG (not PhysX state)."""
import isaacgym
import json,time,runpy,random,hashlib
from pathlib import Path
import numpy as np
import torch
from rl_games.algos_torch.a2c_continuous import A2CAgent

def digest(state):
    h=hashlib.sha256()
    for k,v in sorted(state.items()):
        h.update(k.encode());h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
old_get=A2CAgent.get_full_state_weights
old_set=A2CAgent.set_full_state_weights
old_train=A2CAgent.train
old_epoch=A2CAgent.train_epoch
old_update=A2CAgent.train_actor_critic

def get(self):
    state=old_get(self)
    state['recovery_rng']=dict(torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all(),numpy=np.random.get_state(),python=random.getstate())
    state['recovery_optimizer_updates']=getattr(self,'recovery_updates',0)
    state['recovery_scope']='Adam/model/normalizer/SAPG/counters/RNG restored; PhysX not serialized, fresh rollout and recurrent reset on resume'
    return state

def restore(self,state,set_epoch=True):
    old_set(self,state,set_epoch)
    self.recovery_updates=state.get('recovery_optimizer_updates',0)
    if 'recovery_rng' in state:
        r=state['recovery_rng'];torch.set_rng_state(r['torch'].cpu());torch.cuda.set_rng_state_all([x.cpu() for x in r['cuda']]);np.random.set_state(r['numpy']);random.setstate(r['python'])

def update(self,*args,**kwargs):
    result=old_update(self,*args,**kwargs)
    self.recovery_updates=getattr(self,'recovery_updates',0)+1
    return result

def train(self):
    out=Path(self.experiment_dir);out.mkdir(parents=True,exist_ok=True)
    env=self.vec_env.env
    row=dict(epoch=self.epoch_num,frame=self.frame,optimizer_updates=getattr(self,'recovery_updates',0),num_actors=self.num_actors,model_sha256=digest(self.model.state_dict()),training_states_sha256=env.training_states_sha256,reward_scales=env.reward_scales_current,action_step_rad=float(env.dt*env.hand_dof_speed_scale),control_dt=float(env.dt*env.control_freq_inv),config=env.cfg,source=str(Path(__file__).resolve()))
    (out/'startup.json').write_text(json.dumps(row,indent=2,default=str)+'\n')
    # Populate zero rollout buffers before serializing the random initial state.
    self.init_tensors()
    self.save(str(out/'initial'))
    return old_train(self)

def epoch(self):
    start=time.monotonic();before=getattr(self,'recovery_updates',0)
    result=old_epoch(self)
    env=self.vec_env.env
    row=dict(epoch=self.epoch_num,frame_after=self.frame+self.curr_frames,optimizer_updates=getattr(self,'recovery_updates',0),updates_this_epoch=getattr(self,'recovery_updates',0)-before,wall_seconds=time.monotonic()-start,rollout_seconds=float(result[1]),update_seconds=float(result[2]),lr=self.last_lr,curriculum_epoch=env.policy_update_step,reward_weights=env.reward_scales_current,source_visits=env.source_visits.cpu().tolist(),metrics={k:float(v) for k,v in env.extras.items() if (k.startswith('source') or k in env.reward_scales_current) and (isinstance(v,(int,float)) or torch.is_tensor(v) and v.numel()==1)})
    with (Path(self.experiment_dir)/'learning.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    return result
A2CAgent.get_full_state_weights=get;A2CAgent.set_full_state_weights=restore;A2CAgent.train=train;A2CAgent.train_epoch=epoch;A2CAgent.train_actor_critic=update
runpy.run_module('isaacgymenvs.train',run_name='__main__')
