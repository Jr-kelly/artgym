"""Create one isolated, bounded continuation arm from a frozen expert parent."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--row',type=int,choices=[3,11],required=True)
    p.add_argument('--condition',choices=['original','dense1'],required=True)
    p.add_argument('--gpu',type=int,required=True);p.add_argument('--additional-epochs',type=int,required=True)
    p.add_argument('--name',required=True);p.add_argument('--seed',type=int,default=2026092901)
    p.add_argument('--timeout',type=int,default=18000);a=p.parse_args()
    assert 1<=a.additional_epochs<=1000
    assert not (ROOT/'runs'/a.name).exists()
    parent=ROOT/'runs/hold-20260929/parents'/f'expert{a.row}.pth'
    expected={3:'e4111879414e4e707ccb46538a0c493f71a6fdc1d4f30aa451f68a9170cae13f',
              11:'d5f0cca7d21bc18363da04549a4af7e9ec6db27dd56a48d285cfb1d71bdde1ff'}
    assert hashlib.sha256(parent.read_bytes()).hexdigest()==expected[a.row]
    old=ROOT/'research/multigrasp-20260928/evidence'/f'expert_row{a.row}_seed2810'/'status.json'
    command=json.loads(old.read_text())['command'][3:]
    replacements={'experiment':a.name,'max_iterations':str(1000+a.additional_epochs),
        'seed':str(a.seed),'object.reward.GoalDistance2':'.1' if a.condition=='original' else '1.0'}
    command=[x.split('=',1)[0]+'='+replacements[x.split('=',1)[0]] if x.split('=',1)[0] in replacements else x for x in command]
    command+=['checkpoint='+str(parent)]
    wrapper=[sys.executable,'-m','scripts.run_wuji_hold_job','--name',a.name,'--gpu',str(a.gpu),'--timeout',str(a.timeout),'--','PYTHON','-m','scripts.train_wuji_hold']+command
    spec=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),row=a.row,condition=a.condition,
        seed=a.seed,parent_sha256=expected[a.row],additional_epochs=a.additional_epochs,
        additional_interactions=a.additional_epochs*163840,command=wrapper)
    output=ROOT/'runs/hold-20260929';output.mkdir(parents=True,exist_ok=True)
    (output/(a.name+'-spec.json')).write_text(json.dumps(spec,indent=2)+'\n')
    subprocess.run(wrapper,cwd=ROOT,check=True)


if __name__=='__main__':main()
