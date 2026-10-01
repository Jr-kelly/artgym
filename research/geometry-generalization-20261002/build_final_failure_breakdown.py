"""Descriptive failure decomposition at registered thresholds; no new success gate."""
from pathlib import Path
import json,csv
import numpy as np
D=Path(__file__).resolve().parent
R=D.parents[1]
analysis=json.loads((D/'final-analysis/report.json').read_text());assert len(analysis['runs'])==78
records=[]
for name in analysis['runs']:
 directory=R/name
 receipt=json.loads((directory/'geometry-receipt.json').read_text());report=json.loads((directory/'report.json').read_text());geometry=receipt['asset']['parameters']['label'];selection=json.loads((R/'runs/geometry-generalization-20261002'/(geometry+'-static-final')/'selection.json').read_text());expected=1200 if receipt['protocol']=='F' else 600
 with np.load(directory/'trace.npz') as z:
  keys=['active','fall','invalid','drift','rotation'];t={k:z[k] for k in keys}
 for i,source in enumerate(selection['source_order']):
  causes={'translation':t['drift'][:,i]>=.01,'rotation':t['rotation'][:,i]>=.25,'fall':t['fall'][:,i].astype(bool),'invalid':t['invalid'][:,i].astype(bool),'inactive':~t['active'][:,i].astype(bool),'nonfinite':~np.isfinite(t['drift'][:,i])|~np.isfinite(t['rotation'][:,i])}
  anybad=np.logical_or.reduce(list(causes.values()));indices=np.flatnonzero(anybad)
  first=int(indices[0]) if len(indices) else None;first_types=[k for k,v in causes.items() if first is not None and v[first]]
  records.append(dict(geometry=geometry,model=receipt['model'],protocol=receipt['protocol'],source=source,attempt_row=selection['selected_attempt_rows'][i],first_failure_s=(first+1)/30 if first is not None else None,first_failure_types='+'.join(first_types),translation_breach=bool(causes['translation'].any()),rotation_breach=bool(causes['rotation'].any()),fall=bool(causes['fall'].any()),invalid=bool(causes['invalid'].any()),truncated=len(t['active'])!=expected,scope='Registered full-horizon holding failures only, descriptive diagnostic; no changed success definition'))
rows=[]
for key in sorted({tuple(r[k] for k in ['geometry','model','protocol','source']) for r in records}):
 group=[r for r in records if tuple(r[k] for k in ['geometry','model','protocol','source'])==key];types={}
 for r in group:
  name=r['first_failure_types'] or ('truncated' if r['truncated'] else 'none');types[name]=types.get(name,0)+1
 rows.append(dict(zip(['geometry','model','protocol','source'],key),n=len(group),first_failure_types=types,**{k:sum(r[k] for r in group) for k in ['translation_breach','rotation_breach','fall','invalid','truncated']}))
for name,data in [('failure-episodes.csv',records),('failure-cells.csv',rows)]:
 with (D/'final-analysis'/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
(D/'final-analysis/failure-breakdown.json').write_text(json.dumps(dict(rows=rows,scope='Overlapping ever-breach counts; first-failure categories are mutually exclusive strings and may list simultaneous causes. Not causal attribution or a new success gate.'),indent=2)+'\n')
print('Failure breakdown:',len(records),'episode protocol records')
