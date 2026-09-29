"""Resolve and audit actual followup command configurations, without simulation."""
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration
from scripts.audit_wuji_hold_configs import flatten
from omegaconf import OmegaConf


def main():
    root=Path(__file__).resolve().parents[1]
    receipts=json.loads((root/'research/hold-20260929/receipts/followup-initial-identities.json').read_text())
    out=root/'research/hold-20260929/configs-followup';out.mkdir(exist_ok=False);configs={}
    for name,item in receipts.items():
        config=configuration(overrides=item['status']['command'][3:])
        (out/(name+'.yaml')).write_text(OmegaConf.to_yaml(config,resolve=True))
        configs[name]=flatten(OmegaConf.to_container(config,resolve=True))
    results=[]
    for left,right,factor in [('hold_r3_original_seed2902','hold_r3_dense1_seed2902','.object.reward.GoalDistance2'),
                              ('hold_integrate_singleton_seed2903','hold_integrate_shared_seed2903','.task.env.trainingStates')]:
        a,b=configs[left],configs[right]
        delta={key:[a.get(key),b.get(key)] for key in a.keys()|b.keys() if a.get(key)!=b.get(key)}
        assert set(delta)=={'.experiment','.train.params.config.name','.train.params.config.full_experiment_name',factor},delta
        results.append(dict(left=left,right=right,differences=delta))
    report=dict(status='passed',pairs=results,sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.yaml')})
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
