"""Two bounded known-stroke support trials against existing matched baselines."""
import datetime,hashlib,json,os,pathlib,subprocess,time
import argparse
a=argparse.Namespace(gpu=0,variant='baseline750')
weights={'baseline750':'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth'}
from scripts.record_wuji_support_goal import record

R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003'
env=dict(os.environ,PATH='/home/agiuser/miniconda3/envs/artgym/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONNOUSERSITE='1',PYTHONUTF8='1',PYTHONPATH='.:rl_games',TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',CUDA_VISIBLE_DEVICES=str(a.gpu),PYTHONUNBUFFERED='1')
name='thick14-strong750-necessary-family-film-v80';job=B/'jobs'/name;job.mkdir(parents=True,exist_ok=False)
cmd=['/home/agiuser/miniconda3/envs/artgym/bin/python', '-m', 'scripts.run_g2_robust_demo', '--output', 'runs/support-pressure-20261003/demo/thick14-strong750-necessary-family-film-v80', '--grasp-plan', 'runs/support-pressure-20261003/strong-family-config-v77/thick14/motor-plan.json', '--support-pressure-config', 'runs/support-pressure-20261003/strong-family-config-v77/thick14/support.json', '--thumb-reference-override', 'runs/support-pressure-20261003/strong-family-config-v77/thick14/reference.json', '--knife-asset', 'assets/objects/knife_wuji_support_train_20261003/s0001/mobility.urdf', '--residual-checkpoint', 'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth', '--seconds', '36', '--dx=-.1985', '--dy=.05', '--yaw=0', '--slider-face', 'up', '--table-calibration', 'research/robust-knife-family-20261003/functional-side-edge-under-support-v6/localization.json', '--acquisition-path', 'research/robust-knife-family-20261003/functional-side-edge-under-support-lateral-v3/acquisition-path.json', '--handover-calibration', 'research/robust-knife-family-20261003/handover-from-v25-v1.json', '--load', '.2', '--detent', '.2', '--load-profile', 'pulse', '--load-frequency', '2.9', '--hand-friction', '.65', '--knife-friction', '1.8', '--observation-noise', '.002', '--observation-bias', '.006', '--seed', '2026100358', '--pair-force-measurement', '--resistance-integration', 'solver-brake', '--video']
identity=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,launcher_pid=os.getpid(),weight_sha256='11f87269e7910380c6dab1fa8dcc26e53e40da0bd905a1ae40e7ffcf812b1a1d',scope='One localfullfilm repeat of known H200 development condition, alloutcomescounted; no crossGPU bitwiseclaim/independentvalidation')
(job/'identity.json').write_text(json.dumps(identity,indent=2));record('stronger_thick14_fullfilm_v80_started',evidence=str(job.relative_to(R)/'identity.json'),config=identity,next='FullactualTABLE movie, keep any failure too')
start=time.monotonic()
with (job/'output.log').open('w') as log:child=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
identity.update(exit_code=child.returncode,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-start)
(job/'result.json').write_text(json.dumps(identity,indent=2));record('stronger_thick14_fullfilm_v80_process_closed',evidence=str(job.relative_to(R)/'result.json'),config=identity,next='Record originalsuccesscriteria/pressure, annotate synchronizedviews; no outcomeclaimuntilreport')
if child.returncode:raise RuntimeError('Filmfailed; evidencepreserved')
