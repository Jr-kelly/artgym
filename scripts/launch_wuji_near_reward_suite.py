"""Schedule the near-reward pair after physical gates and fresh-grasp checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now


def main():
    root=Path(__file__).resolve().parents[1];base=root/'runs/wuji-goal'
    status=base/'near-reward-training-launch.json'
    assert not status.exists()
    state=dict(status='waiting_for_gates_and_generation',started=now(),records=[])
    atomic_json(status,state)
    waiting=[base/'diagnostics'/('near-reward-'+v)/'status.json' for v in ['0.1','5.0']]
    waiting += [base/'diagnostics'/('fresh-lowgain-functional-generation-seed'+v)/'independent-quality/status.json' for v in ['19','20']]
    try:
        deadline=time.monotonic()+7200
        while time.monotonic()<deadline:
            checks={str(p.relative_to(root)):json.loads(p.read_text()).get('status') if p.exists() else 'missing' for p in waiting}
            if any(v=='failed' for v in checks.values()):raise RuntimeError(str(checks))
            if all(v in ['completed','completed_no_valid_candidates'] for v in checks.values()):break
            state['waiting']=checks;atomic_json(status,state);time.sleep(30)
        else:raise TimeoutError('Gates did not finish within two hours')
        commands=[]
        for name,gpu in [('wuji_variable_nearreward01_seed23_v1',1),('wuji_variable_nearreward5_seed23_v1',3)]:
            commands.append((name,['-m','scripts.run_reference_experiment','--manifest','wuji_near_reward_suite.json','--name',name]))
            commands.append((name+'-audits',['-m','scripts.run_wuji_goal_audits','--queue','runs/wuji-goal/audit-queue-'+name+'.json',
                '--gpu',str(gpu),'--checkpoint-wait-seconds','21600']))
        commands.append(('near-reward-monitor',['-m','scripts.monitor_wuji_checkpoints','--config','wuji_near_reward_monitor.json']))
        for name,command in commands:
            with (base/(name+'-launch.log')).open('w') as log:
                child=subprocess.Popen([sys.executable]+command,cwd=root,env=dict(os.environ,PYTHONPATH=str(root)),
                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            state['records'].append(dict(name=name,pid=child.pid,command=command))
        state.update(status='launched',finished=now());atomic_json(status,state)
    except Exception as exc:
        state.update(status='failed',error=repr(exc),finished=now());atomic_json(status,state);raise


if __name__=='__main__':main()
