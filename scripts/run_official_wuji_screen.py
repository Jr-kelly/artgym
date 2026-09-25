"""Recorded bounded CPU reach queue followed by one physical worker per host."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,os,subprocess,sys
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/wuji-goal/official-screen'
CACHE=ROOT/'caches/initial_grasp/wuji/knife_wuji_official_approved'


def run(stage,instance):
    out=STATE/instance;out.mkdir(parents=True,exist_ok=True)
    output=CACHE/instance/('screening.json' if stage=='screen' else 'filter_validation.json')
    if output.exists():return json.loads(output.read_text())
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable),2)
    cmd=[sys.executable,'-m','scripts.filter_official_wuji_transfer',stage,'--instance',instance]
    record=dict(status='running',started=now(),command=cmd)
    with (out/(stage+'.log')).open('w') as log:
        child=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        record['pid']=child.pid;atomic_json(out/(stage+'-status.json'),record)
        try:code=child.wait(timeout=1800)
        except subprocess.TimeoutExpired:child.kill();child.wait();code=124
    record.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
    atomic_json(out/(stage+'-status.json'),record)
    if code:raise RuntimeError(stage+' failed for '+instance)
    return json.loads(output.read_text())


def main():
    STATE.mkdir(parents=True,exist_ok=True);instances=[f'{i:03d}' for i in range(35)]
    status=dict(pid=os.getpid(),status='screening',started=now(),completed=[],failed={})
    atomic_json(STATE/'status.json',status)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(run,'screen',i):i for i in instances}
        for f in as_completed(futures):
            i=futures[f]
            try:f.result();status['completed'].append(i)
            except Exception as error:status['failed'][i]=repr(error)
            status['heartbeat']=now();atomic_json(STATE/'status.json',status)
    status['status']='physical';status['physical_completed']=[];atomic_json(STATE/'status.json',status)
    for i in instances:
        if i in status['failed']:continue
        try:run('physical',i);status['physical_completed'].append(i)
        except Exception as error:status['failed'][i]=repr(error)
        status['heartbeat']=now();atomic_json(STATE/'status.json',status)
    reports=[json.loads((CACHE/i/'filter_validation.json').read_text()) for i in status['physical_completed']]
    status.update(status='completed' if not status['failed'] else 'completed_with_failures',finished=now(),
        valid=sum(r['valid'] for r in reports),train=sum(r['train'] for r in reports if int(r['instance'])<30),
        test_on_train_geometry=sum(r['test'] for r in reports if int(r['instance'])<30),
        heldout_geometry=sum(r['valid'] for r in reports if int(r['instance'])>=30))
    atomic_json(STATE/'status.json',status)


if __name__=='__main__':main()
