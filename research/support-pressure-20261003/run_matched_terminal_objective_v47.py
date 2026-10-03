"""Continue useful broad physical learning, restoring full optimizer/RNG."""
import argparse,pathlib,json,os,datetime,subprocess,time,hashlib
p=argparse.ArgumentParser();p.add_argument('--variant',choices=['resampled','wider'],required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--checkpoint-update',type=int,default=150);p.add_argument('--updates',type=int,default=750);p.add_argument('--absorbing',action='store_true');a=p.parse_args()
R=pathlib.Path(__file__).resolve().parents[2];base=R/'runs/support-pressure-20261003';original=json.loads((base/'jobs'/('joint-'+a.variant+'-v41')/'identity.json').read_text());cmd=original['command'];cmd=cmd.copy();old=cmd.index('--initialize-model-from');del cmd[old:old+2];name='joint-'+a.variant+('-absorbing' if a.absorbing else '-ordinary')+'-v47';job=base/'jobs'/name;job.mkdir(exist_ok=False)
weight='runs/support-pressure-20261003/train/joint-'+a.variant+'-v41/update_%06d.pth'%a.checkpoint_update;cmd+=['--resume',weight]
if a.absorbing:cmd+=['--absorbing-failure-penalty']
cmd[cmd.index('--output')+1]='runs/support-pressure-20261003/train/'+name
cmd[cmd.index('--updates')+1]=str(a.updates)
env=dict(os.environ,PATH='/home/wangjiarui/artgym-runtime/bin:/usr/bin:/bin',LD_LIBRARY_PATH='/home/wangjiarui/artgym-runtime/lib',PYTHONUTF8='1',PYTHONNOUSERSITE='1',PYTHONPATH='.:rl_games',CUDA_VISIBLE_DEVICES=str(a.gpu),TORCH_EXTENSIONS_DIR='/tmp/wuji-width-torch-extensions',OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',MAX_JOBS='2',PYTHONUNBUFFERED='1')
row=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,launcher_pid=os.getpid(),gpu=a.gpu,resume_weight_sha256=hashlib.sha256((R/weight).read_bytes()).hexdigest(),scope='FullAdam/RNG continuation, actualnewTABLEepisodes; not solver-state bitwise continuation',source_sha256={x:hashlib.sha256((R/x).read_bytes()).hexdigest() for x in ['scripts/train_wuji_robust_residual.py','scripts/g2_continuous_scene.py','scripts/wuji_scheduled_thumb_reference.py','scripts/wuji_joint_deflection_pressure.py']});(job/'identity.json').write_text(json.dumps(row,indent=2));start=time.monotonic()
with (job/'output.log').open('w') as log:
    child=subprocess.Popen(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT);row['child_pid']=child.pid;(job/'identity.json').write_text(json.dumps(row,indent=2));child.wait()
row.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),exit_code=child.returncode,wall_seconds=time.monotonic()-start);(job/'result.json').write_text(json.dumps(row,indent=2));print(json.dumps(row),flush=True)
