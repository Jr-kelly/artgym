"""Two bounded known-stroke support trials against existing matched baselines."""
import datetime,hashlib,json,os,pathlib,subprocess,time
from scripts.record_wuji_support_goal import record

R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003'
env=dict(os.environ,PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONPATH='.:rl_games',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',CUDA_VISIBLE_DEVICES='0',PYTHONUNBUFFERED='1')
for label in ['nominal','raised1']:
    baseline=B/'jobs'/(label+'-baseline-v35');identity=json.loads((baseline/'identity.json').read_text())
    assert json.loads((baseline/'result.json').read_text())['exit_code']==0
    cmd=identity['command'].copy();name=label+'-stroke-support-v36';job=B/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    cmd[cmd.index('--output')+1]=str((B/'demo'/name).relative_to(R))
    reference=B/'pressure-config-v35'/label/'stroke-support-reference-v36.json'
    cmd[cmd.index('--thumb-reference-override')+1]=str(reference.relative_to(R))
    if label=='nominal':cmd+=['--video']
    identity.update(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,launcher_pid=os.getpid(),
                    matched_baseline=str(baseline.relative_to(R)),reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                    source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['scripts/wuji_scheduled_thumb_reference.py','scripts/g2_r800_policy.py','scripts/run_g2_robust_demo.py']})
    (job/'identity.json').write_text(json.dumps(identity,indent=2))
    record('native_stroke_support_job_started',evidence=str(job.relative_to(R)/'identity.json'),config=identity,
           next='Actual unchanged36s TABLE episode, samegeometry/noisyestimate/material/load/weight; bounded supportreference only')
    start=time.monotonic()
    with (job/'output.log').open('w') as log:
        child=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
    identity.update(exit_code=child.returncode,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-start)
    (job/'result.json').write_text(json.dumps(identity,indent=2))
    record('native_stroke_support_job_closed',evidence=str(job.relative_to(R)/'result.json'),config=identity,
           next='Use actualforces/firstbodyinstability to decide whether this mechanism merits training; do not optimize endpointdecimals')
    if child.returncode:raise RuntimeError(name+' failed; evidence retained')
