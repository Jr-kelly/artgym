"""Gate mixed-data RGB fitting on an executed short fit and independent audit."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment
from scripts.evaluation_gpu_lease import acquire_evaluation_gpu


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting_for_gpu',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state);lease=None;child=None
    try:
        while lease is None:
            lease=acquire_evaluation_gpu(spec['gpu'])
            if lease is None:time.sleep(5)
        used=int(subprocess.check_output(['nvidia-smi','-i',str(spec['gpu']),'--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip())
        assert used<1000,(spec['gpu'],used)
        env=runtime_environment(dict(project=str(pin),python=sys.executable),spec['gpu'])
        for mode,updates in [('runtime',2),('fitting',5000)]:
            command=[sys.executable,'-m','scripts.fit_wuji_rgb_state_pair','--data-spec',str(root/spec['data_spec']),
                '--output',str(out/mode),'--updates',str(updates),'--seed',str(spec['seed'])]
            if mode=='runtime':command+=['--runtime-check']
            audit=[sys.executable,'-m','scripts.audit_wuji_rgb_mixed_fit','--fitting',str(out/mode),
                '--root',str(root),'--output',str(out/(mode+'-independent-audit.json'))]
            for name,cmd in [(mode,command),(mode+'-audit',audit)]:
                with (out/(name+'.log')).open('w') as f:
                    child=subprocess.Popen(cmd,cwd=pin,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,pass_fds=(lease.fileno(),))
                row=dict(name=name,pid=child.pid,command=cmd,status='running',started=now());state['stages'].append(row)
                state['status']=name;atomic_json(out/'status.json',state)
                code=child.wait();row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
                atomic_json(out/'status.json',state);assert code==0,row
            audit_result=json.loads((out/(mode+'-independent-audit.json')).read_text())
            assert audit_result['status']=='passed' and audit_result['original_initial_weights_matched']
        state.update(status='completed',finished=now(),task_success_claim=False)
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        if child and child.poll() is None:child.terminate();child.wait(timeout=20)
        raise
    finally:
        atomic_json(out/'status.json',state)
        if lease:lease.close()


if __name__=='__main__':main()
