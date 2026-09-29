"""Frozen final-budget shared-policy evaluation; no final-data checkpoint choice."""
import argparse
import datetime
import json
from pathlib import Path
from scripts.evaluate_wuji_hold import evaluate,wait_for,sha,ROOT,BASE


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
    plan=json.loads(a.plan.read_text());deadline=datetime.datetime.fromisoformat(plan['deadline_utc']).timestamp()
    out=BASE/plan['evaluation_label'];out.mkdir(parents=True,exist_ok=False)
    for name in plan['training_names'].values():wait_for(BASE/name/'status.json','status','completed',deadline)
    models={'parent':ROOT/plan['parent_checkpoint'],'historical':ROOT/plan['historical_checkpoint']}
    models.update({condition:ROOT/'runs'/name/'checkpoints'/('epoch_%06d.pth'%plan['final_epoch']) for condition,name in plan['training_names'].items()})
    frozen=dict(plan,models={name:dict(path=str(cp.relative_to(ROOT)),sha256=sha(cp)) for name,cp in models.items()},
        frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu=a.gpu)
    (out/'plan.json').write_text(json.dumps(frozen,indent=2)+'\n')
    states=ROOT/plan['final_states'];assert sha(states)==plan['final_states_sha256']
    results=[dict(model='static',**evaluate(models['parent'],states,'static',a.gpu,plan['evaluation_label']+'-static'))]
    for name,cp in models.items():
        for protocol in ['fixed2','fixed5','arrival']:
            results.append(dict(model=name,**evaluate(cp,states,protocol,a.gpu,plan['evaluation_label']+'-'+name+'-'+protocol)))
            (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
    (out/'results.json').write_text(json.dumps(dict(status='completed',plan=frozen,results=results),indent=2)+'\n')


if __name__=='__main__':main()
