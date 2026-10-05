"""New frozen joint validation; same actor/controller and estimate-only adaptation."""
import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
from scripts.run_wuji_singlepush_selected import selection,command

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--prepared',type=Path,help='Reuse previously generated immutable estimate-only preparation');a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True);s=selection();manifest=json.loads(Path('research/singlepush-20261005/NECESSARY-FROZEN-CASES-v1.json').read_text());case=next(r for r in manifest['entries'] if r['name']==a.case)
 for name,sha in case['hashes'].items():assert hashlib.sha256((Path(case['asset_directory'])/name).read_bytes()).hexdigest()==sha,name
 prep=a.prepared or a.output/'preparation';result=dict(case=a.case,split='new-frozen-joint-validation',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection_sha256=hashlib.sha256(Path('research/singlepush-20261005/FROZEN-CANDIDATE.json').read_bytes()).hexdigest(),scope=__doc__,real_robot_ran=False)
 if not a.prepared:
  c=[sys.executable,'-m','scripts.prepare_wuji_newknife_case','--stroke-m',str(s['stroke_m']),'--postlift-only-stroke','--estimate',case['initial_estimate'],'--recipe',s['geometry_recipe'],'--output',str(prep)]
  with (a.output/'preparation.log').open('w') as f:code=subprocess.call(c,stdout=f,stderr=subprocess.STDOUT)
 else:code=0
 e=json.loads((prep/'preparation-result.json').read_text());result['preparation']=e;result['preparation_exit_code']=code
 if e['passed'] and not code:
  assert e['estimate_sha256']==hashlib.sha256(Path(case['initial_estimate']).read_bytes()).hexdigest();assert e['recipe_sha256']==s['required_sha256'][s['geometry_recipe']]
  c=command(s,a.output/'physical',True,prepared=e['prepared'],operation=e['operation_prepared'],asset=str(Path(case['asset_directory'])/'mobility.urdf'),resistance=str(Path(case['asset_directory'])/'resistance.json'),options=case['native_options']);result['command']=c
  with (a.output/'physical.log').open('w') as f:code=subprocess.call(c,stdout=f,stderr=subprocess.STDOUT)
  result['physical_exit_code']=code;ev=a.output/'physical/simulation/extension-evaluation.json';result['evaluation']=json.loads(ev.read_text()) if ev.exists() else None;result['pass_all']=bool(result['evaluation'] and result['evaluation']['pass_all'])
 else:result.update(pass_all=False,evaluation=None,failure='Actual required postlift path preparation rejected; no physical execution')
 result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
