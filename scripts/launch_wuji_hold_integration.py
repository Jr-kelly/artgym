"""Conditional matched-budget singleton/shared-pool continuation from one expert."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--decision',type=Path,required=True)
    p.add_argument('--condition',choices=['singleton','shared'],required=True)
    p.add_argument('--gpu',type=int,required=True);p.add_argument('--name',required=True)
    p.add_argument('--additional-epochs',type=int,required=True);p.add_argument('--seed',type=int,default=2026092903)
    p.add_argument('--timeout',type=int,default=14400);a=p.parse_args()
    assert 1<=a.additional_epochs<=1000
    assert not (ROOT/'runs'/a.name).exists() and not (ROOT/'runs/hold-20260929'/a.name).exists()
    decision=json.loads(a.decision.read_text());choice=decision['integration_starting_expert'];assert choice
    source=choice['source'];assert choice['model'].endswith('-final');condition=choice['model'][:-6]
    parent_name=f'hold_r{source}_{condition}_seed2901'
    parent=ROOT/'runs'/parent_name/'checkpoints/epoch_002000.pth'
    digest=hashlib.sha256(parent.read_bytes()).hexdigest()
    entry=next(x for x in json.loads((ROOT/'research/hold-20260929/receipts/backup-core.json').read_text())['entries'] if x['name']==parent_name and x['epoch']==2000)
    assert digest==entry['sha256']
    pool=ROOT/'research/hold-20260929/data'/('integration-shared.npy' if a.condition=='shared' else f'integration-singleton{source}.npy')
    assert pool.exists()
    command=json.loads((ROOT/'runs/hold-20260929'/parent_name/'status.json').read_text())['command'][3:]
    replacement={'experiment':a.name,'max_iterations':str(2000+a.additional_epochs),'seed':str(a.seed),
                 'task.env.trainingStates':str(pool.relative_to(ROOT)),'checkpoint':str(parent)}
    command=[x.split('=',1)[0]+'='+replacement[x.split('=',1)[0]] if x.split('=',1)[0] in replacement else x for x in command]
    wrapper=[sys.executable,'-m','scripts.run_wuji_hold_job','--name',a.name,'--gpu',str(a.gpu),'--timeout',str(a.timeout),
             '--','PYTHON','-m','scripts.train_wuji_hold_integration']+command
    spec=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),condition=a.condition,source=source,
        parent_sha256=digest,pool_sha256=hashlib.sha256(pool.read_bytes()).hexdigest(),additional_epochs=a.additional_epochs,
        additional_interactions=a.additional_epochs*163840,seed=a.seed,command=wrapper,
        scope='Conditional shared-policy attempt versus same-expert singleton continuation. Same reward/physics/actions/network; pool only. Original3 plus qualifying added sources, unresolved sources excluded explicitly.')
    (ROOT/'runs/hold-20260929'/(a.name+'-spec.json')).write_text(json.dumps(spec,indent=2)+'\n')
    subprocess.run(wrapper,cwd=ROOT,check=True)


if __name__=='__main__':main()
