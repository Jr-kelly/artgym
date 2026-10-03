"""Two bounded known-stroke support trials against existing matched baselines."""
import datetime,hashlib,json,os,pathlib,subprocess,time
from scripts.record_wuji_support_goal import record

R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003'
env=dict(os.environ,PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONPATH='.:rl_games',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1')
for policy,weight in [('P50','runs/robust-knife-family-20261003/train/geometric-P1/update_000050.pth'),('looser150','runs/support-pressure-20261003/train/joint-looser-v34/update_000150.pth'),('pressure150','runs/support-pressure-20261003/train/joint-pressure-v34/update_000150.pth')]:
    label='nominal'
    baseline=B/'jobs'/(label+'-baseline-v35');identity=json.loads((baseline/'identity.json').read_text())
    assert json.loads((baseline/'result.json').read_text())['exit_code']==0
    cmd=identity['command'].copy();name=label+'-'+policy+'-learned-v38';job=B/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    cmd[cmd.index('--output')+1]=str((B/'demo'/name).relative_to(R))
    reference=B/'pressure-config-v35'/label/'reference.json'
    cmd[cmd.index('--thumb-reference-override')+1]=str(reference.relative_to(R))
    cmd[cmd.index('--residual-checkpoint')+1]=weight
    identity['weight_sha256']=hashlib.sha256((R/weight).read_bytes()).hexdigest()
    identity.update(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,launcher_pid=os.getpid(),
                    matched_baseline=str(baseline.relative_to(R)),reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                    source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['scripts/wuji_scheduled_thumb_reference.py','scripts/g2_r800_policy.py','scripts/run_g2_robust_demo.py']})
    (job/'identity.json').write_text(json.dumps(identity,indent=2))
    record('native_large_error_learned_job_started',evidence=str(job.relative_to(R)/'identity.json'),config=identity,
           next='Actual unchanged36s TABLE episode, samegeometry/noisyestimate/material/load/weight; newfrozen learnedactor only; checkpointpressureadapter restored when present')
    start=time.monotonic()
    with (job/'output.log').open('w') as log:
        child=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
    identity.update(exit_code=child.returncode,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-start)
    (job/'result.json').write_text(json.dumps(identity,indent=2))
    record('native_large_error_learned_job_closed',evidence=str(job.relative_to(R)/'result.json'),config=identity,
           next='Compare actualbehavior on estimatorblindspot; no independentvalidation claim')
    if child.returncode:raise RuntimeError(name+' failed; evidence retained')
