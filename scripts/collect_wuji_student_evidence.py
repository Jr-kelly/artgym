"""Bounded CPU collector for completed, preregistered development evaluations."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from scripts.record_wuji_student_goal import R,D,record
from scripts.wuji_student_jobs import SSH,REMOTE

def main():
 p=argparse.ArgumentParser();p.add_argument('--plans',nargs='+',type=Path,required=True);p.add_argument('--seconds',type=int,default=7200);a=p.parse_args()
 entries=[e for plan in a.plans for e in json.loads(plan.read_text())['entries']];start=time.monotonic()
 ssh_env=dict(os.environ);ssh_env.pop('LD_LIBRARY_PATH',None)
 record('evidence_collector_started',local_pid=os.getpid(),plans=[str(p) for p in a.plans],max_seconds=a.seconds,next='Only finishedjobtraces rescore; noexperimentdecisions automated')
 while entries and time.monotonic()-start<a.seconds:
  done=[]
  for e in entries:
   receipt=R/'runs/unified-student-20261001/jobs'/e['name']/'result.json'
   if not receipt.exists():continue
   result=json.loads(receipt.read_text())
   if result['exit_code']!=0:
    record('evidence_collector_skips_failure',name=e['name'],exit_code=result['exit_code'],next='Parentinspectfailure');done.append(e);continue
   dest=R/'runs/unified-student-20261001'/e['name'];dest.mkdir(exist_ok=True)
   subprocess.run(['/usr/bin/rsync','-a','-e','/usr/bin/ssh -i /home/agiuser/.ssh/id_ed25519_h200 -p 33024','wangjiarui@10.13.160.5:'+REMOTE+'/runs/unified-student-20261001/'+e['name']+'/',str(dest)+'/'],check=True,env=ssh_env)
   out=D/(e['name']+'-analysis')
   commands=[sys.executable,'-m','scripts.analyze_wuji_student','--entries']
   commands+=['teacher=runs/unified-student-20261001/'+n for n in ['teacher-official-S2','teacher-official-S5','teacher-dev-F']]
   commands += [e['model']+'='+str(dest/(e['model']+'-'+protocol)) for protocol in ['S2','S5','F']]
   commands+=['--output',str(out)]
   subprocess.run(commands,cwd=R,check=True,stdout=subprocess.DEVNULL)
   data=json.loads((out/'report.json').read_text());rows=[r for r in data['rows'] if r['model']==e['model']]
   compact={p:{'success':[r['success'] for r in rows if r['protocol']==p],'body':[r['body_stable'] for r in rows if r['protocol']==p]} for p in ['S2','S5','F']}
   record('development_checkpoint_independently_scored',model=e['model'],evidence=str(out.relative_to(R)),counts=compact,full_gate_pass=data['gates'][e['model']]['passed'],next='Parentcomparematchedbudgets and stageevidence beforeadaptation')
   print(json.dumps(dict(model=e['model'],counts=compact)),flush=True);done.append(e)
  for e in done:entries.remove(e)
  if entries:time.sleep(20)
 record('evidence_collector_finished',pending=[e['name'] for e in entries],next='Researchdecision remainswithparent; collectorcompletion isnotgoalcompletion')
if __name__=='__main__':main()
