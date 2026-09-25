"""Launch and record isolated acquisition comparisons on the four-H100 host."""
import argparse,fcntl,json,os,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runs/wuji-goal'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true');args=parser.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    student=None
    student_state=ROOT/'runs/wuji_student_precision_v1/pipeline-status.json'
    if args.ensure and student_state.exists():
        result=subprocess.run([sys.executable,'-m','scripts.run_wuji_student_acquisition','--ensure'],
            cwd=ROOT,capture_output=True,text=True,timeout=20)
        try:student=json.loads(result.stdout)
        except ValueError:student={'error':result.stderr[-2000:],'returncode':result.returncode}
    lock=(STATE/'acquisition-suite.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        if args.ensure:
            state=json.loads((STATE/'acquisition-status.json').read_text());state['student']=student
            print(json.dumps(state))
        return
    if args.ensure:
        fcntl.flock(lock,fcntl.LOCK_UN)
        with (STATE/'acquisition-suite.log').open('a') as log:
            child=subprocess.Popen([sys.executable,'-m','scripts.run_wuji_acquisition_suite'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print(json.dumps(dict(starting_pid=child.pid)));return
    manifest=json.loads((ROOT/'wuji_acquisition_suite.json').read_text())
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable));children={}
    while True:
        manifest=json.loads((ROOT/'wuji_acquisition_suite.json').read_text())
        for name,spec in manifest['experiments'].items():
            if (ROOT/'runs'/name/'pipeline-status.json').exists() or name in children:continue
            dependencies=spec.get('start_after_completed',[])
            def completed(dependency):
                path=ROOT/'runs'/dependency/'pipeline-status.json'
                return path.exists() and json.loads(path.read_text()).get('status')=='completed'
            if not all(completed(dependency) for dependency in dependencies):continue
            with (STATE/(name+'-launcher.log')).open('a') as log:
                children[name]=subprocess.Popen([sys.executable,'-m','scripts.run_reference_experiment',
                    '--manifest','wuji_acquisition_suite.json','--name',name],env=env,cwd=ROOT,
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        subprocess.run([sys.executable,'scripts/monitor_wuji_checkpoints.py','--config',
            'wuji_acquisition_monitor.json','--ensure'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
        if (ROOT/'wuji_multicycle_monitor.json').exists():
            subprocess.run([sys.executable,'scripts/monitor_wuji_checkpoints.py','--config',
                'wuji_multicycle_monitor.json','--ensure'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
        for monitor in manifest.get('additional_monitors',[]):
            subprocess.run([sys.executable,'scripts/monitor_wuji_checkpoints.py','--config',
                monitor,'--ensure'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
        subprocess.run([sys.executable,'-m','scripts.monitor_gpu_utilization','--state-dir',
            'runs/gpu-utilization-four','--ensure'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,timeout=30)
        states={}
        for name in manifest['experiments']:
            p=ROOT/'runs'/name/'pipeline-status.json'
            states[name]=json.loads(p.read_text()).get('status') if p.exists() else 'starting'
        health={}
        for label,path in [('utilization',ROOT/'runs/gpu-utilization-four/status.json'),
                           ('checkpoints',STATE/'checkpoint-monitor-four/status.json'),
                           ('multicycle_checkpoints',STATE/'multicycle-monitor-four/status.json')]:
            try:health[label]=json.loads(path.read_text())
            except (OSError,ValueError):health[label]={'error':'Status unavailable'}
        atomic_json(STATE/'acquisition-status.json',dict(pid=os.getpid(),heartbeat=now(),experiments=states,**health))
        time.sleep(30)


if __name__=='__main__':main()
