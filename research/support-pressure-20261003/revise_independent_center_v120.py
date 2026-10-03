"""Explicit pre-freeze correction of unexecuted independent initial estimates."""
import json,numpy as np
from scripts.record_wuji_support_goal import D,record
p=D/'new-independent-definitions-v120-revision1.json';assert not p.exists(),'Existing frozen definitions must not be overwritten'
d=json.loads((D/'new-independent-definitions-v120.json').read_text());rng=np.random.default_rng(2026100469)
for row in d['entries']:
 e=row['estimate'];size=e['handle_size_WTL_m'];e['initial_object_center_shift_knife_m']=(np.array([0,(size[1]-.012)/2,0])+rng.uniform(-1,1,3)*[.0003,.0004,.0006]).tolist();e['initial_center_estimation_error_assumption_m']=[.0003,.0004,.0006];e['source']+=' Initial center also noisy and derived from estimated thickness; no exact physical center given to controller.'
d['revision']='Initial center estimate uses noisy estimatedthickness and explicit independentposeerror; originalunexecuted definitionspreserved';d['center_noise_seed']=2026100469;p.write_text(json.dumps(d,indent=2));record('new_independent_initial_center_revision1_rebuilt',evidence=str(p.relative_to(D.parent.parent)),next='Run only after candidate/controlfreeze')
