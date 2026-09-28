"""New authorized round: locked budget, immutable source, timed local workers.
Conservative GPU accounting charges entire physics process wall time on one GPU,
including startup/CPU/rendering; independent processes are summed, never averaged.
"""
import argparse,datetime,fcntl,hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/g2-functional-v2-20260928'
def utc():return datetime.datetime.now(datetime.timezone.utc)
def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--name');p.add_argument('--module',default='scripts.run_g2_tabletop');p.add_argument('--kind',choices=['development','validation','learning'],default='development');p.add_argument('--max-seconds',type=int,default=900);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
 if a.worker:
  m=json.loads(a.worker.read_text());start=time.monotonic();cmd=m['command'];env=os.environ.copy();pin=Path(m['cwd'])
  env.update(PATH='/home/agiuser/miniconda3/envs/artgym/bin:'+env['PATH'],LD_LIBRARY_PATH='/home/agiuser/miniconda3/envs/artgym/lib',PYTHONPATH=str(pin)+':'+str(pin/'rl_games'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
  with open(m['log'],'x') as f:
   child=subprocess.Popen(cmd,cwd=pin,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   (BASE/(m['name']+'-running.json')).write_text(json.dumps(dict(pid=child.pid,utc=utc().isoformat(),command=cmd)))
   try:code=child.wait(timeout=m['max_seconds']);reason='exited'
   except subprocess.TimeoutExpired:
    os.killpg(child.pid,signal.SIGTERM)
    try:code=child.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);code=child.wait()
    reason='reserved_wall_limit'
  result=dict(exit_code=code,reason=reason,seconds=time.monotonic()-start,ended_utc=utc().isoformat())
  (BASE/(m['name']+'-status.json')).write_text(json.dumps(result,indent=2)+'\n');return
 assert a.name and a.max_seconds>0
 extra=a.args[1:] if a.args[:1]==['--'] else a.args
 output=Path(extra[extra.index('--output')+1]);assert output.is_absolute() and BASE.resolve() in output.resolve().parents
 assert not output.exists(), 'Do not overwrite runs'
 with (BASE/'budget.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);state=json.loads((BASE/'state.json').read_text());old=list(BASE.glob('*-launch.json'))
  controls=sum(json.loads(f.read_text())['kind']!='learning' for f in old);configs=sum(json.loads(f.read_text())['kind']=='learning' for f in old)
  dev=sum(json.loads(f.read_text())['kind']=='development' for f in old)
  gpu=0.
  for f in old:
   m=json.loads(f.read_text());status=BASE/(m['name']+'-status.json');gpu+=(json.loads(status.read_text())['seconds'] if status.exists() else m['max_seconds'])/3600
  remaining=dict(control=100-controls,development=80-dev,learning=6-configs,gpu_hours=8-gpu,wall_seconds=(datetime.datetime.fromisoformat(state['deadline_utc'])-utc()).total_seconds())
  print(json.dumps(dict(before_launch=remaining)),flush=True)
  assert a.max_seconds<remaining['wall_seconds'] and a.max_seconds/3600<=remaining['gpu_hours']
  if a.kind=='learning':assert configs<6
  else:assert controls<100 and (a.kind=='validation' or dev<80)
  manifest=BASE/(a.name+'-launch.json');assert not manifest.exists()
  files=sorted((ROOT/'scripts').glob('*.py'))+sorted((ROOT/'configs').rglob('*'))
  hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()};version=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
  pin=BASE/'source-pins'/version
  if not pin.exists():
   pin.mkdir(parents=True)
   for name in ['scripts','configs']:shutil.copytree(ROOT/name,pin/name)
   for name in ['isaacgymenvs','rl_games','assets','caches','runs']:(pin/name).symlink_to(ROOT/name,target_is_directory=True)
   (pin/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
  info=dict(name=a.name,kind=a.kind,utc=utc().isoformat(),max_seconds=a.max_seconds,remaining_before=remaining,command=['/home/agiuser/miniconda3/envs/artgym/bin/python','-u','-m',a.module]+extra,cwd=str(pin),source_version=version,log=str(BASE/(a.name+'.log')),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),accounting='Each launched independent execution counted even on setup failure; sum full worker walltime as conservative singleGPU time')
  manifest.write_text(json.dumps(info,indent=2)+'\n')
  proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker',str(manifest)],cwd=ROOT,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  info['supervisor_pid']=proc.pid;manifest.write_text(json.dumps(info,indent=2)+'\n')
  state['last_launch']=a.name;state['executions']=[f.name for f in sorted(BASE.glob('*-launch.json'))];(BASE/'state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(info,indent=2))
if __name__=='__main__':main()
