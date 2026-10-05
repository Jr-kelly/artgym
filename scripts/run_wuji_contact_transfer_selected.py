"""One entry for retained demo, development contrasts and frozen joint trials.
Simulation only. Guard is explicitly a failed development path, never promotion.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path
from scripts.run_wuji_singlepush_selected import selection,command
D=Path('research/contact-transfer-20261006');B=Path('runs/contact-transfer-20261006')
def build(case,output,no_video=False,load='reference'):
 s=selection();options=[];kwargs={}
 if case in ['upper-geometry-friction','mid-high-delay']:
  f=json.loads((D/'FROZEN-JOINT-VALIDATION.json').read_text())
  for path,sha in f['required_sha256'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
  row=next(r for r in f['entries'] if r['name']==case);prep=B/'frozen'/case/'preparation';kwargs=dict(prepared=str(prep/'pickup'),operation=str(prep/'operation'),asset=row['asset_directory']+'/mobility.urdf',resistance=row['asset_directory']+'/resistance.json');options=row['native_options']
 elif case in ['near-small','near-small-guard']:
  prep=B/'preparation/near-small-prefix-v1';asset='assets/objects/knife_wuji_singlepush_20261005/frozen-v1/near-small';kwargs=dict(prepared=str(prep/'pickup'),operation=str(prep/'operation'),asset=asset+'/mobility.urdf',resistance=asset+'/resistance.json');options=['--stroke-m','.034']
  if case=='near-small-guard':options+=['--target-clearance-spec',str(prep/'operation/estimated-collision/spec.json')]
 elif case in ['large-baseline','large-center']:
  prep=Path('runs/singlepush-20261005/preparation/development-large28-v1') if case=='large-baseline' else B/'preparation/large-centered35-v9';asset='assets/objects/knife_wuji_newknife_20261005/heldout-v1/large-high';kwargs=dict(prepared=str(prep/'pickup'),operation=str(prep/'operation'),asset=asset+'/mobility.urdf',resistance=asset+'/resistance.json');options=['--stroke-m','.028' if case=='large-baseline' else '.035']
 else:assert case=='nominal'
 c=command(s,output,no_video,load,options=options,**kwargs);c[2]='scripts.run_wuji_contact_transfer';return c
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal','near-small','near-small-guard','large-baseline','large-center','upper-geometry-friction','mid-high-delay'],default='nominal');p.add_argument('--output',type=Path,required=True);p.add_argument('--no-video',action='store_true');p.add_argument('--load',choices=['reference','1.0','1.25','1.5'],default='reference');a=p.parse_args();assert a.case=='nominal' or a.load=='reference','Load label only selects nominal physics capacity; actor has no load ID';subprocess.run(build(a.case,a.output,a.no_video,a.load),check=True)
