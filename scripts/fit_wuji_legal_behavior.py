"""Bounded behavior bootstrap from real executed script labels, on developer GPU.

First actual cycle fits actor only; second cycle is offline validation, never
independent physics success. Frozen R800 remains a legal history-conditioned
feature source. Optional zero action base removes its harmful frozen motion;
the same original command memory, gains and actuator bounds are retained.
"""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_robust_learning import ResidualActorCritic,R800,TEACHER
import torch,numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--steps',type=int,default=800);p.add_argument('--seed',type=int,default=2026100351);p.add_argument('--base-mode',choices=['r800','zero'],default='zero');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);torch.manual_seed(a.seed);np.random.seed(a.seed)
 data=np.load(a.dataset);device='cuda';x=torch.tensor(data['public'],device=device);y=torch.tensor(data['executed_action'],device=device);fit=torch.tensor(data['train'],device=device);check=torch.tensor(data['validation'],device=device);saved=torch.load(a.parent,map_location=device);model=ResidualActorCritic().to(device);model.load_state_dict(saved['model']);model.logstd.data.fill_(-3.);scale=torch.full((20,),2.,device=device);base=x[:,131:151] if a.base_mode=='r800' else torch.zeros_like(y);target=torch.atanh(((y-base)/scale).clamp(-.999,.999));opt=torch.optim.Adam(model.parameters(),lr=3e-4,eps=1e-5);ids=fit.nonzero().flatten()
 for step in range(a.steps):
  batch=ids[torch.randint(len(ids),(256,),device=device)];pred=model.actor(x[batch]);loss=(pred-target[batch]).square().mean();opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
 with torch.no_grad():
  predicted=(base+scale*model.actor(x).tanh()).clamp(-1,1);error=(predicted-y).square();report=dict(args=vars(a),dataset_sha256=hashlib.sha256(a.dataset.read_bytes()).hexdigest(),parent_sha256=hashlib.sha256(a.parent.read_bytes()).hexdigest(),training_frames=int(fit.sum()),validation_frames=int(check.sum()),train_action_mse=float(error[fit].mean()),validation_action_mse=float(error[check].mean()),validation_action_max_error=float((predicted-y)[check].abs().max()),action_base_mode=a.base_mode,scope='Offline script-label fitting only; nominal repeat-cycle holdout, not new physical rollout or geometry generalization; source body roll unresolved',input='154 legal features, actual50-history frozenR800 base action retained as feature; no current object/slider/contact/load truth')
 payload=dict(saved);payload.update(model=model.state_dict(),optimizer=opt.state_dict(),action_scale=scale.tolist(),action_base_mode=a.base_mode,args=vars(a),rng_cpu=torch.get_rng_state(),rng_cuda=torch.cuda.get_rng_state_all(),rng_numpy=np.random.get_state(),behavior_bootstrap=report,teacher_sha256=hashlib.sha256(TEACHER.read_bytes()).hexdigest(),student_sha256=hashlib.sha256(R800.read_bytes()).hexdigest(),resume='Offline actor Adam updated; critic inherited; future PPO resumes with new physics episodes. PPO updates count retained, BC steps separately reported')
 path=a.output/'behavior_bootstrap.pth';torch.save(payload,path);report['checkpoint_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();path.with_suffix('.sha256').write_text(report['checkpoint_sha256']+'\n');(a.output/'report.json').write_text(json.dumps(report,default=str,indent=2));print(json.dumps(report,default=str))
if __name__=='__main__':main()
