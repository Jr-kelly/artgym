"""Finite registered second optimization stream; independent jobs, no agents."""
import json, os, shlex, subprocess, sys, time
from pathlib import Path
from scripts.record_wuji_width_goal import R,D,record
from scripts.wuji_width_jobs import host_tool_environment

def run():
    ssh=json.loads(os.environ['WUJI_WIDTH_SSH_ARGV'])
    assert json.loads((D/'FORMAL_REPEAT_REGISTRATION.json').read_text())['new_optimization_seed']==2026100216
    deadline=time.monotonic()+6000
    endpoint=D/'queues/fixed-endpoint-confirm-v1.json'
    while True:
        q=json.loads(endpoint.read_text())
        assert not any(t['status']=='failed' for t in q['tasks'])
        if all(t['status']=='complete' for t in q['tasks']):break
        assert time.monotonic()<deadline
        time.sleep(5)
    children=[]
    for gpu,arm in enumerate(['C','G']):
        name=arm+'2-window1-h200-17314'
        cmd=json.loads((R/'runs/width-student-distillation-20261002/jobs'/ (arm+'1-window1-h200-17314')/'identity.json').read_text())['command']
        cmd[0]='PYTHON'
        cmd[cmd.index('--output')+1]='runs/width-student-distillation-20261002/'+name
        for flag in ['--seed','--fresh-optimization-seed']:cmd[cmd.index(flag)+1]='2026100216'
        log=(D/(name+'-controller.log')).open('a')
        child=subprocess.Popen([sys.executable,'-m','scripts.wuji_width_jobs','--gpu',str(gpu),'--seconds','3000',name,'--',*cmd],cwd=R,stdout=log,stderr=subprocess.STDOUT)
        children.append(child)
        record('second_pair_arm_started',evidence='research/width-student-distillation-20261002/FORMAL_REPEAT_REGISTRATION.json',arm=arm+'2',controller_pid=child.pid,gpu=gpu,state_updates=dict(second_pair_training_started=True),next='Read only atomic checkpoints; matched seed and full3200 endpoint')
    for step in [52000,52800,54400]:
        paths=['runs/width-student-distillation-20261002/'+arm+'2-window1-h200-17314' for arm in ['C','G']]
        while True:
            check=' && '.join('test -f '+shlex.quote('/tmp/artgym-width-20261002/'+p+'/step_%06d.ready.json'%step) for p in paths)
            ready=subprocess.run(ssh+[check],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=host_tool_environment(),timeout=25).returncode==0
            if ready:break
            assert time.monotonic()<deadline and all(c.poll() in [None,0] for c in children)
            time.sleep(10)
        remote=['wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/./'+p+'/step_%06d'%step+suffix for p in paths for suffix in ['.pth','.ready.json']]
        subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*remote,str(R)+'/'],check=True,env=host_tool_environment(),timeout=180)
        queue=D/'queues'/('repeat-step%d-dev-v1.json'%step)
        subprocess.run([sys.executable,'-m','scripts.wuji_width_queue','build','--phase','dev','--seconds','600','--models',* [arm+'='+p+'/step_%06d.pth'%step for arm,p in zip(['C','G'],paths)],'--output',str(queue)],cwd=R,check=True)
        log=(D/('repeat-step%d-dev-controller.log'%step)).open('a')
        subprocess.run([sys.executable,'-m','scripts.wuji_width_queue','run','--queue',str(queue),'--gpus','2','3','4','5','6'],cwd=R,stdout=log,stderr=subprocess.STDOUT,check=True)
        assert all(t['status']=='complete' for t in json.loads(queue.read_text())['tasks'])
    for c in children:assert c.wait(timeout=60)==0
    remote=['wangjiarui@10.13.160.5:/tmp/artgym-width-20261002/./'+p for p in paths]
    subprocess.run(['rsync','-aR','-e',shlex.join(ssh[:-1]),*remote,str(R)+'/'],check=True,env=host_tool_environment(),timeout=180)
    record('registered_second_pair_and_all_dev_complete',evidence='research/width-student-distillation-20261002/FORMAL_REPEAT_REGISTRATION.json',state_updates=dict(second_pair_training_complete=True,formal_saved_updates_by_arm=dict(C1=3200,G1=3200,C2=3200,G2=3200),optimizer_updates=12800),next='Independently rescore repeat; no further training; freeze firstpair confirmed candidates for final')

if __name__=='__main__':
    try:run()
    except Exception as e:
        record('registered_repeat_controller_failure',failure_type=type(e).__name__,next='Inspect own receipts; preserve successful checkpoints and finish other authorized work')
        raise
