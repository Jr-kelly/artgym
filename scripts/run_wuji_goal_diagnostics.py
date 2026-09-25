"""Recorded two-GPU queue for bounded acquisition diagnostics."""
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment

ROOT=Path(__file__).resolve().parents[1]


def run_lane(gpu,jobs):
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable),gpu)
    for name,arguments in jobs:
        path=ROOT/'runs/wuji-goal/diagnostics'/name;path.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,'-m','scripts.diagnose_wuji_acquisition','--output',str(path)]+arguments
        record=dict(name=name,gpu=gpu,command=command,started=now(),status='running')
        atomic_json(path/'status.json',record)
        with (path/'worker.log').open('w') as log:
            code=subprocess.call(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        record.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
        atomic_json(path/'status.json',record)


if __name__=='__main__':
    queues=[[],[]]
    for i,controller in enumerate(['hold','replay','random']):
        for step in [0,2500]:
            queues[i%2].append((f'{controller}-curriculum-{step}',
                ['--controller',controller,'--curriculum-step',str(step)]))
    for i,arm in enumerate(['wuji_single_upstream','wuji_single_corrected']):
        cp=ROOT/'runs'/arm/'evaluation/monitor/policies/epoch_002500.pth'
        queues[i].append((arm+'-cp2500',['--controller','checkpoint','--checkpoint',str(cp),
                                     '--curriculum-step','2500']))
    queues[1].append(('replay-acquisition-30hz',['--controller','replay','--task','wuji_acquisition',
                    '--override','object=knife_wuji_acquisition','--save-expert']))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run_lane,gpu,jobs) for gpu,jobs in zip([0,2],queues)]
        for future in futures:future.result()
