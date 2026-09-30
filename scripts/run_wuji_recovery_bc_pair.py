"""Same-data, same-Adam/RNG paired segment, only raw versus executed labels differ."""
import argparse,json,subprocess,sys,time,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--end-epoch',type=int,required=True);p.add_argument('--previous-epoch',type=int,default=100);p.add_argument('--name',required=True);p.add_argument('--previous-name');p.add_argument('--max-seconds',type=int,default=1500);a=p.parse_args()
    out=R/'runs/artmanip-recovery-20260930'/a.name;out.mkdir(parents=True,exist_ok=False)
    data=[str(R/f'runs/unified-policy-20260930/train-data-t{sec}/source{s}') for s in range(4) for sec in [2,5]]
    initial=R/'runs/unified-policy-20260930/bc-unified-historical-s3001-seg1/epoch_000100.pth'
    paths={}
    for arm,label in [('M','mu'),('E','executed')]:
        init=initial if a.previous_epoch==100 else R/'runs/artmanip-recovery-20260930'/a.previous_name/arm/f'epoch_{a.previous_epoch:06d}.pth'
        cmd=[sys.executable,'-m','scripts.train_wuji_recovery_bc','--resume','--init',str(init),'--data']+data+['--output',str(out/arm),'--label',label,'--epochs',str(a.end_epoch),'--save-every','100','--lr','.00001','--seed','2026093001','--max-seconds',str(a.max_seconds)]
        (out/(arm+'-command.json')).write_text(json.dumps(dict(command=cmd,init_sha256=hashlib.sha256(init.read_bytes()).hexdigest()),indent=2)+'\n')
        with (out/(arm+'.log')).open('w') as f:subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=a.max_seconds+180,check=True)
        completed=json.loads((out/arm/'completed.json').read_text());assert completed['epoch']==a.end_epoch,completed
        paths[arm]=str((out/arm/f'epoch_{a.end_epoch:06d}.pth').relative_to(R))
    (out/'completed.json').write_text(json.dumps(dict(paths=paths,time=time.time(),added_updates=(a.end_epoch-a.previous_epoch)*8))+'\n')
    print(json.dumps(paths))
if __name__=='__main__':main()
