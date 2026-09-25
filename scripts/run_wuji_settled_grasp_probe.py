"""Generate new settled candidates, then restart them in independent physics."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gpu',type=int,default=5)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    p=args.output.resolve();p.mkdir(parents=True,exist_ok=True)
    assert not (p/'status.json').exists()
    state=dict(status='running',started=now(),stages=[],gpu=args.gpu,scope=__doc__)
    atomic_json(p/'status.json',state)
    environment=runtime_environment(dict(project=str(root),python=sys.executable),args.gpu)

    def run(name,arguments):
        with (p/(name+'.log')).open('w') as log:
            child=subprocess.Popen([sys.executable]+arguments,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT)
        row=dict(name=name,status='running',pid=child.pid,started=now(),command=arguments)
        state['stages'].append(row);atomic_json(p/'status.json',state)
        try:code=child.wait(timeout=1800)
        except subprocess.TimeoutExpired:child.kill();child.wait();code=124
        row.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
        atomic_json(p/'status.json',state)
        return code

    candidates=p/'candidates'
    try:
        assert run('prepare',['-m','scripts.prepare_wuji_settled_grasps',
            '--selection',str(root/'runs/wuji-goal/diagnostics/multigrasp-spring-preload-v2-correct-geometry/selection.json'),
            '--output',str(candidates)])==0
        code=run('restart_static',['-m','scripts.audit_wuji_static_grasp','--task','wuji_acquisition_official_support40mrad',
            '--hand','wuji_paper_official_actuator','--object','knife_wuji_fingertip_precision000',
            '--initial-states',str(candidates/'initial_states.npy'),'--output',str(candidates/'static')])
        if code:
            state.update(status='failed',finished=now(),error='Static audit did not complete; retain original failure and inspect before any follow-up.')
            atomic_json(p/'status.json',state);raise SystemExit(code)
        report=json.loads((candidates/'static/report.json').read_text())
        manifest=json.loads((candidates/'manifest.json').read_text())
        counts={}
        for split,denominator in [('train',33),('test',5)]:
            source_rows=[v for v in manifest['records'] if v['split']==split]
            restarted=[v for v in source_rows if v['restarted']]
            count=dict(source_count=denominator,restarted=len(restarted),stable20s=0,posture_closed_reachable_stable20s=0)
            for row in restarted:
                metric=report['records'][row['candidate_row']]
                count['stable20s']+=int(metric['stable20s'])
                count['posture_closed_reachable_stable20s']+=int(metric['stable20s'] and row['posture_pass']
                    and row['slider_closed'] and row['thumb_reach']['passed'])
            counts[split]=count
        state.update(status='completed',finished=now(),counts=counts,
            interpretation='New settled initial states, not an improved score for the original grasps. Semantic pad/body contacts still need verification before training.')
        atomic_json(p/'status.json',state)
        print(json.dumps(state),flush=True)
    except Exception as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        atomic_json(p/'status.json',state)
        raise


if __name__=='__main__':main()
