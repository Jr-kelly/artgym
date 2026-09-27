"""Frozen twenty-placement validation, gated on actual continuous success.

Does not choose/tune controllers on the validation set. Reuses the exact
successful source pin and weights; all acquisition/planning failures remain.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/g2-local-policy-20260928'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value(command,flag,default=None):
    return command[command.index(flag)+1] if flag in command else default


def put(command,flag,new):
    if flag in command:command[command.index(flag)+1]=str(new)
    else:command.extend([flag,str(new)])


def alive(record):
    try:
        cmd=Path('/proc/%d/cmdline'%record['pid']).read_bytes().replace(b'\0',b' ')
        return value(record['command'],'--output').encode() in cmd and b'scripts.run_g2_tabletop' in cmd
    except FileNotFoundError:return False


def declare(args):
    assert not args.manifest.exists()
    launch=json.loads(args.base_launch.read_text());folder=Path(value(launch['command'],'--output'))
    report=json.loads((folder/'report.json').read_text())
    assert report['required_task_success'] and report['operation_steps']==600
    assert report.get('learned_preparation_hold_success',True)
    audit=json.loads(args.audit.read_text())
    assert audit['independent_whole_success'] and audit['state_reset_after_start']==False
    assert audit['prefix_verified'] and audit['input_command_parity_verified']
    budget=json.loads(args.budget.read_text())
    assert not budget['budget_exceeded']
    rng=random.Random(args.seed);columns=[]
    for bound in [.005,.005,2.]:
        values=[(2*(i+rng.random())/20-1)*bound for i in range(20)]
        rng.shuffle(values);columns.append(values)
    trials=[dict(name=args.manifest.stem+'-%02d'%i,placement=i,dx_m=x,dy_m=y,yaw_deg=yaw)
            for i,(x,y,yaw) in enumerate(zip(*columns))]
    command=launch['command'];inputs={}
    for flag in ['--learned-hold-policy','--learned-operation-policy','--teacher']:
        path=value(command,flag)
        if path:inputs[path]=sha(path)
    pin=Path(launch['cwd'])
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        seed=args.seed,source_pin=str(pin),source_manifest_sha256=sha(pin/'source-hashes.json'),
        base_launch=str(args.base_launch),base_command=command,base_report_sha256=sha(folder/'report.json'),
        independent_audit=str(args.audit),independent_audit_sha256=sha(args.audit),
        input_sha256=inputs,trials=trials,
        method='frozen privileged learned H/S composite; not unchanged original teacher or deployable student',
        interpretation='20 new geometric placements, one attempt each. Placement known to planner; not perception robustness. No controller tuning or failed-run reruns.',
        criteria=dict(seconds=20,reversal_seconds=5,endpoint_last_seconds=.3,endpoint_max_m=.01,
            strict_endpoint_m=.002,world_translation_m=.01,world_rotation_rad=.25,
            reference='fixed at actual operation takeover; hold preparation independently scored'),
        budget_anchor=budget,delivery_start_utc=json.loads((RUN/'state.json').read_text())['delivery_start_utc'])
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(manifest=str(args.manifest),sha256=sha(args.manifest),placements=20)))


def status(manifest):
    rows=[]
    for case in manifest['trials']:
        folder=RUN/case['name'];launch=RUN/(case['name']+'-launch.json');row=dict(case)
        if launch.exists() and alive(json.loads(launch.read_text())):
            row['status']='running'
        elif (folder/'report.json').exists():
            r=json.loads((folder/'report.json').read_text())
            row.update(status='finished',grasp_success=r['grasp_success'],operation_entered=r['operation_steps']>0,
                operation_success=r.get('operation_window_success',r.get('required_task_success',False)),
                whole_success=r.get('required_task_success',False),hold_success=r.get('learned_preparation_hold_success'),
                endpoints=r.get('endpoints'),strict_2mm=r.get('strict_2mm'),
                world_drift_m=r.get('world_drift_max_m'),world_rotation_rad=r.get('world_rotation_max_rad'),
                slider_travel_m=r.get('slider_travel_m'),physical_drop=r.get('physical_drop_detected'),
                failure=r.get('failure_class'))
        elif launch.exists():
            failure=folder/'failure.json'
            detail=json.loads(failure.read_text()) if failure.exists() else {}
            takeover=folder/'takeover.json'
            acquired=bool(json.loads(takeover.read_text()).get('grasp_success')) if takeover.exists() else False
            row.update(status='failed',grasp_success=acquired,operation_entered=detail.get('last_phase')=='operate',operation_success=False,
                whole_success=False,failure=detail or 'preflight/initialization or interruption; retained log')
        else:row['status']='pending'
        rows.append(row)
    return rows


def execute(args):
    manifest=json.loads(args.manifest.read_text());pin=Path(manifest['source_pin'])
    assert sha(pin/'source-hashes.json')==manifest['source_manifest_sha256']
    for path,digest in manifest['input_sha256'].items():assert sha(path)==digest,path
    # Preregistration must be committed AND pushed before any validation launch.
    relative=str(args.manifest.resolve().relative_to(ROOT))
    committed=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
    assert committed==args.manifest.read_bytes()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['gh','api','repos/Jr-kelly/artgym/commits/'+head,'--jq','.sha'],cwd='/home/agiuser',text=True).strip()
    assert remote==head
    results=args.manifest.with_name(args.manifest.stem+'-results.json')
    driver=RUN/(args.manifest.stem+'-driver.json')
    if driver.exists():
        old=json.loads(driver.read_text());proc=Path('/proc/%d/cmdline'%old['pid'])
        if proc.exists() and b'scripts.run_g2_local_validation' in proc.read_bytes():
            raise RuntimeError('Another validation driver is still active')
    driver.write_text(json.dumps(dict(pid=os.getpid(),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                     preregistration_commit=head,manifest_sha256=sha(args.manifest)),indent=2)+'\n')
    stopped=False
    stop_signals={}
    while True:
        now=datetime.datetime.now(datetime.timezone.utc)
        anchor=manifest['budget_anchor']
        # Conservative upper bound: count every elapsed wall second since the
        # verified one-GPU interval audit, even any idle periods.
        charged=anchor['charged_gpu_hours']+(now-datetime.datetime.fromisoformat(anchor['checked_utc'])).total_seconds()/3600
        stop=charged>=12 or now>=datetime.datetime.fromisoformat(manifest['delivery_start_utc'])
        rows=status(manifest);running=sum(r['status']=='running' for r in rows)
        if stop:
            stopped=True
            for row in rows:
                if row['status']=='running':
                    record=json.loads((RUN/(row['name']+'-launch.json')).read_text())
                    pid=record['pid']
                    if alive(record) and pid not in stop_signals:
                        os.kill(pid,signal.SIGINT);stop_signals[pid]=time.monotonic()
                    elif alive(record) and time.monotonic()-stop_signals.get(pid,time.monotonic())>120:
                        os.kill(pid,signal.SIGTERM)
        for row in rows:
            if stopped or running>=args.concurrency:break
            if row['status']!='pending':continue
            command=manifest['base_command'].copy()
            for flag,delta in [('--dx',row['dx_m']),('--dy',row['dy_m']),('--yaw',row['yaw_deg'])]:
                put(command,flag,float(value(command,flag,0))+delta)
            put(command,'--output',RUN/row['name'])
            env=os.environ.copy();env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:'+env['PATH'],
                LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH=str(pin)+':'+str(pin/'rl_games'),
                OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
            log=RUN/(row['name']+'.log')
            with log.open('x') as stream:
                child=subprocess.Popen(command,cwd=pin,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            record=dict(pid=child.pid,utc=now.isoformat(),command=command,cwd=str(pin),source_version=pin.name,
                module='scripts.run_g2_tabletop',log=str(log),scope='preregistered frozen validation; same one local GPU')
            (RUN/(row['name']+'-launch.json')).write_text(json.dumps(record,indent=2)+'\n');running+=1
        rows=status(manifest)
        finished=[r for r in rows if r['status'] in ['finished','failed']]
        picked=[r for r in finished if r.get('grasp_success')]
        out=dict(updated_utc=now.isoformat(),manifest_sha256=sha(args.manifest),planned=20,finished=len(finished),
            acquisition_successes=len(picked),conditional_operation_successes=sum(r.get('operation_success',False) for r in picked),
            whole_successes=sum(r.get('whole_success',False) for r in finished),trials=rows,
            stopped_by_budget=stopped,charged_gpu_hours_upper_bound=charged,
            all_finished=len(finished)==20,denominator='All started trials, including planning/acquisition failures; unstarted cases reported separately')
        temporary=results.with_suffix('.tmp');temporary.write_text(json.dumps(out,indent=2)+'\n');temporary.replace(results)
        if out['all_finished'] or (stopped and not any(r['status']=='running' for r in rows)):
            print(json.dumps({k:v for k,v in out.items() if k!='trials'}));return
        time.sleep(5)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['declare','run'])
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--base-launch',type=Path)
    p.add_argument('--audit',type=Path)
    p.add_argument('--budget',type=Path)
    p.add_argument('--seed',type=int,default=2026092801)
    p.add_argument('--concurrency',type=int,choices=[1,2],default=2)
    a=p.parse_args();(declare if a.mode=='declare' else execute)(a)


if __name__=='__main__':main()
