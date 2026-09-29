"""Replay recorded expert observations through its own recurrent model, no physics."""
import argparse,json,hashlib
from pathlib import Path
from scripts.wuji_goal_common import configuration
from isaacgymenvs.deploy.student_policy_runtime import build_policy_player
from isaacgymenvs.eval_common import preprocess_train_config,_infer_expl_num_blocks
from omegaconf import OmegaConf
import numpy as np
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',default='cpu');p.add_argument('--segment',type=int,default=100);a=p.parse_args();torch.set_num_threads(2)
 cfg=configuration('wuji_multigrasp',1,['object=knife_wuji_bridge3_20260922','hand=wuji_paper_official_actuator','rl_device='+a.device],train='wujiAcquisitionSAPG')
 player=build_policy_player(cfg,preprocess_train_config(cfg,OmegaConf.to_container(cfg.train,resolve=True)),a.checkpoint,_infer_expl_num_blocks(a.checkpoint),0)
 with np.load(a.data/'sequences.npz') as z:d={k:torch.tensor(z[k],device=a.device) for k in z.files}
 T,N,_=d['obs'].shape;states=[torch.zeros((x.shape[0],N,x.shape[2]),device=a.device) for x in player.model.get_default_rnn_state()];errors=[]
 with torch.no_grad():
  for start in range(0,T,a.segment):
   end=min(start+a.segment,T);mask=torch.zeros((T,N),device=a.device);mask[1:]=d['done'][:-1].float()
   mu,_,_,states=player.model.a2c_network(dict(obs=player.model.norm_obs(d['obs'][start:end].transpose(0,1).reshape(-1,d['obs'].shape[-1])),rnn_states=states,seq_length=end-start,dones=mask[start:end].transpose(0,1).reshape(-1,1)))
   errors.append((mu.reshape(N,end-start,20).transpose(0,1)-d['mu'][start:end]).abs())
 error=torch.cat(errors);trace=np.load(a.data/'trace.npz');target_error=float(np.max(abs(trace['target']-d['target_clipped'].cpu().numpy())))
 continuing=(~d['done'][:-1].bool())&d['active_before'][1:].bool()
 previous_error=float((d['previous_action'][1:]-d['executed_action'][:-1]).abs()[continuing].max())
 result=dict(mu_max_error=float(error.max()),mu_mean_error=float(error.mean()),physical_target_max_error=target_error,previous_action_max_error=previous_error,steps=T,episodes=N,checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),passed=bool(error.max()<1e-4 and target_error<1e-6 and previous_error<1e-6),scope='Recorded-history recurrent inference and action-target alignment, no training or new physical episodes')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['passed']
if __name__=='__main__':main()
