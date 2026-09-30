"""F and S use independent complete physical episodes; no relabelled F traces."""
import argparse,json,subprocess,sys,hashlib,time,os
from pathlib import Path
from scripts.validate_wuji_recovery_final import validate_final_batch
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--states',required=True);p.add_argument('--models',nargs='+',required=True);p.add_argument('--protocols',nargs='+',default=['S2','S5','F']);p.add_argument('--static',action='store_true');a=p.parse_args()
    models=[x.split('=',1) for x in a.models];results=[]
    freeze_sha=validate_final_batch(R,a.states,models,a.protocols,os.environ.get('WUJI_RECOVERY_FINAL_PHASE')=='1',a.static)
    out=R/'runs/artmanip-recovery-20260930'/a.name;out.mkdir(parents=True,exist_ok=False)
    plan=dict(states=a.states,states_sha256=hashlib.sha256((R/a.states).read_bytes()).hexdigest(),models={k:dict(path=v,sha256=hashlib.sha256((R/v).read_bytes()).hexdigest()) for k,v in models},protocols=a.protocols,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if freeze_sha:plan['freeze_sha256']=freeze_sha
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    if a.static:models.insert(0,('static',models[0][1]))
    for model,cp in models:
        task='wuji_artmanip_reference' if model.startswith('rl') else 'wuji_multigrasp'
        for protocol in a.protocols:
            dest=out/(model+'-'+protocol)
            cmd=[sys.executable,'-m','scripts.evaluate_wuji_recovery','--checkpoint',cp,'--task',task,'--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',a.states,'--output',str(dest),'--seed','2026093031','--protocol',protocol[0],'--stage-seconds','5' if protocol=='S5' else '2']
            if model=='static':cmd+=['--static']
            with (out/(dest.name+'.log')).open('w') as f:subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=1200)
            results.append(dict(model=model,protocol=protocol,directory=dest.name,report=json.loads((dest/'report.json').read_text())))
            (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    (out/'completed.json').write_text(json.dumps(dict(time=time.time(),status='completed'))+'\n')
if __name__=='__main__':main()
