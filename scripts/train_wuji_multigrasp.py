"""Run unchanged PPO while recording the exact pre-update model identity."""
import isaacgym
import hashlib,json,runpy
from pathlib import Path
from rl_games.algos_torch.a2c_continuous import A2CAgent
base=A2CAgent.train
def audited_train(self):
    output=Path(self.nn_dir).parent/'initial-model.json'
    model=self.model.state_dict();h=hashlib.sha256()
    for name,value in sorted(model.items()):
        h.update(name.encode());h.update(value.detach().cpu().numpy().tobytes())
    output.write_text(json.dumps(dict(model_tensor_sha256=h.hexdigest(),epoch=self.epoch_num,
        initialization='random; no checkpoint',training_states_sha256=self.vec_env.env.training_states_sha256),indent=2)+'\n')
    return base(self)
A2CAgent.train=audited_train
runpy.run_module('isaacgymenvs.train',run_name='__main__')
