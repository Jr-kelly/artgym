"""Build and run a finite dynamic evaluation queue on actual verified idle GPUs."""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from scripts.wuji_width_contract import ROUND, sha, canonical_hash
from scripts.wuji_width_jobs import source_hash
from scripts.record_wuji_width_goal import R, D, record
from scripts.host_tool_environment import host_tool_environment


def build(a):
    state=json.loads((D/'STATE.json').read_text())
    assert a.phase in ('dev','confirm','final')
    if a.phase=='final':assert state.get('candidate_frozen')
    assets=json.loads((D/'ASSETS.json').read_text());tasks=[]
    labels=['baseline','W110','W120']+(['W115','W115_T110'] if a.phase=='final' else [])
    models=[]
    for spec in a.models:
        role,name=spec.split('=',1);path=R/name;digest=sha(path)
        if role!='teacher' and digest!='16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9':
            ready=json.loads(path.with_suffix('.ready.json').read_text());assert ready['sha256']==digest
        models.append((role,name,digest))
    for label in labels:
        directory=R/'runs'/ROUND/'static'/(label+'-'+a.phase)
        states=directory/'valid-states.npy';selection=directory/'selection.json'
        selected=json.loads(selection.read_text());assert selected['no_policy_filter']
        if not selected['selected_attempt_rows']:continue
        for role,path,digest in models:
            for protocol in ['F','S2','S5']:
                identity=dict(model_sha256=digest,source_sha256=source_hash(R),asset_sha256=canonical_hash(assets[label]),
                    states_sha256=sha(states),selection_sha256=sha(selection),protocol=protocol,shard='all-registered-rows',
                    batch_n=len(selected['selected_attempt_rows']))
                key=canonical_hash(identity);name=a.phase+'-'+label+'-'+role+'-'+protocol+'-'+key[:12]
                output='runs/'+ROUND+'/eval/'+name
                command=['PYTHON','-m','scripts.evaluate_wuji_geometry','--research-dir','research/'+ROUND,
                    '--label',label,'--states',str(states.relative_to(R)),'--model','teacher' if role=='teacher' else 'student',
                    '--protocol',protocol,'--output',output]
                if role!='teacher':command+=['--student-checkpoint',path]
                tasks.append(dict(key=key,name=name,role=role,geometry=label,phase=a.phase,identity=identity,
                                  command=command,output=output,selection=str(selection.relative_to(R)),seconds=a.seconds,status='pending'))
    assert tasks
    a.output.parent.mkdir(parents=True,exist_ok=True)
    assert not a.output.exists(), 'Queue is immutable; resume it rather than regenerate'
    a.output.write_text(json.dumps(dict(round=ROUND,historical_final_access=False,tasks=tasks),indent=2)+'\n')
    record('finite_evaluation_queue_registered',evidence=str(a.output),task_count=len(tasks),queue_phase=a.phase,
           next='Dynamically claim ready tasks on verified idleH200; checkpoint and source hashes must match')


def run(a):
    state=json.loads((D/'STATE.json').read_text());assert state['remote_inventory_verified']
    assert not state['remote_additional_consumption_unknown']
    ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV']);assert 'wangjiarui@10.13.160.5' in ssh and '33024' in ssh
    inventory=subprocess.check_output(ssh+['nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader,nounits'],text=True,timeout=25,env=host_tool_environment())
    devices={int(r.split(',')[0]):r.split(',') for r in inventory.strip().splitlines()}
    assert len(a.gpus)<=8 and len(set(a.gpus))==len(a.gpus)
    assert all(g in devices and 'H200' in devices[g][1] and int(devices[g][2])<100 for g in a.gpus)
    with a.queue.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        queue=json.loads(a.queue.read_text());assert queue['round']==ROUND
        assert not any(t['status']=='running' for t in queue['tasks']), 'Reconcile recorded jobs before recovery; never duplicate'
        active={};pending=[t for t in queue['tasks'] if t['status']=='pending']
        def save():
            tmp=a.queue.with_suffix('.tmp');tmp.write_text(json.dumps(queue,indent=2)+'\n');tmp.replace(a.queue)
        while pending or active:
            for gpu in a.gpus:
                if gpu in active or not pending:continue
                task=pending.pop(0)
                assert task['identity']['source_sha256']==source_hash(R), 'Source changed; retain queue and preregister a new version'
                command=[sys.executable,'-m','scripts.wuji_width_jobs','--gpu',str(gpu),'--seconds',str(task['seconds'])]
                if task['phase']!='dev':command+=['--reserved-phase',task['phase']]
                command += [task['name'],'--',*task['command']]
                child=subprocess.Popen(command,cwd=R);task.update(status='running',controller_pid=child.pid,gpu=gpu)
                active[gpu]=(child,task);save()
            for gpu,(child,task) in list(active.items()):
                code=child.poll()
                if code is not None:
                    task.update(status='complete' if code==0 else 'failed',exit_code=code);del active[gpu];save()
            if active:time.sleep(3)
        record('finite_evaluation_queue_finished',evidence=str(a.queue),completed=sum(t['status']=='complete' for t in queue['tasks']),
               failed=sum(t['status']=='failed' for t in queue['tasks']),next='Audit coverage and independently rescore; no retry or next training window without evidence')


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    b=sub.add_parser('build');b.add_argument('--phase',choices=['dev','confirm','final'],required=True)
    b.add_argument('--models',nargs='+',required=True);b.add_argument('--output',type=Path,required=True);b.add_argument('--seconds',type=int,default=900)
    r=sub.add_parser('run');r.add_argument('--queue',type=Path,required=True);r.add_argument('--gpus',type=int,nargs='+',required=True)
    a=p.parse_args();build(a) if a.mode=='build' else run(a)


if __name__=='__main__':main()
