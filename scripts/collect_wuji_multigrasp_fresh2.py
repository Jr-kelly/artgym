"""Bounded local continuation of the queued second-generation physical test screen."""
import argparse,datetime,json,shlex,subprocess,sys,time
from pathlib import Path
from scripts.monitor_wuji_checkpoints import runtime_environment
R=Path(__file__).resolve().parents[1];BASE=R/'runs/multigrasp-20260928';DATA=R/'research/multigrasp-20260928/data'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-i','/home/agiuser/.ssh/id_ed25519_h200','-o','IdentitiesOnly=yes','-p','30296','wangjiarui@10.14.0.93'];REMOTE='/home/wangjiarui/artgym-multigrasp-20260928'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--label',default='fresh2-local-continuation');a=parser.parse_args()
 out=BASE/a.label;out.mkdir(exist_ok=False);start=time.monotonic();state=dict(status='waiting_generation',started=now(),deadline_utc='2026-09-28T23:53:52+00:00')
 def save():
  state['heartbeat']=now();(out/'status.json').write_text(json.dumps(state,indent=2)+'\n')
 while datetime.datetime.now(datetime.timezone.utc)<datetime.datetime(2026,9,28,23,53,52,tzinfo=datetime.timezone.utc):
  save();result=subprocess.run(SSH+['cat '+REMOTE+'/runs/multigrasp-20260928/fresh-generation-v2/status.json'],capture_output=True,text=True,timeout=25)
  if result.returncode==0:
   remote=json.loads(result.stdout)
   if remote['status'] in ['completed','failed']:break
  time.sleep(30)
 else:raise TimeoutError('Generation wait deadline')
 state['generation']=remote
 if remote['status']!='completed':state['status']='generation_failed';save();return
 rsync=['rsync','-a','-e',shlex.join(SSH[:-1])]
 cache='caches/initial_grasp/wuji/knife_wuji_lowgain_fresh_multigrasp2026092805/000/'
 (R/cache).mkdir(parents=True,exist_ok=True)
 subprocess.run(rsync+[SSH[-1]+':'+REMOTE+'/'+cache,str(R/cache)+'/'],check=True,timeout=120)
 subprocess.run(rsync+[SSH[-1]+':'+REMOTE+'/runs/multigrasp-20260928/fresh-generation-3000/',str(BASE/'fresh-generation-3000')+'/'],check=True,timeout=120)
 import shutil
 states=DATA/'fresh2805-candidates.npy';assert not states.exists();shutil.copy2(R/cache/'valid_grasps.npy',states)
 env=runtime_environment(dict(project=str(R),python=sys.executable))
 geometry=DATA/'fresh2805-geometry.json';state['status']='geometry_screen';save()
 with (out/'geometry.log').open('w') as f:subprocess.run([sys.executable,'-m','scripts.screen_wuji_multigrasp_test','--states',str(states),'--output',str(geometry),'--seed','2026092805'],cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
 state['status']='static_screen';save();name='fresh2805-static-v1';evidence=BASE/name/'evidence'
 cmd=[sys.executable,'-m','scripts.run_multigrasp_job','--name',name,'--gpu','0','--timeout','1800','--','PYTHON','-m','scripts.audit_wuji_multigrasp']
 cmd+=['--checkpoint','runs/multigrasp-20260928/reference.pth','--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',str(states),'--static','--stage-seconds','2','--output',str(evidence)]
 subprocess.run(cmd,cwd=R,check=True)
 frozen=DATA/'fresh2805-frozen';subprocess.run([sys.executable,'-m','scripts.freeze_wuji_multigrasp_test','--states',str(states),'--geometry',str(geometry),'--static',str(evidence),'--output',str(frozen),'--seed','2026092809'],cwd=R,env=env,check=True)
 state.update(status='completed',finished=now(),frozen=json.loads((frozen/'manifest.json').read_text()));save()
 subprocess.run([sys.executable,'-m','scripts.record_wuji_multigrasp_event','--event','fresh2805_physical_screen_complete','--summary','Second3000generated candidates physically screened without learned-policy selection; qualified base count '+str(state['frozen']['base_grasp_count']),'--evidence',str(frozen/'manifest.json'),'--next','Freeze four models using development then run final identical-cohort comparison'],cwd=R,check=True)
if __name__=='__main__':main()
