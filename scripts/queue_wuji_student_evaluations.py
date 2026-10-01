"""Bounded CPU orchestrator for already-preregistered checkpoint evaluations only."""
import argparse,datetime,json,subprocess,sys,time
from pathlib import Path
from scripts.wuji_student_jobs import SSH,R,D,REMOTE
from scripts.record_wuji_student_goal import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--seconds',type=int,default=7200);p.add_argument('--gpu',type=int,default=2);a=p.parse_args()
 plan=json.loads(a.plan.read_text());pending=list(plan['entries']);beg=time.monotonic()
 record('evaluation_queue_started',plan=str(a.plan),local_pid=__import__('os').getpid(),max_seconds=a.seconds,scope='Only preregistered checkpoints; noadaptivebranches',next='Parent inspects each stage evidence')
 while pending and time.monotonic()-beg<a.seconds:
  jobs=R/'runs/unified-student-20261001/jobs';active=[json.loads(p.read_text()) for p in jobs.glob('*/identity.json') if not (p.parent/'result.json').exists()]
  if len(active)>=4 or any(x['gpu']==a.gpu and not x.get('local') for x in active):time.sleep(15);continue
  available=[]
  for e in pending:
   receipt=jobs/e['name']/'result.json'
   if receipt.exists():
    assert json.loads(receipt.read_text())['exit_code']==0, 'Previously failed evaluation requires explicit repair'
    available.append(e);continue
   path=REMOTE+'/'+e['checkpoint']
   ready=subprocess.call(SSH+['test -f '+path+' && test -f '+path.replace('.pth','.sha256')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)==0
   if not ready:continue
   cmd=[sys.executable,'-m','scripts.wuji_student_jobs','--gpu',str(a.gpu),'--seconds','1800',e['name'],'--','/tmp/wuji-student-runtime/bin/python','-m','scripts.evaluate_wuji_student_batch','--teacher',plan['teacher'],'--models',e['model']+'='+e['checkpoint'],'--states',plan['states'],'--output','runs/unified-student-20261001/'+e['name']]
   code=subprocess.call(cmd,cwd=R)
   if code:
    record('evaluation_queue_failed',name=e['name'],exit_code=code,next='Explicitinspectandrepair; no automatic duplicate retry');return
   available.append(e);break
  for e in available:pending.remove(e)
  if not available:time.sleep(15)
 record('evaluation_queue_finished',pending=pending,wall_seconds=time.monotonic()-beg,next='Analyze completepairedtraces; queuedend is not researchconvergence')
if __name__=='__main__':main()
