"""Repair exactly one pre-physics CLI failure without changing its placement.

Original manifest, failed launch and frozen source are preserved. Aggregation
reports all21 launches /20 distinct physical placements rather than hiding it.
"""
import argparse
import copy
import datetime
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'runs/g2-local-policy-20260928'
OLD='g2-local-policy-validation-v1-08'
NEW=OLD+'-cli-retry'


def alive(record):
    try:raw=Path('/proc/%d/cmdline'%record['pid']).read_bytes()
    except FileNotFoundError:return False
    return record['module'].encode() in raw and NEW.encode() in raw


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','aggregate']);a=p.parse_args()
    results=json.loads((ROOT/'research/g2-local-policy-validation-v1-results.json').read_text())
    assert results['all_finished'], 'Finish original frozen queue first'
    original=json.loads((RUN/(OLD+'-launch.json')).read_text())
    manifest=RUN/(NEW+'-launch.json')
    if a.action=='launch':
        assert not manifest.exists() and not (RUN/NEW).exists()
        failure=json.loads((RUN/OLD/'failure.json').read_text())
        assert failure['exception_type']=='ArgumentParserError' and failure['steps']==0
        command=original['command'].copy();dy=command.index('--dy');value=command[dy+1]
        command[dy:dy+2]=['--dy='+value]
        command[command.index('--output')+1]=str(RUN/NEW)
        restored=command.copy();j=restored.index('--dy='+value);restored[j:j+1]=['--dy',value]
        restored[restored.index('--output')+1]=original['command'][original['command'].index('--output')+1]
        assert restored==original['command'], 'Only CLI tokenization and output folder may change'
        env=os.environ.copy();pin=Path(original['cwd'])
        env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:'+env['PATH'],
            LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',
            PYTHONPATH=str(pin)+':'+str(pin/'rl_games'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        log=RUN/(NEW+'.log')
        with log.open('x') as stream:
            child=subprocess.Popen(command,cwd=pin,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        record=dict(original,pid=child.pid,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            command=command,log=str(log),predecessor=OLD,scope='frozen validation identical numeric placement08; pre-physics CLI repair only')
        manifest.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return
    record=json.loads(manifest.read_text());assert not alive(record)
    folder=RUN/NEW;report=folder/'report.json';failure=folder/'failure.json'
    assert report.exists() or failure.exists()
    combined=copy.deepcopy(results);row=combined['trials'][8];original_row=copy.deepcopy(row)
    row.update(name=NEW,original_failed_launch=original_row)
    if report.exists():
        r=json.loads(report.read_text());row.update(status='finished',grasp_success=r['grasp_success'],
            operation_entered=r['operation_steps']>0,operation_success=r['operation_window_success'],
            whole_success=r['required_task_success'],failure=r.get('failure_class'))
    else:
        r=json.loads(failure.read_text());row.update(status='failed',failure=r,grasp_success=False,
            operation_entered=r.get('last_phase')=='operate',operation_success=False,whole_success=False)
    physical=sum(any((RUN/r['name']/name).exists() for name in ['trace.npz','partial-trace.npz']) for r in combined['trials'])
    combined.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        frozen_original_results='research/g2-local-policy-validation-v1-results.json',
        launch_attempts=21,prephysics_cli_failures=1,unique_physical_placements=physical,
        acquisition_successes=sum(r['grasp_success'] for r in combined['trials']),
        conditional_operation_successes=sum(r['operation_success'] for r in combined['trials'] if r['grasp_success']),
        whole_successes=sum(r['whole_success'] for r in combined['trials']),
        denominator='20 frozen distinct numerical placements; original failed CLI launch08 preserved separately; no controller/source/physics changes')
    output=ROOT/'research/g2-local-policy-validation-v1-physical-results.json'
    assert not output.exists();output.write_text(json.dumps(combined,indent=2)+'\n')
    print(json.dumps({k:v for k,v in combined.items() if k!='trials'}))


if __name__=='__main__':main()
