"""Original player on exact recorded network inputs/incoming RNN; diagnosis only."""
import argparse,hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration
import torch
from isaacgymenvs.deploy.wuji.temporal_policy_runtime import WujiTemporalPolicyRuntime
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',default='cpu');p.add_argument('--fp32',action='store_true');a=p.parse_args();torch.set_num_threads(2)
 if a.fp32:torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
 root=Path(__file__).resolve().parents[1];f=torch.load(a.fixture,map_location='cpu');n=len(f['ids']);cfg=configuration('wuji_multigrasp',n,['hand=wuji_paper_official_actuator','object=knife_wuji_bridge3_20260922','rl_device='+a.device,'sim_device=cpu'],train='wujiAcquisitionSAPG',seed=2026100211)
 r=WujiTemporalPolicyRuntime(cfg,root/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',root/'runs/unified-student-20261001/SA-real-51200/step_051200.pth',n=n);rows=[]
 for i,row in enumerate(f['probes']):
  r.player.states=[x.clone().to(r.device) for x in f['probes'][i-1]['rnn']] if i else [torch.zeros_like(x).to(r.device) for x in row['rnn']];r.player.model.a2c_network.actor_encoder_obs_override=row['x'].clone().to(r.device)
  with torch.no_grad():action=r.player.get_action(row['obs'].clone().to(r.device),is_deterministic=True)
  rows.append(dict(step=i,action=float((action.cpu()-row['action']).abs().max()),rnn=float(max((x.cpu()-y).abs().max() for x,y in zip(r.player.states,row['rnn'])))))
 result=dict(fixture_sha256=hashlib.sha256(a.fixture.read_bytes()).hexdigest(),exact_recorded_network_inputs=True,recorded_incoming_rnn=True,device=a.device,fp32_override=a.fp32,numerical_flags=dict(cudnn_tf32=torch.backends.cudnn.allow_tf32,matmul_tf32=torch.backends.cuda.matmul.allow_tf32,torch_version=torch.__version__),first_step=rows[0],max_action=max(x['action'] for x in rows),max_rnn=max(x['rnn'] for x in rows),rows=rows,scope='Original player on exact H200 network input/RNN. Isolates construction from device/backend differences; diagnostic, not autonomous interface parity or new physical evaluation.')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
if __name__=='__main__':main()
