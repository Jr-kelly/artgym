"""Held-out trajectory action and one-step physical-target errors by phase/finger."""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from omegaconf import OmegaConf
import numpy as np
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--data',nargs='+',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',default='cpu');a=p.parse_args();torch.set_num_threads(4)
 cfg=configuration('wuji_multigrasp',1,['object=knife_wuji_bridge3_20260922','hand=wuji_paper_official_actuator','rl_device='+a.device],train='wujiAcquisitionSAPG');player=build_policy_player(cfg,preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),a.checkpoint,_infer_expl_num_blocks(a.checkpoint),0);model=player.model;rows=[]
 for directory in a.data:
  with np.load(directory/'sequences.npz') as z:d={k:torch.tensor(z[k][:,96:],device=a.device) for k in z.files}
  with np.load(directory/'trace.npz') as z:reached=np.abs(z['slider'][:,96:]-z['goal'][:,96:])<.002
  info=json.loads((directory/'interface.json').read_text());report=json.loads((directory/'report.json').read_text());period=report['protocol']['stage_steps'];lower=torch.tensor(info['joint_lower'],device=a.device);upper=torch.tensor(info['joint_upper'],device=a.device)
  n=d['obs'].shape[1];states=[torch.zeros((s.shape[0],n,s.shape[2]),device=a.device) for s in model.get_default_rnn_state()];errors=[];action=[];reset=torch.zeros((600,n),device=a.device);reset[1:]=d['done'][:-1].float()
  with torch.no_grad():
   for start in range(0,600,100):
    end=start+100;obs=d['obs'][start:end].transpose(0,1).reshape(-1,138)
    mu,_,_,states=model.a2c_network(dict(obs=model.norm_obs(obs),rnn_states=states,seq_length=100,dones=reset[start:end].transpose(0,1).reshape(-1,1)))
    mu=mu.reshape(n,100,20).transpose(0,1);raw=d['initial_target'][start:end]+mu.clamp(-1,1)*.04;raw[:,:,16:]=d['previous_target'][start:end,:,16:]+mu[:,:,16:].clamp(-1,1)*.025;target=raw.clamp(lower,upper)
    errors.append(((target-d['target_clipped'][start:end])/(upper-lower)).abs().cpu().numpy());action.append((mu-d['mu'][start:end]).cpu().numpy())
  error=np.concatenate(errors);act=np.concatenate(action);active=d['active_before'].cpu().numpy().astype(bool);step=np.arange(600)[:,None];streak=np.zeros(n,dtype=int);hold=np.zeros((600,n),bool);arrival=hold.copy()
  for t in range(600):
   if t%period==0:streak[:]=0
   streak=np.where(reached[t],streak+1,0);hold[t]=streak>=9;arrival[t]=(streak>0)&(streak<9)
  groups={}
  for phase,mask in {'all':active,'switch_first15':active&(step%period<15),'arrival_first8':active&arrival,'holding_after9':active&hold}.items():
   for part,sl in [('all',slice(None)),('support',slice(0,16)),('thumb',slice(16,20))]:
    e=error[:,:,sl][mask];v=act[:,:,sl][mask];groups[phase+'_'+part]=dict(values=int(e.size),target_range_mean=float(e.mean()) if e.size else None,target_range_p95=float(np.quantile(e,.95)) if e.size else None,action_mse=float((v*v).mean()) if e.size else None)
  rows.append(dict(data=str(directory),source=int(directory.name.removeprefix('source')) if hasattr(str,'removeprefix') else int(directory.name.replace('source','')),seconds=report['protocol']['stage_seconds'],groups=groups))
 result=dict(checkpoint=str(a.checkpoint),sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),device=a.device,rows=rows,scope='Heldout episode96..127, recurrent full history, one-step physical target conditioned on expert previous target; not closed-loop success; no cross-expert latent supervision')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(output=str(a.output),rows=len(rows))))
if __name__=='__main__':main()
