"""Whole-object support gate for flat-table sequences; old root gate retained separately."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np

def evaluate(trial):
 z=np.load(trial/'trace.npz');times=z['time'];start=12.;end=float(times[-1]);contacts=[]
 for l in (trial/'knife-contact-pairs.jsonl').open():
  x=json.loads(l)
  if start<=x['time_s']<=end and 'table' in [x['body0'],x['body1']] and x['solver_lambda']>1e-5:contacts.append(x)
 e=json.loads((trial/'extension-evaluation.json').read_text());r=dict(version='flat-table-whole-object-v1',hold_start_stage_s=start,table_contact_records_after_lift=len(contacts),table_support_absent_after_lift=not contacts,legacy_root_pickup_gate=e['checks']['continuous_pickup'],whole_pickup=not contacts and e['checks']['continuous_pickup'],active_forward_m=e['active_forward_m'],hold_min_active_m=e['hold_min_active_m'],continuous_success=not contacts and e['pass_all'],trace_sha256=hashlib.sha256((trial/'trace.npz').read_bytes()).hexdigest(),scope='Native knife/table contact gate across explicit pickup hold and operation; rotation can lift root while blade stays supported, which is rejected.')
 (trial/'flat-table-evaluation.json').write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);a=p.parse_args();print(json.dumps(evaluate(a.trial)))
