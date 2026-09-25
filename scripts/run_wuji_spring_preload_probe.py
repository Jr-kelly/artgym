"""Bounded training-only static target probe and separately frozen validation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',type=int,default=5)
    parser.add_argument('--output-root',type=Path,default=ROOT/'runs/wuji-goal/diagnostics/multigrasp-spring-preload')
    args=parser.parse_args()
    root=args.output_root.resolve()
    root.mkdir(parents=True,exist_ok=True)
    status=root/'pipeline-status.json'
    assert not status.exists()
    state=dict(status='running',started=now(),gpu=args.gpu,stages=[],scope=__doc__)
    atomic_json(status,state)
    env=runtime_environment(dict(project=str(ROOT),python=sys.executable),args.gpu)

    def run(name,cmd):
        with (root/(name+'.log')).open('w') as log:
            child=subprocess.Popen([sys.executable]+cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        row=dict(name=name,pid=child.pid,started=now(),command=cmd,status='running')
        state['stages'].append(row);atomic_json(status,state)
        try: code=child.wait(timeout=1800)
        except subprocess.TimeoutExpired:child.kill();child.wait();code=124
        row.update(returncode=code,finished=now(),status='completed' if code==0 else 'failed')
        if code:state.update(status='failed',finished=now())
        atomic_json(status,state)
        if code:raise SystemExit(code)

    train=root/'train'
    run('prepare_train',['-m','scripts.prepare_wuji_spring_preload','--output',str(train)])
    common=['-m','scripts.audit_wuji_static_grasp','--hand','wuji_paper_official_actuator',
            '--object','knife_wuji_fingertip_precision000']
    run('audit_train',common+['--initial-states',str(train/'initial_states.npy'),'--output',str(train/'static')])
    manifest=json.loads((train/'manifest.json').read_text())
    import yaml
    config=yaml.safe_load((train/'static/config.yaml').read_text())
    assert config['object']['asset']['asset_root']=='assets/objects/knife_wuji_fingertip'
    report=json.loads((train/'static/report.json').read_text())
    assert report['num_envs']==297 and report['recorded_steps']==600
    assert report['initial_state_sha256']==manifest['states_sha256']
    rows=[]
    for i,setting in enumerate(manifest['settings']):
        records=report['records'][i*33:(i+1)*33]
        meta=manifest['records'][i*33:(i+1)*33]
        rows.append(dict(setting_index=i,setting=setting,stable20s=sum(v['stable20s'] for v in records),
            stable2s=sum(v['stable2s'] for v in records),falls=sum(v['fall'] for v in records),
            mean_target_shift_l2=sum(v['target_shift_l2'] for v in meta)/33))
    chosen=min(rows,key=lambda v:(-v['stable20s'],v['mean_target_shift_l2'],v['setting_index']))
    selection=dict(status='selected_on_training_only',selected_utc=now(),setting=chosen['setting'],
                   selected_index=chosen['setting_index'],training_results=rows,
                   source_report_sha256=hashlib.sha256((train/'static/report.json').read_bytes()).hexdigest(),
                   selection_rule=manifest['selection_rule'])
    atomic_json(root/'selection.json',selection)
    validation=root/'validation'
    run('prepare_validation',['-m','scripts.prepare_wuji_spring_preload','--output',str(validation),
                            '--selection',str(root/'selection.json')])
    run('audit_validation',common+['--initial-states',str(validation/'initial_states.npy'),'--output',str(validation/'static')])
    result=json.loads((validation/'static/report.json').read_text())
    assert result['num_envs']==5
    state.update(status='completed',finished=now(),training_selected=chosen,validation_stable20s=result['stable20s'])
    atomic_json(status,state)
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    main()
