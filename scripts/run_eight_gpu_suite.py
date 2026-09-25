"""Persistently coordinate official data jobs, gated teacher runs, and monitoring."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import re

from scripts.monitor_wuji_checkpoints import atomic_json, now, pid_alive, read_json, runtime_environment
from scripts.suite_scheduling import TRAINING_ARMS,training_ready,pending_data,choose_data_gpus

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/experiment-suite'


def main():
    STATE.mkdir(parents=True,exist_ok=True)
    lock=(STATE/'suite.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        if '--ensure' in sys.argv:
            print(json.dumps(read_json(STATE/'status.json',{'status':'starting'})));return
        raise
    if '--ensure' in sys.argv:
        if not (STATE/'lygra-ready.json').exists():
            print(json.dumps({'status':'waiting_for_runtime_validation'}));return
        with (STATE/'suite.log').open('a') as log:
            process=subprocess.Popen([sys.executable,'-m','scripts.run_eight_gpu_suite'],cwd=ROOT,
                env=runtime_environment({'project':str(ROOT),'python':sys.executable}),
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        fcntl.flock(lock,fcntl.LOCK_UN)
        print(json.dumps({'status':'starting','pid':process.pid}));return
    (STATE/'suite.pid').write_text(str(os.getpid()))
    manifest=read_json(ROOT/'experiment_suite.json')
    processes={}
    dataset_jobs={}
    env=runtime_environment({'project':str(ROOT),'python':sys.executable})

    def launch_reference(name):
        run=ROOT/'runs'/name
        if (run/'pipeline-status.json').exists() or name in processes:return
        dependencies = manifest['experiments'][name].get('start_after_completed', [])
        if any(read_json(ROOT/'runs'/dep/'pipeline-status.json', {}).get('status') != 'completed'
               for dep in dependencies):
            return
        with (STATE/f'{name}-launcher.log').open('a') as log:
            processes[name]=subprocess.Popen([sys.executable,'-m','scripts.run_reference_experiment',
                '--manifest','experiment_suite.json','--name',name],cwd=ROOT,env=env,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)

    def ready(dataset):
        rows=[read_json(STATE/'data'/dataset/f'{i:03d}/status.json',{}) for i in range(35)]
        for i,row in enumerate(rows):
            if row.get('status')=='completed' and 'evaluation_unique' not in row['counts']:
                from scripts.run_official_dataset import prepare_evaluation_cache
                hand='sharpa' if dataset=='knife_sharpa_official' else 'wuji'
                cache=ROOT/'caches/initial_grasp'/hand/dataset/f'{i:03d}'
                row['counts']['evaluation_unique']=prepare_evaluation_cache(cache,22 if hand=='sharpa' else 20)
                atomic_json(STATE/'data'/dataset/f'{i:03d}/status.json',row)
        return len(rows)==35 and all(x.get('status')=='completed' for x in rows),rows

    next_monitor=0
    while True:
        # Scheduling can be adjusted without interrupting running teachers/workers.
        manifest=read_json(ROOT/'experiment_suite.json')
        errors=[]
        for key,process in list(dataset_jobs.items()):
            if process.poll() is not None:del dataset_jobs[key]
        sharpa_ready,sharpa=ready('knife_sharpa_official')
        wuji_ready,wuji=ready('knife_wuji_official')
        if training_ready(sharpa):
            atomic_json(STATE/'sharpa-train-ready.json',dict(train_objects=30,
                train_grasps=sum(x['counts']['train'] for x in sharpa[:30]),objects=sharpa[:30],evaluation_gate_separate=True))
            for name in TRAINING_ARMS:launch_reference(name)
        if sharpa_ready:
            atomic_json(STATE/'sharpa-ready.json',dict(train_objects=30,heldout_objects=5,
                train_grasps=sum(x['counts']['train'] for x in sharpa[:30]),
                heldout_grasps=sum(x['counts']['evaluation_unique'] for x in sharpa[30:]),
                heldout_raw_grasps=sum(x['counts']['valid'] for x in sharpa[30:]),objects=sharpa))
        if wuji_ready:
            atomic_json(STATE/'wuji-official-ready.json',dict(train_objects=30,heldout_objects=5,objects=wuji))
        for name in manifest.get('additional_transfer_arms',[]):
            launch_reference(name)
        busy={key[0] for key in dataset_jobs}
        active={(key[1],key[2]) for key in dataset_jobs}
        for other_dataset,other_rows in [('knife_sharpa_official',sharpa),('knife_wuji_official',wuji)]:
            for i,row in enumerate(other_rows):
                if row.get('status') not in ('generating','validating'):continue
                pid_path=STATE/'data'/other_dataset/f'{i:03d}/worker.pid'
                pid=int(pid_path.read_text()) if pid_path.exists() else None
                command=Path(f'/proc/{pid}/cmdline').read_bytes().decode(errors='replace') if pid_alive(pid) else ''
                if 'run_dataset_with_pid' in command and other_dataset in command:
                    busy.add(row['gpu'])
                    active.add((other_dataset,f'{i:03d}'))
                else:
                    errors.append(dict(dataset=other_dataset,instance=f'{i:03d}',error='Worker exited before publishing final status'))
        training={name:read_json(ROOT/'runs'/name/'pipeline-status.json',{'status':'waiting_for_data'}) for name in manifest['experiments']}
        pending=[job for job in pending_data(sharpa,wuji) if (job[0],job[2]) not in active]
        available=[]
        if pending and not manifest.get('scheduling',{}).get('pause_new_data_jobs',False) and Path('/tmp/artgym-lygra-runtime/.artgym-verified').exists():
            output=subprocess.check_output(['nvidia-smi','--query-gpu=index,memory.free','--format=csv,noheader,nounits'],text=True,timeout=10)
            memory={int(line.split(',')[0]):float(line.split(',')[1]) for line in output.strip().splitlines()}
            available=choose_data_gpus(manifest.get('scheduling',{}),busy,memory,training)
        for gpu in available:
            if gpu in busy or not pending:continue
            dataset,robot,instance=pending.pop(0)
            path=STATE/'data'/dataset/instance;path.mkdir(parents=True,exist_ok=True)
            with (path/'worker.log').open('a') as log:
                process=subprocess.Popen([sys.executable,'-m','scripts.run_dataset_with_pid',
                     '--dataset',dataset,'--robot',robot,'--instance',instance,'--gpu',str(gpu)],
                     cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                     start_new_session=True)
            dataset_jobs[(gpu,dataset,instance)]=process
        for dataset,rows in [('sharpa',sharpa),('wuji',wuji)]:
            for row in rows:
                if row.get('status')=='failed':errors.append(dict(dataset=dataset,instance=row['instance'],error=row['error']))
        if time.monotonic()>=next_monitor:
            subprocess.run([sys.executable,'scripts/monitor_wuji_checkpoints.py','--config','experiment_monitor.json','--ensure'],
                           cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
            subprocess.run([sys.executable,'-m','scripts.monitor_gpu_utilization','--ensure'],
                           cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
            if manifest.get('additional_transfer_arms'):
                for monitor in manifest.get('additional_transfer_monitors',['wuji_augmentation_monitor.json']):
                    subprocess.run([sys.executable,'scripts/monitor_wuji_checkpoints.py','--config',monitor,'--ensure'],
                        cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
            next_monitor=time.monotonic()+300
        training={name:read_json(ROOT/'runs'/name/'pipeline-status.json',{'status':'waiting_for_data'}) for name in manifest['experiments']}
        for name,row in training.items():
            if row['status']=='failed':errors.append(dict(experiment=name,error='Training/preflight failed; inspect run logs'))
        workers=[]
        for label,rows in [('knife_sharpa_official',sharpa),('knife_wuji_official',wuji)]:
            for i,row in enumerate(rows):
                if row.get('status') not in ('generating','validating'):continue
                path=STATE/'data'/label/f'{i:03d}'
                pid_path=path/'worker.pid'
                worker=dict(gpu=row['gpu'],dataset=label,instance=f'{i:03d}',status=row['status'],
                    pid=int(pid_path.read_text()) if pid_path.exists() else None)
                log=path/'generation.log'
                if log.exists():
                    with log.open('rb') as stream:
                        stream.seek(0,2);stream.seek(max(0,stream.tell()-65536))
                        counts=re.findall(rb'Number of Solutions: (\d+)',stream.read())
                    if counts:worker['accepted_candidates']=int(counts[-1])
                workers.append(worker)
        atomic_json(STATE/'status.json',dict(pid=os.getpid(),heartbeat=now(),datasets={
            'sharpa':dict(completed=sum(x.get('status')=='completed' for x in sharpa),total=35),
            'wuji':dict(completed=sum(x.get('status')=='completed' for x in wuji),total=35)},
            data_workers=workers,
            utilization=read_json(ROOT/'runs/gpu-utilization/status.json',{}),
            experiments={k:{'status':v['status'],'stages':v.get('stages',[])} for k,v in training.items()},errors=errors))
        time.sleep(5)


if __name__=='__main__':main()
