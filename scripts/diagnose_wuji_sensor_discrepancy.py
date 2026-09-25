"""Replay a saved first numerical mismatch without creating a simulator."""
from scripts import wuji_goal_common
import argparse,hashlib,json
from pathlib import Path
import torch
from omegaconf import OmegaConf
from isaacgymenvs.deploy.wuji.rgb_policy_runtime import WujiRGBPolicyRuntime
from scripts.wuji_physical_state_encoder import decode_prediction,SCALES
from scripts.check_wuji_student_actor_runtime import TEACHER

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--device',type=int);a=p.parse_args();assert not a.output.exists()
 torch.set_num_threads(4);cfg=OmegaConf.load(a.run/'config.yaml')
 if a.device is not None:cfg.rl_device=cfg.sim_device='cuda:'+str(a.device)
 torch.cuda.set_device(int(str(cfg.rl_device).split(':')[1]))
 root=Path(__file__).resolve().parents[1];d=torch.load(a.run/'sensor-first-discrepancy.pth',map_location=cfg.rl_device)
 rt=WujiRGBPolicyRuntime(cfg,root/TEACHER,a.artifact);player=rt.player;ref=d['reference_observation'];sensor=d['sensor'];n=len(ref)
 ph=decode_prediction(ref[:,:55],sensor['estimated_state']/ref.new_tensor(SCALES),rt.properties)
 sob=torch.cat([sensor['policy_observation'],ph,ref.new_zeros(n,5),ref[:,137:]],-1)
 results={}
 def replay(name,obs,states,norm=None):
  player.states=[x.clone() for x in states];h=None
  if norm is not None:h=player.model.a2c_network.priv_encoder.register_forward_pre_hook(lambda m,inp:(norm,))
  try:
   with torch.no_grad():x=player.get_action(obs,is_deterministic=True)
  finally:
   if h:h.remove()
  results[name]={'vs_sensor_max':float((x-sensor['action']).abs().max()),'vs_reference_max':float((x-d['reference_action']).abs().max())}
  return x
 refout=replay('exact_reference',ref,d['reference_incoming'],d['reference_normalized_privileged'])
 senout=replay('exact_sensor',sob,d['sensor_incoming'])
 # TorchScript quaternion kernels may switch from unfused to fused arithmetic
 # after warmup. Replay the saved warm-runtime state with warmed kernels too.
 for _ in range(20):ph=decode_prediction(ref[:,:55],sensor['estimated_state']/ref.new_tensor(SCALES),rt.properties)
 sob=torch.cat([sensor['policy_observation'],ph,ref.new_zeros(n,5),ref[:,137:]],-1)
 senout=replay('exact_sensor_warmed_decode',sob,d['sensor_incoming'])
 print(json.dumps(results),flush=True)
 assert results['exact_reference']['vs_reference_max']<1e-6,results
 assert results['exact_sensor_warmed_decode']['vs_sensor_max']<1e-6,results
 for label,first,last in [('encoder_normalization',55,75),('previous_action',75,95),('fk_tips',96,111),('whole_policy',0,111)]:
  changed=ref.clone();changed[:,first:last]=sob[:,first:last]
  replay('replace_'+label,changed,d['reference_incoming'],d['reference_normalized_privileged'])
 replay('replace_history',ref,d['sensor_incoming'],d['reference_normalized_privileged'])
 replay('sensor_with_reference_history',sob,d['reference_incoming'])
 normalized=player.model.norm_obs(player._preproc_obs(sob))[:,111:132]
 replay('replace_estimated_privileged',ref,d['reference_incoming'],normalized)
 fields={}
 for label,first,last in [('initial',0,55),('normalized_joints',55,75),('previous_action',75,95),('goal',95,96),('fk_tips',96,111)]:
  diff=(ref[:,first:last]-sob[:,first:last]).abs();idx=diff.reshape(-1).argmax();fields[label]={'max':float(diff.max()),'row':int(idx)//(last-first),'field':int(idx)%(last-first)+first}
 delta=(senout-refout).abs();idx=delta.reshape(-1).argmax();row=int(idx)//20
 result=dict(status='verified_replay',step=d['step'],failed_check=d['key'],error=d['error'],tolerance=d['tolerance'],fields=fields,ablations=results,action_worst_row=row,action_worst_dof=int(idx)%20,
  recurrent_state_max=[float((x-y).abs().max()) for x,y in zip(d['reference_incoming'],d['sensor_incoming'])],
  estimated_privileged_normalized_max=float((normalized-d['reference_normalized_privileged']).abs().max()),
  discrepancy_sha256=hashlib.sha256((a.run/'sensor-first-discrepancy.pth').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Offline same-H100 actor replays of an old-development first mismatch; no model fitting or threshold changes.')
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
