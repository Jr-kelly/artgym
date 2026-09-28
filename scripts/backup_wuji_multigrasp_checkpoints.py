"""Bounded backup of complete immutable milestones; never touches training processes."""
import argparse,datetime,hashlib,json,shlex,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-i','/home/agiuser/.ssh/id_ed25519_h200','-o','IdentitiesOnly=yes','-p','30296','wangjiarui@10.14.0.93']
REMOTE='/home/wangjiarui/artgym-multigrasp-20260928'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=27000);a=p.parse_args();start=time.monotonic();done={}
 out=R/'research/multigrasp-20260928/receipts/checkpoint-backups';out.mkdir(exist_ok=False)
 while time.monotonic()-start<a.seconds and len(done)<16:
  pending=[(arm,epoch) for arm in 'ABCD' for epoch in [250,500,750,1000] if arm+'-'+str(epoch) not in done]
  code='import pathlib,json,hashlib; r=pathlib.Path('+repr(REMOTE)+'); rows=[]\nfor arm,epoch in '+repr(pending)+':\n p=r/"runs"/("mg_"+arm+"_seed2801")/"checkpoints"/("epoch_%06d.json"%epoch)\n if p.exists():\n  meta=json.loads(p.read_text()); f=p.with_suffix(".pth"); rows.append(dict(arm=arm,epoch=epoch,metadata=meta,relative=str(f.relative_to(r)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))\nprint(json.dumps(rows))'
  try:
   rows=json.loads(subprocess.check_output(SSH+['/home/wangjiarui/artgym-runtime/bin/python -c '+shlex.quote(code)],text=True,timeout=40))
   for row in rows:
    target=R/row['relative'];target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['rsync','-a','-e',shlex.join(SSH[:-1]),SSH[-1]+':'+REMOTE+'/'+row['relative'],str(target)],check=True,timeout=180)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']
    key=row['arm']+'-'+str(row['epoch']);row.update(verified_utc=now(),local=str(target));done[key]=row
    (out/(key+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    subprocess.run(['python3','-m','scripts.record_wuji_multigrasp_event','--event','milestone_backup_verified','--summary','Backed up immutable '+key+' with identical remote/local SHA256; not evaluated or selected.','--evidence',str(out/(key+'.json')),'--next','Continue fixed1000epoch training and preregistered development selection'],cwd=R,check=True)
   (out/'status.json').write_text(json.dumps(dict(updated=now(),status='completed' if len(done)==16 else 'waiting_milestones',count=len(done),expected=16,records=done),indent=2)+'\n')
  except Exception as exc:
   with (out/'errors.jsonl').open('a') as f:f.write(json.dumps(dict(time=now(),error=repr(exc)))+'\n')
  if len(done)<16:time.sleep(60)
if __name__=='__main__':main()
