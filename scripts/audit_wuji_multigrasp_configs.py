"""Compose the exact captured four commands and verify only declared factors vary."""
import hashlib,json
from pathlib import Path
from scripts.wuji_goal_common import configuration
from omegaconf import OmegaConf
R=Path(__file__).resolve().parents[1]
def flat(x,prefix=''):
 if isinstance(x,dict):
  result={}
  for k,v in x.items():result.update(flat(v,prefix+'.'+k))
  return result
 return {prefix:x}
def main():
 receipt=json.loads((R/'research/multigrasp-20260928/receipts/monitor-latest.json').read_text());out=R/'research/multigrasp-20260928/configs';out.mkdir(exist_ok=True);configs={}
 for arm in 'ABCD':
  name='mg_'+arm+'_seed2801';command=receipt['jobs'][name]['command'];overrides=command[3:]
  cfg=configuration(overrides=overrides);resolved=OmegaConf.to_container(cfg,resolve=True)
  (out/(arm+'.yaml')).write_text(OmegaConf.to_yaml(cfg,resolve=True));configs[arm]=flat(resolved)
 diffs={}
 allowed={'.experiment','.train.params.config.name','.train.params.config.full_experiment_name','.task.env.supportActionSpan','.task.env.trainingStates'}
 for arm in 'BCD':
  delta={k:[configs['A'].get(k),configs[arm].get(k)] for k in set(configs['A'])|set(configs[arm]) if configs['A'].get(k)!=configs[arm].get(k)}
  assert set(delta)<=allowed,delta;diffs[arm]=delta
 models=receipt['initial_models'];assert len({models['mg_'+a+'_seed2801']['model_tensor_sha256'] for a in 'ABCD'})==1
 report=dict(status='passed',differences_from_A=diffs,initial_model_tensor_sha256=models['mg_A_seed2801']['model_tensor_sha256'],hand_joint_order='index,middle,ring,pinky,thumb; four joints each',contact_sensor_order='thumb,index,middle,ring,pinky',quaternion_order='xyzw',pose_frame='hand_base',control_hz=30,source_pin='source-manifest.json',config_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.yaml')})
 (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
