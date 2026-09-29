"""One protocol/device, explicit equal initial states and batch size for every model."""
import argparse,subprocess,sys,json,hashlib,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--states',required=True);p.add_argument('--seconds',type=int,choices=[2,5],required=True);p.add_argument('--models',nargs='+',required=True);p.add_argument('--static',action='store_true');a=p.parse_args()
 out=R/'runs/unified-policy-20260930'/a.stage;out.mkdir(parents=True,exist_ok=False)
 models={x.split('=',1)[0]:x.split('=',1)[1] for x in a.models}
 plan=dict(states=a.states,states_sha256=hashlib.sha256((R/a.states).read_bytes()).hexdigest(),seconds=a.seconds,models={k:dict(path=v,sha256=hashlib.sha256((R/v).read_bytes()).hexdigest()) for k,v in models.items()})
 (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');results=[]
 jobs=list(models.items())
 if a.static:jobs.insert(0,('static',next(iter(models.values()))))
 for name,cp in jobs:
  dest=out/name;cmd=[sys.executable,'-m','scripts.audit_wuji_multigrasp' if name=='static' else 'scripts.collect_wuji_unified','--checkpoint',cp,'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',a.states,'--span','.04','--output',str(dest),'--seed','2026093030','--stage-seconds',str(a.seconds)]
  if name=='static':cmd+=['--static']
  with (out/(name+'.log')).open('w') as f:subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=900,check=True)
  result=json.loads((dest/'report.json').read_text());results.append(dict(model=name,report=result));(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 (out/'completed.json').write_text(json.dumps(dict(status='completed',time=time.time()))+'\n')
if __name__=='__main__':main()
