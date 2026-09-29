"""Bounded BC segment plus same-device development checks at its two milestones.

The caller applies stage gates between segments. This script never selects or
runs a new method and never reads the final split.
"""
import argparse,datetime,json,os,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/'runs/unified-policy-20260930'
def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--init',required=True);p.add_argument('--start-epoch',type=int,default=0);p.add_argument('--end-epoch',type=int,default=100);p.add_argument('--lr',default='.00001');p.add_argument('--seed',type=int,default=2026093001);p.add_argument('--resume',action='store_true');a=p.parse_args();assert a.end_epoch-a.start_epoch==100
 manifest=B/(a.name+'-orchestration.json');assert not manifest.exists();mid=a.start_epoch+50;checkpoints=[mid,a.end_epoch];records=[];children=[]
 data=[f'runs/unified-policy-20260930/train-data-t{sec}/source{source}' for source in range(4) for sec in [2,5]]
 def launch(label,gpu,timeout,args):
  cmd=[sys.executable,'-m','scripts.run_wuji_unified_job','--name',label+'-job','--gpu',str(gpu),'--timeout',str(timeout),'--','PYTHON',*args]
  with (B/(label+'-wrapper.log')).open('w') as f:proc=subprocess.Popen(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  children.append(proc);records.append(dict(label=label,pid=proc.pid,gpu=gpu,command=cmd,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()));manifest.write_text(json.dumps(records,indent=2)+'\n');return proc
 trainargs=['-m','scripts.train_wuji_unified_bc','--init',a.init,'--data',*data,'--output',f'runs/unified-policy-20260930/{a.name}','--epochs',str(a.end_epoch),'--save-every','50','--lr',a.lr,'--seed',str(a.seed),'--max-seconds','2200']
 if a.resume:trainargs+=['--resume']
 training=launch(a.name,0,2400,trainargs);deadline=time.time()+2400
 def wait_cp(epoch):
  cp=B/a.name/f'epoch_{epoch:06d}.pth'
  while time.time()<deadline:
   if cp.exists():return str(cp.relative_to(R))
   if training.poll() is not None:raise RuntimeError('Training stopped before required checkpoint')
   time.sleep(1)
  raise TimeoutError('Checkpoint wait')
 cp_mid=wait_cp(mid)
 # GPU1 starts fixed5 at the first immutable milestone while GPU0 completes BC.
 ev5=[]
 for epoch in checkpoints:
  cp=wait_cp(epoch);label=f'{a.name}-dev-t5-cp{epoch}'
  ev5.append(launch(label,1,1100,['-m','scripts.evaluate_wuji_unified_gate','--stage',label,'--states','research/unified-policy-20260930/data/development-all.npy','--seconds','5','--models',f'cp{epoch}={cp}']))
  # Sequential per-device execution is enforced here, not by racing GPU leases.
  if epoch==mid:
   training.wait(timeout=max(1,deadline-time.time()));assert training.returncode==0
   cp_end=wait_cp(a.end_epoch);label2=f'{a.name}-dev-t2'
   ev2=launch(label2,0,2200,['-m','scripts.evaluate_wuji_unified_gate','--stage',label2,'--states','research/unified-policy-20260930/data/development-all.npy','--seconds','2','--models',f'cp{mid}={cp_mid}',f'cp{a.end_epoch}={cp_end}'])
  ev5[-1].wait(timeout=1200);assert ev5[-1].returncode==0
 ev2.wait(timeout=2300);assert ev2.returncode==0
 (B/(a.name+'-segment-completed.json')).write_text(json.dumps(dict(status='completed',records=records,checkpoint_epochs=checkpoints,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))+'\n')
if __name__=='__main__':main()
