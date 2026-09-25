"""Run an isolated ten-candidate ArtGrasp preflight before fresh generation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from scripts.monitor_wuji_checkpoints import atomic_json, now, runtime_environment


def main():
    root=Path(__file__).resolve().parents[1]
    name='knife_wuji_lowgain_fresh_preflight20260922'
    out=root/'runs/wuji-goal/diagnostics/fresh-lowgain-functional-preflight'
    out.mkdir(parents=True,exist_ok=True)
    assert not (out/'status.json').exists()
    src=root/'assets/objects/knife_wuji_fingertip'
    dst=root/'assets/objects'/name
    assert not dst.exists()
    shutil.copytree(src/'000',dst/'000')
    atomic_json(dst/'lbx.json',{'000':json.loads((src/'lbx.json').read_text())['000']})
    import numpy as np
    cache=root/'caches/initial_grasp/wuji'/name/'000'
    cache.mkdir(parents=True,exist_ok=False)
    original=root/'caches/initial_grasp/wuji/knife_wuji_fingertip/000'
    for filename in ['qpos.npy','opos.npy']:
        if not (original/filename).exists():
            original=root/'caches/initial_grasp/wuji/knife_wuji_paper/000'
        np.save(cache/filename,np.load(original/filename)[:10])
    command=[sys.executable,'-m','scripts.validate_fresh_wuji_lowgain','--dataset',name,
             '--expected-candidates','10','--batch-size','10','--output',str(out/'validation')]
    environment=runtime_environment(dict(project=str(root),python=sys.executable),2)
    with (out/'validation.log').open('w') as log:
        child=subprocess.Popen(command,cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT)
    state=dict(status='running',started=now(),pid=child.pid,command=command,
               purpose='Runtime/configuration preflight, not fresh grasp-generation evidence')
    atomic_json(out/'status.json',state)
    try:code=child.wait(timeout=300)
    except subprocess.TimeoutExpired:child.kill();child.wait();code=124
    state.update(status='completed' if code==0 else 'failed',finished=now(),returncode=code)
    atomic_json(out/'status.json',state)
    raise SystemExit(code)


if __name__=='__main__':main()
