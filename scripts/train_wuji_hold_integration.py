"""Audit a CP2000 expert continuation for conditional pool integration."""
import isaacgym
import hashlib
import json
import runpy
from pathlib import Path
import torch
from rl_games.algos_torch.a2c_continuous import A2CAgent


def digest(value):
    h=hashlib.sha256()
    def add(item):
        if torch.is_tensor(item):
            h.update(str(item.dtype).encode());h.update(str(tuple(item.shape)).encode())
            h.update(item.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(item,dict):
            for key in sorted(item,key=str):h.update(str(key).encode());add(item[key])
        elif isinstance(item,(list,tuple)):
            for sub in item:add(sub)
        else:h.update(repr(item).encode())
    add(value);return h.hexdigest()


original=A2CAgent.train
def audited_train(self):
    env=self.vec_env.env
    receipt=dict(epoch=self.epoch_num,frame=self.frame,num_actors=self.num_actors,
        model_sha256=digest(self.model.state_dict()),optimizer_sha256=digest(self.optimizer.state_dict()),
        last_lr=self.last_lr,training_states_sha256=env.training_states_sha256,
        reward_scales=env.reward_scales,span=env.cfg['env']['supportActionSpan'],
        rollout_reset=self.obs is None,
        scope='CP2000 full expert continuation; only pool differs between shared-policy and singleton consolidation arms. PhysX absent; paired seed resets rollout/RNN. No scripted controller or teacher routing.')
    assert self.epoch_num==2000 and self.frame==327680000
    assert self.obs is None and self.rnn_states is None and receipt['span']==.04
    (Path(self.nn_dir).parent/'resume-identity.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return original(self)


A2CAgent.train=audited_train
runpy.run_module('isaacgymenvs.train',run_name='__main__')
