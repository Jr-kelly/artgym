from pathlib import Path
import subprocess,os,json,time,datetime
r=Path('/tmp/artgym-unified-policy-20260930');b=r/'runs/unified-policy-20260930';py='/tmp/wuji-unified-runtime/bin/python';end=time.time()+1800
while time.time()<end:
 states=[]
 for seconds in [2,5]:
  try:states.append(json.loads((b/f'train-data-t{seconds}-job/status.json').read_text()).get('status'))
  except (FileNotFoundError,json.JSONDecodeError):states.append('waiting')
 if 'failed' in states:raise RuntimeError('Collection failed; no pilot')
 if states==['completed','completed']:break
 time.sleep(5)
else:raise TimeoutError('Collection wait exceeded1800s')
env=dict(os.environ,PYTHONPATH=str(r)+':'+str(r/'rl_games'),LD_LIBRARY_PATH='/tmp/wuji-unified-runtime/lib',PYTHONUNBUFFERED='1',TORCH_EXTENSIONS_DIR='/tmp/wuji-unified-torch-extensions');records=[];children=[]
for gpu,expert,source in [(0,'historical',0),(1,'source3',3)]:
 label=f'bc-pilot-{expert}';cmd=[py,'-m','scripts.run_wuji_unified_job','--name',label+'-job','--gpu',str(gpu),'--timeout','1000','--','PYTHON','-m','scripts.train_wuji_unified_bc','--init',f'runs/unified-policy-20260930/experts/{expert}.pth','--data',f'runs/unified-policy-20260930/train-data-t2/source{source}',f'runs/unified-policy-20260930/train-data-t5/source{source}','--output',f'runs/unified-policy-20260930/{label}','--limit','4','--epochs','20','--save-every','10','--perturb','.02','--seed','2026093001','--max-seconds','900']
 with (b/(label+'-wrapper.log')).open('w') as f:p=subprocess.Popen(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 children.append(p);records.append(dict(pid=p.pid,gpu=gpu,command=cmd,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
(b/'bc-pilot-launch.json').write_text(json.dumps(records,indent=2)+'\n')
for p in children:p.wait()
(b/'bc-pilot-queue-completed.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),codes=[p.returncode for p in children]))+'\n')
