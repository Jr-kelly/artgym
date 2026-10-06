"""Read existing segment evidence; no rerun and no success inferred from root height."""
import argparse,json
from pathlib import Path
from collections import defaultdict
import numpy as np
def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();z=np.load(a.directory/'trace.npz');b=defaultdict(list)
 for line in (a.directory/'knife-contact-pairs.jsonl').open():
  r=json.loads(line)
  if r.get('solver_lambda',0)>1e-5:
   key=r['body1'] if r['body0'].startswith('link_') else r['body0'];b[key].append(r['time_s'])
 result=dict(object_initial=z['object'][0,:7].tolist(),object_final=z['object'][-1,:7].tolist(),root_displacement_m=float(np.linalg.norm(z['object'][-1,:3]-z['object'][0,:3])),slider_range_m=[float(z['slider'].min()),float(z['slider'].max())],contact_time_ranges={k:dict(first=min(v),last=max(v),frames=len(set(v))) for k,v in b.items()},scope='Native contact and recorded movement summary; root height alone is not whole-knife lift proof.')
 out=a.directory/'native-segment-summary.json';out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
