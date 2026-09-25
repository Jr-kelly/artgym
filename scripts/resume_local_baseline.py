"""Resume the reboot-interrupted baseline with its exact saved launch parameters."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment

ROOT=Path('/data/research/artgym')
OLD=ROOT/'runs/wuji_knife_fingertip_sapg'
RUN=ROOT/'runs/wuji_knife_fingertip_resume_20260921'


def main():
    RUN.mkdir(exist_ok=True)
    lock=(RUN/'pipeline.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (RUN/'pipeline-status.json').exists():raise RuntimeError('Resume run already recorded')
    old=json.loads((OLD/'pipeline-status.json').read_text())
    previous=next(s for s in old['stages'] if s['name']=='teacher')
    checkpoint=RUN/'resume_source_epoch_005800.pth'
    shutil.copyfile(OLD/'last/model.pth',checkpoint)
    import torch
    payload=torch.load(checkpoint,map_location='cpu')[0]
    if payload['epoch']!=5800 or 'optimizer' not in payload:raise ValueError('Incomplete resume checkpoint')
    del payload
    command=[f'experiment={RUN.name}' if item.startswith('experiment=') else item for item in previous['command']]
    command.append(f'checkpoint={checkpoint}')
    env=runtime_environment({'project':str(ROOT),'python':sys.executable},0)
    with (RUN/'teacher.log').open('a') as log:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    state=dict(status='teacher',pid=os.getpid(),started=now(),resumed_from=str(OLD),
        checkpoint=str(checkpoint),resume_epoch=5800,reason='Local host reboot at 2026-09-21 11:17 Asia/Shanghai',
        stages=[dict(name='teacher',status='running',pid=process.pid,command=command,started=now())])
    atomic_json(RUN/'pipeline-status.json',state)
    previous.update(status='interrupted',interruption='Host reboot',resumed_run=str(RUN))
    old.update(status='interrupted',resumed_run=str(RUN));atomic_json(OLD/'pipeline-status.json',old)
    config_path=ROOT/'runs/checkpoint-monitor/config.json';config=json.loads(config_path.read_text())
    if not any(r['name']==RUN.name for r in config['runs']):
        spec=dict(config['runs'][0],name=RUN.name,run=str(RUN));config['runs'].append(spec);atomic_json(config_path,config)
    code=process.wait();state.update(status='completed' if code==0 else 'failed',finished=now())
    state['stages'][0].update(status=state['status'],finished=now(),returncode=code)
    atomic_json(RUN/'pipeline-status.json',state)
    raise SystemExit(code)


if __name__=='__main__':main()
