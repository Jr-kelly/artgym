import numpy as np,json,hashlib
from pathlib import Path
r=Path.cwd();d=r/'research/geometry-generalization-20261002';old=json.loads((r/'research/unified-student-20261001/data/manifest.json').read_text());excluded=set(h for e in old['entries'] for h in e['row_sha256']);seen=set();n=0
for e in json.loads((d/'DATA.json').read_text())['entries']:
 if e['split'].startswith('final'):continue
 for row in np.load(r/e['path']):
  h=hashlib.sha256(row.tobytes()).hexdigest();assert h not in excluded
  key=(e['label'],h);assert key not in seen;seen.add(key);n+=1
(d/'data-disjointness-audit.json').write_text(json.dumps(dict(new_nonfinal_rows=n,historical_hashes_only=len(excluded),overlaps=0,old_final_arrays_accessed=False,new_final_arrays_accessed=False,geometry_lineage_duplicates='Allowed across distinct assets, not within a geometry'),indent=2)+'\n')
