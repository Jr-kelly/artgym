"""Frozen four-arm plus historical-reference evaluation on exactly shared states/GPU."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];BASE=R/'runs/multigrasp-20260928'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--states',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--gpu',type=int,required=True);p.add_argument('--label',required=True);p.add_argument('--selection',choices=['development','final1000'],default='development');a=p.parse_args()
 # The state manifest supplies immutable source IDs and cohort labels for every row.
 import numpy as np
 states=np.load(a.states);mapping=json.loads(a.manifest.read_text())
 assert mapping['states_sha256']==sha(a.states) and len(mapping['rows'])==len(states)
 out=BASE/a.label;out.mkdir(exist_ok=False);models=[]
 for arm in 'ABCD':
  frozen=json.loads((BASE/('development-'+arm)/'frozen.json').read_text());cp=R/frozen['checkpoint']
  assert frozen['status']=='frozen' and sha(cp)==frozen['sha256']
  if a.selection=='final1000':
   cp=R/'runs'/('mg_'+arm+'_seed2801')/'checkpoints/epoch_001000.pth'
   metadata=json.loads(cp.with_suffix('.json').read_text())
   assert metadata['epoch']==1000 and metadata['frame']==163840000
   frozen=dict(frozen,checkpoint=str(cp.relative_to(R)),sha256=sha(cp),cp=1000,rule='fixed final1000; identical163840000traininginteractions for every arm')
  models.append(dict(label=arm,checkpoint=str(cp),sha256=frozen['sha256'],span=frozen['span'],freeze=frozen))
 ref=BASE/'reference.pth';assert sha(ref)=='4d8af0637a29787811b5ab2251425ddc79382dce2f84ae00708455b1149890ac'
 models.append(dict(label='reference',checkpoint=str(ref),sha256=sha(ref),span=.04))
 plan=dict(selection=a.selection,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),states_sha256=sha(a.states),mapping_sha256=sha(a.manifest),gpu=a.gpu,models=models,protocols=['static20s','fixed2s','fixed5s','arrival10mm20s'],scope='fixed models, identical state ordering and physics; no subsequent checkpoint selection on this cohort')
 (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');results=[]
 jobs=[(models[-1],'static')]+[(m,protocol) for m in models for protocol in ['fixed2','fixed5','arrival']]
 for m,protocol in jobs:
  label=a.label+'-'+m['label']+'-'+protocol;evidence=BASE/label/'evidence'
  module='scripts.audit_wuji_multigrasp_arrival' if protocol=='arrival' else 'scripts.audit_wuji_multigrasp'
  args=['--checkpoint',m['checkpoint'],'--task','wuji_multigrasp','--hand','wuji_paper_official_actuator','--object','knife_wuji_bridge3_20260922','--initial-states',str(a.states),'--span',str(m['span']),'--output',str(evidence),'--seed','2026092807']
  args+=['--total-seconds','20'] if protocol=='arrival' else ['--stage-seconds','5' if protocol=='fixed5' else '2']
  if protocol=='static':args+=['--static']
  cmd=[sys.executable,'-m','scripts.run_multigrasp_job','--name',label,'--gpu',str(a.gpu),'--timeout','1800','--','PYTHON','-m',module]+args
  subprocess.run(cmd,cwd=R,check=True)
  report=json.loads((evidence/'report.json').read_text());assert report['checkpoint_sha256']==m['sha256'] and report['initial_states_sha256']==sha(a.states)
  results.append(dict(model=m['label'],protocol=protocol,evidence=str(evidence.relative_to(R)),report=report))
  (out/'results.json').write_text(json.dumps(dict(status='running',plan=plan,results=results),indent=2)+'\n')
 (out/'results.json').write_text(json.dumps(dict(status='completed',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan=plan,results=results),indent=2)+'\n')
if __name__=='__main__':main()
