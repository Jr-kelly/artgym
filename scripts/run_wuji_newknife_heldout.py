"""One predeclared frozen nearby joint condition, with common initial adaptation.
Assets/load are simulator inputs only. Actor weights and recipe stay frozen.
"""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True);selection=json.loads(Path('research/newknife-20261005/FROZEN-CANDIDATE.json').read_text());manifest=json.loads(Path('research/newknife-20261005/NECESSARY-HELDOUTS-v1.json').read_text());case=next(r for r in manifest['entries'] if r['name']==a.case)
 for path,sha in selection['required_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
 recipe=Path(selection['geometry_recipe']);assert hashlib.sha256(recipe.read_bytes()).hexdigest()==selection['geometry_recipe_sha256']
 for name,sha in case['hashes'].items():assert hashlib.sha256((Path(case['asset_directory'])/name).read_bytes()).hexdigest()==sha,name
 result=dict(case=a.case,split='frozen-heldout',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope=__doc__,selection_sha256=hashlib.sha256(Path('research/newknife-20261005/FROZEN-CANDIDATE.json').read_bytes()).hexdigest(),checkpoint=selection.get('trained_checkpoint',selection['baseline_checkpoint']),recipe_sha256=selection['geometry_recipe_sha256'],real_robot_ran=False)
 cmd=[sys.executable,'-m','scripts.prepare_wuji_newknife_case','--estimate',case['initial_estimate'],'--recipe',str(recipe),'--output',str(a.output/'preparation')]
 with (a.output/'preparation.log').open('w') as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result['preparation_exit_code']=code
 if code:
  result.update(pass_all=False,failure='Original geometry/actuator preparation gate rejected; not physically executed',preparation=json.loads((a.output/'preparation/preparation-result.json').read_text()))
 else:
  prepared=json.loads((a.output/'preparation/preparation-result.json').read_text());cmd=[sys.executable,'-m','scripts.run_wuji_newknife','--prepared',prepared['prepared'],'--operation-prepared',prepared['operation_prepared'],'--asset',str(Path(case['asset_directory'])/'mobility.urdf'),'--resistance',str(Path(case['asset_directory'])/'resistance.json'),'--pressure',selection['pressure'],'--no-video','--output',str(a.output/'physical')]+selection.get('native_options',[])
  if selection.get('trained_checkpoint'):cmd+=['--checkpoint',selection['trained_checkpoint']]
  result['command']=cmd
  with (a.output/'physical.log').open('w') as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
  result['physical_exit_code']=code;ev=a.output/'physical/simulation/newknife-evaluation.json';result['evaluation']=json.loads(ev.read_text()) if ev.exists() else None;result['pass_all']=bool(result['evaluation'] and result['evaluation']['pass_all']);result['failure']=None if result['pass_all'] else 'Frozen full-task checks failed' if result['evaluation'] else 'Native runtime failed'
 result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
