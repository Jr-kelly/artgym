"""Bounded development selection and equal-budget frozen tests for hold continuations."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/hold-20260929'
DATA=ROOT/'research/hold-20260929/data'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_for(path, key, expected, deadline):
    while time.time()<deadline:
        if path.exists():
            result=json.loads(path.read_text())
            if result.get(key)==expected:return result
            if result.get(key)=='failed':raise RuntimeError(result)
        time.sleep(20)
    raise TimeoutError(str(path))


def evaluate(checkpoint,states,protocol,gpu,label):
    evidence=BASE/label/'evidence'
    module='scripts.audit_wuji_multigrasp_arrival' if protocol=='arrival' else 'scripts.audit_wuji_multigrasp'
    command=[sys.executable,'-m','scripts.run_wuji_hold_job','--name',label,'--gpu',str(gpu),'--timeout','900','--','PYTHON','-m',module,
        '--checkpoint',str(checkpoint),'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator',
        '--object','knife_wuji_bridge3_20260922','--initial-states',str(states),'--span','.04','--output',str(evidence),'--seed','2026092930']
    command+=['--total-seconds','20'] if protocol=='arrival' else ['--stage-seconds','5' if protocol=='fixed5' else '2']
    if protocol=='static':command+=['--static']
    subprocess.run(command,cwd=ROOT,check=True)
    report=json.loads((evidence/'report.json').read_text())
    assert report['initial_states_sha256']==sha(states) and report['checkpoint_sha256']==sha(checkpoint)
    return dict(protocol=protocol,evidence=str(evidence.relative_to(ROOT)),report=report)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['development','final'],required=True)
    p.add_argument('--row',type=int,choices=[3,11],required=True);p.add_argument('--gpu',type=int,required=True)
    p.add_argument('--condition',choices=['original','dense1']);p.add_argument('--seed-label',default='seed2901')
    p.add_argument('--deadline-utc',default='2026-09-29T16:00:00+00:00');a=p.parse_args()
    deadline=datetime.datetime.fromisoformat(a.deadline_utc).timestamp()
    if a.mode=='development':
        assert a.condition
        name=f'hold_r{a.row}_{a.condition}_{a.seed_label}'
        out=BASE/('dev-'+name);out.mkdir(parents=True,exist_ok=False)
        wait_for(BASE/name/'status.json','status','completed',deadline)
        results=[];scores={}
        for epoch in [1250,1500,1750,2000]:
            checkpoint=ROOT/'runs'/name/'checkpoints'/f'epoch_{epoch:06d}.pth'
            values=[]
            for seconds in (2,5):
                item=evaluate(checkpoint,DATA/f'dev-row{a.row}.npy',f'fixed{seconds}',a.gpu,f'dev-{name}-cp{epoch}-t{seconds}')
                item['epoch']=epoch;results.append(item);values.append(item['report']['stable_full_all_endpoints']/32)
                (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
            scores[epoch]=sum(values)/2
        selected=max(scores,key=lambda epoch:(scores[epoch],epoch))
        cp=ROOT/'runs'/name/'checkpoints'/f'epoch_{selected:06d}.pth'
        frozen=dict(status='frozen',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            name=name,row=a.row,condition=a.condition,epoch=selected,checkpoint=str(cp.relative_to(ROOT)),sha256=sha(cp),
            scores=scores,rule='Equal strict fixed2/5 rates on32 fixed own-source development perturbations; tie latest; final not used')
        (out/'results.json').write_text(json.dumps(dict(status='completed',results=results),indent=2)+'\n')
        (out/'frozen.json').write_text(json.dumps(frozen,indent=2)+'\n');print(json.dumps(frozen),flush=True)
    else:
        out=BASE/f'final-row{a.row}-{a.seed_label}';out.mkdir(parents=True,exist_ok=False)
        selected={condition:wait_for(BASE/f'dev-hold_r{a.row}_{condition}_{a.seed_label}'/'frozen.json','status','frozen',deadline) for condition in ('original','dense1')}
        states=DATA/f'final-row{a.row}.npy';models={'parent':BASE/'parents'/f'expert{a.row}.pth'}
        for condition in ('original','dense1'):
            models[condition+'-final']=ROOT/'runs'/f'hold_r{a.row}_{condition}_{a.seed_label}'/'checkpoints/epoch_002000.pth'
            models[condition+'-selected']=ROOT/selected[condition]['checkpoint']
        plan=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),row=a.row,states_sha256=sha(states),
            models={name:dict(path=str(cp.relative_to(ROOT)),sha256=sha(cp)) for name,cp in models.items()},
            selected=selected,gpu=a.gpu,scope='Same128 new perturbations per source and physicalGPU. Primary final2000 equal additional163840000 interactions; developmentselected table supplementary. Parent reference unchanged. Not unseen-grasp generalization.')
        (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        results=[dict(model='static',**evaluate(models['parent'],states,'static',a.gpu,f'final-r{a.row}-{a.seed_label}-static'))]
        cache={}
        for name,checkpoint in models.items():
            for protocol in ('fixed2','fixed5','arrival'):
                key=(sha(checkpoint),protocol)
                if key in cache:
                    item=dict(cache[key],model=name,reused_identical_checkpoint_evidence=True)
                else:
                    item=dict(model=name,**evaluate(checkpoint,states,protocol,a.gpu,f'final-r{a.row}-{a.seed_label}-{name}-{protocol}'))
                    cache[key]=item
                results.append(item)
                (out/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
        result=dict(status='completed',plan=plan,results=results)
        (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(dict(status='completed',output=str(out))),flush=True)


if __name__=='__main__':main()
