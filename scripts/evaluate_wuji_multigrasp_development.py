"""Apply the preregistered common development rule after fixed-budget training."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];BASE=R/'runs/multigrasp-20260928'
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=list('ABCD'),required=True);p.add_argument('--gpu',type=int,required=True);a=p.parse_args();name='mg_'+a.arm+'_seed2801';span=.04 if a.arm in 'AB' else .20
 out=BASE/('development-'+a.arm);out.mkdir(exist_ok=False);rows=[];status=BASE/name/'status.json'
 train=json.loads(status.read_text());assert train['status']=='completed',train
 for cp in [250,500,750,1000]:
  checkpoint=R/'runs'/name/'checkpoints'/('epoch_%06d.pth'%cp);assert checkpoint.exists(),checkpoint
  for seconds in [2,5]:
   job='dev-'+a.arm+'-cp'+str(cp)+'-t'+str(seconds);evidence=BASE/job/'evidence'
   command=[sys.executable,'-m','scripts.run_multigrasp_job','--name',job,'--gpu',str(a.gpu),'--timeout','1800','--','PYTHON','-m','scripts.audit_wuji_multigrasp','--checkpoint',str(checkpoint),'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states','research/multigrasp-20260928/data/dev-perturb.npy','--span',str(span),'--stage-seconds',str(seconds),'--output',str(evidence)]
   subprocess.run(command,cwd=R,check=True)
   report=json.loads((evidence/'report.json').read_text());assert report['num_envs']==128
   score=report['stable_full_all_endpoints']/128
   rows.append(dict(cp=cp,seconds=seconds,score=score,strict=report['stable_full_all_endpoints'],alive=report['alive_full'],path=str(evidence.relative_to(R)),checkpoint_sha256=report['checkpoint_sha256']))
   (out/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
 scores={cp:sum(x['score'] for x in rows if x['cp']==cp)/2 for cp in [250,500,750,1000]};selected=max(scores,key=lambda cp:(scores[cp],cp));checkpoint=R/'runs'/name/'checkpoints'/('epoch_%06d.pth'%selected)
 result=dict(status='frozen',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),arm=a.arm,seed=2026092801,span=span,cp=selected,checkpoint=str(checkpoint.relative_to(R)),sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),scores=scores,rows=rows,rule='max equally weighted16union-training-record dev strict2/5s; tie latest; blind test not read',formal_training_interactions=163840000)
 (out/'frozen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
