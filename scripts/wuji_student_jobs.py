"""Bounded single-GPU remote jobs with immutable source snapshots and durable ledger."""
import argparse,fcntl,shutil,datetime,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
from scripts.record_wuji_student_goal import record,R,D
SSH=['ssh','-i','/home/agiuser/.ssh/id_ed25519_h200','-p','33024','wangjiarui@10.13.160.5']
REMOTE='/tmp/artgym-student-20261001'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--gpu',type=int,required=True);p.add_argument('--seconds',type=int,required=True);p.add_argument('--final',action='store_true');p.add_argument('--local',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
 assert a.gpu in range(4) and a.seconds>0
 if any(token.endswith('final-all.npy') for token in a.command):assert a.final, 'Final cohort requires explicit frozen final phase'
 state=json.loads((D/'STATE.json').read_text())
 cutoff=state['deadline_utc'] if a.final else state['ordinary_cutoff_utc']
 assert time.time()+a.seconds+30<=datetime.datetime.fromisoformat(cutoff).timestamp()
 jobs=R/'runs/unified-student-20261001/jobs';jobs.mkdir(parents=True,exist_ok=True)
 with (jobs/'.launch.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  completed=sum(json.loads(p.read_text())['gpu_hours'] for p in jobs.glob('*/result.json'))
  active=[json.loads(p.read_text()) for p in jobs.glob('*/identity.json') if not (p.parent/'result.json').exists()]
  assert not any(j['gpu']==a.gpu and j.get('local',False)==a.local for j in active), 'GPU has an owned active job'
  assert len(active)<4
  reserve=0 if a.final else state['reserved_final_gpu_hours']
  assert completed+sum(j['seconds']/3600 for j in active)+a.seconds/3600<=state['max_gpu_hours']-reserve
  available=subprocess.check_output(([] if a.local else SSH)+(['nvidia-smi','--query-gpu=index,memory.used','--format=csv,noheader,nounits'] if a.local else ['nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits']),text=True)
  memory={int(line.split(',')[0]):int(line.split(',')[1]) for line in available.strip().splitlines()}
  if a.local:
   processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=process_name','--format=csv,noheader'],text=True).strip().splitlines()
   assert all('ToDesk' in x for x in processes), 'Unrelated local compute process'
   assert memory[a.gpu]<5000
  else:assert memory[a.gpu]<100, 'GPU is not idle'
  out=jobs/a.name;out.mkdir(exist_ok=False)
  start=time.time();identity=dict(name=a.name,gpu=a.gpu,seconds=a.seconds,command=a.command,start_utc=utc(),local_pid=os.getpid(),remote_root=REMOTE,final=a.final,local=a.local,resource_check=available)
  codehash=hashlib.sha256()
  for folder in ['scripts','isaacgymenvs','rl_games']:
   for path in sorted((R/folder).rglob('*')):
    if path.is_file() and path.suffix in ['.py','.yaml']:
     codehash.update(str(path.relative_to(R)).encode());codehash.update(path.read_bytes())
  identity['local_source_sha256']=codehash.hexdigest()
  if a.final:
   from scripts.validate_wuji_student_final import validate
   identity.update(validate(a.command,codehash.hexdigest(),R))
  (out/'identity.json').write_text(json.dumps(identity,indent=2))
 # A real copy freezes source/config and assets; outputs use a shared job namespace.
 pin=REMOTE+'/pins/'+a.name
 prep='mkdir -p '+shlex.quote(pin)+'; cp -a '+REMOTE+'/source/. '+shlex.quote(pin)+'/; ln -s '+REMOTE+'/runs '+shlex.quote(pin)+'/runs'
 if a.local:
  pin='/tmp/artgym-student-local-pins/'+a.name
  Path(pin).mkdir(parents=True,exist_ok=False)
  for folder in ['scripts','isaacgymenvs','rl_games','assets','caches']:
   shutil.copytree(R/folder,Path(pin)/folder,ignore=shutil.ignore_patterns('__pycache__'))
  for folder in ['unified-student-20261001/data','multigrasp-20260928/data','artmanip-recovery-20260930/data']:
   shutil.copytree(R/'research'/folder,Path(pin)/'research'/folder,ignore=shutil.ignore_patterns('final*'))
  (Path(pin)/'runs').symlink_to(R/'runs',target_is_directory=True)
 else:subprocess.run(SSH+[prep],check=True)
 command=a.command[1:] if a.command[:1]==['--'] else a.command
 env='CUDA_VISIBLE_DEVICES='+str(a.gpu)+' LD_LIBRARY_PATH=/tmp/wuji-student-runtime/lib PYTHONPATH=.:rl_games TORCH_EXTENSIONS_DIR=/tmp/wuji-student-torch-extensions OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=2 PYTHONNOUSERSITE=1 PYTHONUNBUFFERED=1'
 if a.local:env='PATH=/home/agiuser/miniconda3/envs/artgym/bin:$PATH '+env.replace('/tmp/wuji-student-runtime/lib','/home/agiuser/miniconda3/envs/artgym/lib').replace('/tmp/wuji-student-torch-extensions','/tmp/wuji-student-local-torch-extensions')
 shell='cd '+shlex.quote(pin)+' && '+env+' timeout --signal=TERM --kill-after=30 '+str(a.seconds)+' '+shlex.join(command)
 # The local working tree can contain new analysis helpers. Record the actual
 # immutable pin separately; never present its local hash as remote provenance.
 pin_audit="import pathlib,hashlib,json,sys\nr=pathlib.Path(sys.argv[1]);h=hashlib.sha256();selected={}\nfor folder in ['scripts','isaacgymenvs','rl_games']:\n for p in sorted((r/folder).rglob('*')):\n  if p.is_file() and p.suffix in ['.py','.yaml']:\n   rel=str(p.relative_to(r));data=p.read_bytes();h.update(rel.encode());h.update(data)\n   if p.name in ['train_wuji_unified_student.py','evaluate_wuji_recovery.py','wuji_student_interface.py','wuji_known_controller.py','a2c_sapg_priv_network_builder.py']:selected[rel]=hashlib.sha256(data).hexdigest()\nprint(json.dumps(dict(pinned_source_sha256=h.hexdigest(),selected_source_sha256=selected)))"
 if a.local:
  provenance=json.loads(subprocess.check_output(['python3','-c',pin_audit,pin],text=True))
 else:
  provenance=json.loads(subprocess.check_output(SSH+['python3 -c '+shlex.quote(pin_audit)+' '+shlex.quote(pin)],text=True))
 identity.update(provenance)
 identity['pinned_source_matches_local']=identity['pinned_source_sha256']==identity['local_source_sha256']
 if a.final:assert identity['pinned_source_matches_local'], 'Final immutable pin differs from frozen source'
 identity['remote_shell']=shell
 (out/'identity.json').write_text(json.dumps(identity,indent=2))
 record('job_started',**identity,next='Poll status; do not duplicate job')
 with (out/'stdout.log').open('w') as log:
  code=subprocess.call((['bash','-c',shell] if a.local else SSH+[shell]),stdout=log,stderr=subprocess.STDOUT)
 elapsed=time.time()-start
 result=dict(**identity,end_utc=utc(),exit_code=code,wall_seconds=elapsed,gpu_hours=elapsed/3600)
 (out/'result.json').write_text(json.dumps(result,indent=2))
 # Ledger derives from completed receipts and live process elapsed, never PID guesses.
 finished=list((R/'runs/unified-student-20261001/jobs').glob('*/result.json'))
 record('job_finished',**result,next='Inspect evidence before dependent experiments')
 raise SystemExit(code)
if __name__=='__main__':main()
