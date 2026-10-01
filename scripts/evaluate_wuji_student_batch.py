"""Serial paired protocols for immutable student artifacts on one assigned GPU."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--teacher',required=True);p.add_argument('--models',nargs='+',required=True);p.add_argument('--states',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--protocols',nargs='+',default=['S2','S5','F']);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 plan=dict(teacher=a.teacher,models=a.models,states=a.states,protocols=a.protocols);(a.output/'plan.json').write_text(json.dumps(plan,indent=2));results=[]
 for entry in a.models:
  name,path=entry.split('=',1)
  if path!='teacher':
   artifact=Path(path);assert artifact.with_suffix('.sha256').read_text().strip()==hashlib.sha256(artifact.read_bytes()).hexdigest()
  for protocol in a.protocols:
   dest=a.output/(name+'-'+protocol)
   cmd=[sys.executable,'-m','scripts.evaluate_wuji_recovery','--checkpoint',a.teacher,'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--seed','2026093031','--initial-states',a.states,'--output',str(dest),'--stage-seconds','5' if protocol=='S5' else '2','--protocol','F' if protocol=='F' else 'S']
   if path!='teacher':
    cmd+=['--unified-student',path]
    if protocol=='S2':cmd+=['--holdout-probes','runs/unified-student-20261001/teacher-legal-S2/latent-probes.pth','runs/unified-student-20261001/teacher-legal-S5/latent-probes.pth']
   subprocess.run(cmd,check=True)
   report=json.loads((dest/'report.json').read_text());results.append(dict(model=name,protocol=protocol,directory=dest.name,report=report,command=cmd))
   (a.output/'results.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
