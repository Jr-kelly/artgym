"""Resolve the real four training commands and permit only the declared coefficient."""
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration
from omegaconf import OmegaConf

ROOT=Path(__file__).resolve().parents[1]


def flatten(value,prefix=''):
    if not isinstance(value,dict):return {prefix:value}
    result={}
    for key,item in value.items():result.update(flatten(item,prefix+'.'+key))
    return result


def main():
    receipt=json.loads((ROOT/'research/hold-20260929/receipts/monitor-latest.json').read_text())
    out=ROOT/'research/hold-20260929/configs';out.mkdir(parents=True,exist_ok=False)
    configs={};differences={}
    for row in (3,11):
        for condition in ('original','dense1'):
            name=f'hold_r{row}_{condition}_seed2901'
            cfg=configuration(overrides=receipt['jobs'][name]['command'][3:])
            assert cfg.task.env.supportActionSpan==.04 and cfg.task.env.absolutePoseObjective.ramp_epochs==0
            assert all(value==cfg.object.reward[key] for key,value in cfg.task.env.rewardWeightCurriculum.items())
            (out/(name+'.yaml')).write_text(OmegaConf.to_yaml(cfg,resolve=True))
            configs[name]=flatten(OmegaConf.to_container(cfg,resolve=True))
        a,b=[configs[f'hold_r{row}_{condition}_seed2901'] for condition in ('original','dense1')]
        delta={key:[a.get(key),b.get(key)] for key in a.keys()|b.keys() if a.get(key)!=b.get(key)}
        assert set(delta)=={'.experiment','.train.params.config.name','.train.params.config.full_experiment_name','.object.reward.GoalDistance2'},delta
        differences[row]=delta
    report=dict(status='passed',differences=differences,
        source='Actual remote training commands; local resolved configuration with matching task source',
        sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.yaml')})
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
