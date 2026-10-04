"""Resume saved model/Adam/RNG with its explicit training configuration.

The physics starts fresh episodes; this never claims bitwise solver resume.
Changing the scene/curriculum should use the trainer's explicit overrides.
"""
import argparse,json,subprocess,sys
from pathlib import Path
import torch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--updates',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();saved=torch.load(a.checkpoint,map_location='cpu')
    assert saved['format']=='wuji-r800-residual-ppo-v1' and a.updates>saved['updates']
    config=dict(saved['args'])
    for key in ['initialize_model_from','fresh_sampling_seed','override_initial_estimate_scene',
                'reset_support_logstd','reset_thumb_logstd','reset_residual_head']:
        config[key]=None
    config.update(resume=str(a.checkpoint.resolve()),updates=a.updates,output=str(a.output))
    command=[sys.executable,'-m','scripts.train_wuji_robust_residual']
    for key,value in config.items():
        if value is None or value is False:continue
        command.append('--'+key.replace('_','-'))
        if value is not True:command.append(str(value))
    # A separate receipt does not precreate the trainer's output directory.
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.with_name(a.output.name+'-resume-command.json').write_text(json.dumps(dict(
        command=command,source_checkpoint=str(a.checkpoint),previous_updates=saved['updates'],
        scope=__doc__),indent=2)+'\n')
    subprocess.run(command,check=True)


if __name__=='__main__':main()
