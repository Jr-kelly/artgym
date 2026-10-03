"""Resume a saved experiment configuration without repeating its initialization."""
import argparse,json,subprocess,sys
from pathlib import Path
import torch

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--updates',type=int,required=True);p.add_argument('--print-only',action='store_true');a=p.parse_args()
 root=Path(__file__).resolve().parents[1];saved=torch.load(a.checkpoint,map_location='cpu');assert saved['format']=='wuji-r800-residual-ppo-v1' and a.updates>saved['updates'];assert not a.output.exists()
 args=dict(saved['args']);args.update(resume=str(a.checkpoint.resolve()),output=str(a.output.resolve()),updates=a.updates,initialize_model_from=None,fresh_sampling_seed=None,reset_support_logstd=None,support_delta_coordinates=None,override_initial_estimate_scene=None)
 # Explicit saved clocks/credit parameters are required; original defaults
 # would otherwise restore weights while silently changing the experiment.
 args['support_command_period']=saved.get('support_command_period',1);args['support_latch_after_preparation']=saved.get('support_latch_after_preparation',False)
 cmd=[sys.executable,'-m','scripts.train_wuji_robust_residual']
 for name,value in args.items():
  if value is None or value is False:continue
  cmd.append('--'+name.replace('_','-'))
  if value is not True:cmd.append(str(value))
 receipt=dict(command=cmd,checkpoint_updates=saved['updates'],target_absolute_updates=a.updates,scope='Restore model/Adam/RNG and saved experiment configuration. New physics episodes; not exact solver continuation. Initialization, new samplingseed and exploration resets omitted; no hardware interfaces.')
 print(json.dumps(receipt),flush=True)
 if not a.print_only:
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.with_name(a.output.name+'.resume-command.json').write_text(json.dumps(receipt,indent=2))
  raise SystemExit(subprocess.call(cmd,cwd=root))

if __name__=='__main__':main()
