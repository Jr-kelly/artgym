"""Three-update full-size Sharpa resume probe; never replaces a live teacher."""
import json
import subprocess
import sys
from pathlib import Path

from scripts.monitor_wuji_checkpoints import runtime_environment, now, atomic_json


def main():
    root=Path(__file__).resolve().parents[1]
    name='sharpa_paper_property_probe_20260922'
    out=root/'runs'/name;out.mkdir(exist_ok=True)
    if (out/'probe-status.json').exists():raise RuntimeError('Probe already exists')
    source=root/'runs/sharpa_paper_reference/checkpoints/epoch_000600.pth'
    cmd=[sys.executable,'-m','torch.distributed.run','--standalone','--nnodes=1','--nproc_per_node=2',
         '-m','isaacgymenvs.train','task=artmanip_paper_reference','hand=sharpa',
         'object=knife_sharpa_official','train=paperReferenceSAPG','num_envs=10000',
         'experiment='+name,'max_iterations=603','multi_gpu=True','headless=True',
         'graphics_device_id=-1','force_render=False','pipeline=gpu','num_subscenes=0',
         'seed=20260921','checkpoint='+str(source),'+task.env.batchedObjectPropertyRead=True']
    env=runtime_environment(dict(project=str(root),python=sys.executable));env['CUDA_VISIBLE_DEVICES']='2,3'
    state=dict(started=now(),status='running',command=cmd,gpus=[2,3],
               scope='Same full20kenvironment paper configuration and full optimizer/counters fromCP600; only CPU collection/batched copy of property observations changes. PhysX state is reinitialized on resume.')
    with (out/'teacher.log').open('w') as log:
        p=subprocess.Popen(cmd,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        state['pid']=p.pid;atomic_json(out/'probe-status.json',state)
        try:
            code=p.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:p.wait(timeout=30)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            code=124
    state.update(status='completed' if code==0 else 'failed',returncode=code,finished=now())
    atomic_json(out/'probe-status.json',state)
    if code:raise SystemExit(code)
    latest=json.loads((out/'checkpoints/latest.json').read_text())
    check=[sys.executable,'tests/check_distributed_checkpoint.py',latest['checkpoint'],
           '--world-size','2','--epochs','603','--frames',str(603*320000),
           '--previous',str(source),'--output',str(out/'checkpoint-audit.json')]
    subprocess.run(check,cwd=root,env=env,check=True,stdout=subprocess.DEVNULL)
    state.update(status='checkpoint_verified',verification='checkpoint-audit.json')
    atomic_json(out/'probe-status.json',state);print(json.dumps(state),flush=True)


if __name__=='__main__':main()
