"""Bounded real command check on a restored public checkout, with explicit provenance."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=a.source.resolve();a.output.mkdir(parents=True,exist_ok=False);manifest=json.loads((source/'RESTORE_SOURCE.json').read_text())
 for e in manifest['files']:assert hashlib.sha256((source/e['path']).read_bytes()).hexdigest()==e['sha256'],e['path']
 expected=dict(teacher='2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8',student='16202c4ee4c60d37391108ebb9318fd9d4e1eb4cecbaef21965d5249f1328bf9');commands=[];reports=[]
 for model in ['teacher','student']:
  directory=a.output/model;command=[sys.executable,'-m','scripts.evaluate_wuji_geometry','--label','baseline','--states','research/geometry-generalization-20261002/data/baseline/adapted-seeds.npy','--model',model,'--protocol','S2','--output',str(directory.resolve())]
  commands.append(command);subprocess.run(command,cwd=source,check=True);r=json.loads((directory/'report.json').read_text());receipt=json.loads((directory/'geometry-receipt.json').read_text());assert r['checkpoint_sha256']==expected['teacher'] and receipt['model_unchanged']
  if model=='student':assert r['unified_student_sha256']==expected['student']
  assert r['recorded_steps']==600 and len(r['records'])==4;reports.append(dict(model=model,initial_states_sha256=r['initial_states_sha256'],results=r['records'],source_sha256=r['source_sha256'],actual_asset=receipt['asset']['object']))
 assert reports[0]['initial_states_sha256']==reports[1]['initial_states_sha256']
 result=dict(passed=True,actual_scientific_source=str(source),actual_public_commit=manifest['public_git_commit'],actual_code_sha256=manifest['code_sha256'],driver_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),commands=commands,reports=reports,scope='Restored GitHubdraft-byte models/assets on fresh public source; 4knowntrainingseed S2episodes permodel. Command/restoreverification only; not new finaldata or extra capability statistical samples. Launcher pin identifies thisdriver; scientific source override is explicit.')
 (a.output/'restore-smoke.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='reports'}))
if __name__=='__main__':main()
