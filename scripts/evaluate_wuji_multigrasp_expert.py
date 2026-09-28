"""Frozen final-checkpoint expert evaluation on independent source perturbations."""
import argparse,datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics
R=Path(__file__).resolve().parents[1];B=R/'runs/multigrasp-20260928'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--row',type=int,required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args()
    name='expert_row'+str(a.row)+'_seed2810';out=B/(name+'-evaluation');out.mkdir(exist_ok=False)
    deadline=datetime.datetime(2026,9,29,0,30,tzinfo=datetime.timezone.utc)
    while datetime.datetime.now(datetime.timezone.utc)<deadline:
        s=json.loads((B/name/'status.json').read_text())
        if s['status'] in ['completed','failed']:break
        time.sleep(20)
    else:raise TimeoutError('Expert training deadline')
    assert s['status']=='completed',s
    cp=R/'runs'/name/'checkpoints/epoch_001000.pth';meta=json.loads(cp.with_suffix('.json').read_text());assert meta['frame']==163840000 and meta['epoch']==1000
    source=R/'research/multigrasp-20260928/data'/('expert-'+str(a.row)+'.npy');hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
    states=states_for_seed(np.load(source),2026092820+a.row,hand,trials=32);np.save(out/'states.npy',states)
    plan=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkpoint=str(cp.relative_to(R)),checkpoint_sha256=sha(cp),states_sha256=sha(out/'states.npy'),source_row=a.row,seed=2026092820+a.row,scope='Final1000 only, independent32 perturbations of own training source; learnability fit diagnosis, not novel-grasp generalization')
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');results=[]
    for protocol in ['static','fixed2','fixed5','arrival']:
        label=name+'-'+protocol;evidence=B/label/'evidence';module='scripts.audit_wuji_multigrasp_arrival' if protocol=='arrival' else 'scripts.audit_wuji_multigrasp'
        args=['--checkpoint',str(cp),'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',str(out/'states.npy'),'--span','.04','--output',str(evidence),'--seed','2026092820']
        args+=['--total-seconds','20'] if protocol=='arrival' else ['--stage-seconds','5' if protocol=='fixed5' else '2']
        if protocol=='static':args+=['--static']
        subprocess.run([sys.executable,'-m','scripts.run_multigrasp_job','--name',label,'--gpu',str(a.gpu),'--timeout','600','--','PYTHON','-m',module]+args,cwd=R,check=True)
        report=json.loads((evidence/'report.json').read_text());results.append(dict(protocol=protocol,evidence=str(evidence.relative_to(R)),report=report))
    (out/'results.json').write_text(json.dumps(dict(status='completed',plan=plan,results=results),indent=2)+'\n')
if __name__=='__main__':main()
