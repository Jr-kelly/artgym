"""Bounded single-grasp diagnostic preserving the matrix physics and PPO setup."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1]
B=R/'runs/multigrasp-20260928'
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-row',type=int,required=True)
    p.add_argument('--gpu',type=int,required=True);p.add_argument('--name',required=True)
    p.add_argument('--seed',type=int,default=2026092810);p.add_argument('--epochs',type=int,default=1000)
    a=p.parse_args();assert 0<=a.source_row<16 and 1<=a.epochs<=1000
    assert not (R/'runs'/a.name).exists() and not (B/a.name).exists()
    data=R/'research/multigrasp-20260928/data'/('expert-'+str(a.source_row)+'.npy')
    states=np.load(R/'research/multigrasp-20260928/data/candidates.npy')[a.source_row:a.source_row+1]
    if data.exists():assert np.array_equal(np.load(data),states)
    else:np.save(data,states)
    # Reuse exact recorded matrix A overrides, replacing only diagnostic identity,
    # singleton source pool, seed, and explicitly bounded epoch count.
    original=json.loads((B/'mg_A_seed2801/status.json').read_text())['command']
    overrides=original[3:]
    replacement={'experiment':a.name,'seed':str(a.seed),'max_iterations':str(a.epochs),
        'task.env.trainingStates':str(data.relative_to(R))}
    overrides=[x.split('=',1)[0]+'='+replacement[x.split('=',1)[0]] if x.split('=',1)[0] in replacement else x for x in overrides]
    command=[sys.executable,'-m','scripts.run_multigrasp_job','--name',a.name,'--gpu',str(a.gpu),
        '--timeout','14400','--','PYTHON','-m','scripts.train_wuji_multigrasp']+overrides
    receipt=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_row=a.source_row,
        training_pool_sha256=hashlib.sha256(data.read_bytes()).hexdigest(),seed=a.seed,
        span=.04,epochs=a.epochs,interactions=a.epochs*163840,command=command,
        scope='Single-grasp learnability diagnosis; random initialization, unchanged A physics/reward/network. Not another factorial arm or independent-seed replication of the matrix.')
    (B/(a.name+'-spec.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    subprocess.run(command,cwd=R,check=True)
if __name__=='__main__':main()
