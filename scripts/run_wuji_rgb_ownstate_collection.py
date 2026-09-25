"""Collect frozen RGB policy states after the ongoing paired evaluation finishes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from scripts.monitor_wuji_checkpoints import atomic_json,now,runtime_environment


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True)
    args=p.parse_args();spec=json.loads(args.spec.read_text());root=Path(spec['root']);pin=Path(__file__).resolve().parents[1]
    out=root/spec['output'];assert out.exists() and not (out/'status.json').exists()
    state=dict(status='waiting_for_previous_evaluation',started=now(),spec=spec,stages=[])
    atomic_json(out/'status.json',state);child=None
    try:
        while True:
            previous=json.loads((root/spec['wait_for']/'status.json').read_text())
            assert previous['status']!='failed',previous.get('error')
            if previous['status']=='completed':break
            state['heartbeat']=now();atomic_json(out/'status.json',state);time.sleep(15)
        artifact=root/spec['artifact']
        assert hashlib.sha256(artifact.read_bytes()).hexdigest()==spec['artifact_sha256']
        selected=[base+i for base in [0,100,200] for i in range(30)]
        stages=[dict(name='runtime',seconds=2,rows=[0,100,200],runtime=True)]
        stages += [dict(name=f'collection-{seconds}s-part{part}',seconds=seconds,rows=selected[part*45:(part+1)*45],runtime=False)
            for seconds in [2,5] for part in range(2)]
        collections=[]
        for stage in stages:
            folder=out/stage['name']
            cmd=[sys.executable,'-m','scripts.eval_wuji_rgb_state_policy','--artifact',str(artifact),
                '--output',str(folder),'--seconds',str(stage['seconds']),'--collect-rgb-data',
                '--initial-state-rows']+list(map(str,stage['rows']))
            if stage['runtime']:cmd+=['--runtime-check']
            env=runtime_environment(dict(project=str(pin),python=sys.executable),0)
            env['VK_ICD_FILENAMES']='/etc/vulkan/icd.d/nvidia_icd.json'
            with (out/(stage['name']+'.log')).open('w') as f:
                child=subprocess.Popen(cmd,cwd=pin,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
            row=dict(name=stage['name'],pid=child.pid,command=cmd,status='running',started=now())
            state['status']='collecting';state['stages'].append(row);atomic_json(out/'status.json',state)
            code=child.wait();row.update(returncode=code,status='completed' if code==0 else 'failed',finished=now())
            atomic_json(out/'status.json',state);assert code==0,row
            policy=json.loads((folder/'rgb-policy-audit.json').read_text())
            assert policy['status']=='passed' and policy['model_unchanged'] and policy['estimator_unchanged']
            if stage['runtime']:assert policy['checks']['privileged_invariance']==1800
            audit_path=folder/'collection-independent-audit.json'
            command=[sys.executable,'-m','scripts.audit_wuji_rgb_state_data','--run',str(folder),
                '--output',str(audit_path),'--allow-inactive']
            with (out/(stage['name']+'-audit.log')).open('w') as f:
                result=subprocess.run(command,cwd=pin,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
            assert result.returncode==0
            audit=json.loads(audit_path.read_text());assert audit['status']=='verified'
            if not stage['runtime']:
                collection=folder/'collection-status.json'
                collections.append(dict(path=str(folder.relative_to(root)),status_sha256=hashlib.sha256(collection.read_bytes()).hexdigest(),
                    active_images=audit['active_images'],inactive_images=audit['inactive_images']))
        assert len(collections)==4
        atomic_json(out/'dataset-manifest.json',dict(status='completed',collections=collections,
            policy_sha256=spec['artifact_sha256'],active_images=sum(c['active_images'] for c in collections),
            inactive_images=sum(c['inactive_images'] for c in collections),
            scope='90oldinitialrows x2clocks x200samples from a frozen RGB controller. Include only active rows in later fitting. No policy update or independent task success.'))
        state.update(status='completed',finished=now(),trained_new_model=False)
    except BaseException as exc:
        state.update(status='failed',finished=now(),error=repr(exc))
        if child and child.poll() is None:child.terminate();child.wait(timeout=20)
        raise
    finally:atomic_json(out/'status.json',state)


if __name__=='__main__':main()
