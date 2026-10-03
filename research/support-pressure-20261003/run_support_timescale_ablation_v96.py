"""Two bounded known-stroke support trials against existing matched baselines."""
import datetime,hashlib,json,os,pathlib,subprocess,time
import argparse
p=argparse.ArgumentParser();p.add_argument('--gpu',type=int,required=True);a=p.parse_args();a.variant='slow6-untrained'
weights={a.variant:'runs/support-pressure-20261003/checkpoints/strong750-support-period5-v96.pth'}
def record(*args,**kwargs): pass # Remote receipts copied to primary durable journal on launch/close; primary handoff paths are not remote paths.

R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003'
import torch
source=R/'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth'
output=R/weights[a.variant];output.parent.mkdir(parents=True,exist_ok=True);assert not output.exists()
payload=torch.load(source,map_location='cpu');payload['support_command_period']=5;payload['intervention']='Decisiontime-only nativeablation, no learning/modeltensor changes'
torch.save(payload,output)
(output.with_suffix('.receipt.json')).write_text(json.dumps(dict(source=str(source.relative_to(R)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),ablation_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),scope='Deploymenttimescale ablation only; not new learnedweight'),indent=2))
env=dict(os.environ,PATH='/home/wangjiarui/artgym-runtime/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/wangjiarui/artgym-runtime/lib',PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONPATH='.:rl_games',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',CUDA_VISIBLE_DEVICES=str(a.gpu),PYTHONUNBUFFERED='1')
for label,policy,weight in [(label,a.variant,weights[a.variant]) for label in ['nominal','raised1']]:
    baseline=B/'jobs'/(label+'-baseline-v35');identity=json.loads((baseline/'identity.json').read_text())
    assert json.loads((baseline/'result.json').read_text())['exit_code']==0
    cmd=identity['command'].copy();cmd[0]='/home/wangjiarui/artgym-runtime/bin/python';identity['gpu']=a.gpu;name=label+'-'+policy+'-support-timescale-ablation-v96';job=B/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
    cmd[cmd.index('--output')+1]=str((B/'demo'/name).relative_to(R))
    folder=B/'staged-brace-config-v86'/label
    reference=folder/'reference.json'
    cmd[cmd.index('--support-pressure-config')+1]=str((folder/'support.json').relative_to(R))
    cmd[cmd.index('--thumb-reference-override')+1]=str(reference.relative_to(R))
    cmd[cmd.index('--residual-checkpoint')+1]=weight
    identity['weight_sha256']=hashlib.sha256((R/weight).read_bytes()).hexdigest()
    if False:cmd+=['--video']
    identity.update(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,launcher_pid=os.getpid(),
                    matched_baseline=str(baseline.relative_to(R)),reference_sha256=hashlib.sha256(reference.read_bytes()).hexdigest(),
                    source_sha256={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in ['scripts/wuji_scheduled_thumb_reference.py','scripts/g2_r800_policy.py','scripts/run_g2_robust_demo.py']})
    (job/'identity.json').write_text(json.dumps(identity,indent=2))
    record('native_matched_history_candidate_job_started',evidence=str(job.relative_to(R)/'identity.json'),config=identity,
           next='Actual unchanged36s TABLE episode, samegeometry/noisyestimate/material/load/weight; newjointtrainedactor only; originalcommonestimate rollingreference retained')
    start=time.monotonic()
    with (job/'output.log').open('w') as log:
        child=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
    identity.update(exit_code=child.returncode,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-start)
    (job/'result.json').write_text(json.dumps(identity,indent=2))
    record('native_matched_history_candidate_job_closed',evidence=str(job.relative_to(R)/'result.json'),config=identity,
           next='Matched newstagedsupport H200900 adaptation comparison, same publicestimate/grip/clearancepath/load/material/criteria andsameinitial750bank/Adam/RNG/budget. Comparewith existing750staged v87, no duplicatebaseline/independentvalidation claim.')
    if child.returncode:raise RuntimeError(name+' failed; evidence retained')
