"""Wait for final jobs to release each GPU, then render fixed development examples."""
import datetime,json,os,subprocess,time
from pathlib import Path
r=Path('/tmp/artgym-unified-policy-20260930');os.chdir(r);b=r/'runs/unified-policy-20260930';f=json.loads((r/'research/unified-policy-20260930/final-freeze.json').read_text());pending={0:2,1:5};jobs=[];deadline=time.time()+5800
while pending:
 for gpu,sec in list(pending.items()):
  marker=b/('final-t'+str(sec)+'-job/status.json')
  if not marker.exists():continue
  try:status=json.loads(marker.read_text())
  except json.JSONDecodeError:continue
  if status['status'] not in ['completed','failed','timeout']:continue
  assert status['status']=='completed',status
  name='demo-t'+str(sec);cmd=['/tmp/wuji-unified-runtime/bin/python','-m','scripts.run_wuji_unified_job','--name',name+'-job','--gpu',str(gpu),'--timeout','1200','--','PYTHON','-m','scripts.audit_wuji_multigrasp','--checkpoint',f['candidate']['path'],'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states','research/unified-policy-20260930/data/development-all.npy','--initial-state-rows','0','32','64','96','--span','.04','--output','runs/unified-policy-20260930/'+name,'--seed','2026093030','--stage-seconds',str(sec),'--video']
  with (b/(name+'-wrapper.log')).open('w') as out:p=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  jobs.append(dict(pid=p.pid,name=name,gpu=gpu,command=cmd,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));(b/'video-launched.json').write_text(json.dumps(jobs,indent=2)+'\n');pending.pop(gpu)
 if time.time()>deadline:raise TimeoutError('Final jobs have not released GPUs; no video launched on occupied device')
 time.sleep(3)
