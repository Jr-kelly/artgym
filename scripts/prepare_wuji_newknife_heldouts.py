"""Predeclare three local-neighbor heldouts, never added to training registry.
Assets and noisy once-estimates only; no physics or success evidence generated.
"""
import json,hashlib
from pathlib import Path
import numpy as np
from scripts.build_wuji_newknife import build

def main():
 root=Path('assets/objects/knife_wuji_newknife_20261005/heldout-v1');assert not root.exists();rows=[];rng=np.random.default_rng(2026100521)
 configs=[dict(name='small-low',length=.140,width=.018,thickness=.007,slider_length=.030,slider_width=.006,protrusion=.0015,proximal=.025,mass=.050,reference_N=.55,kind='constant'),dict(name='large-high',length=.148,width=.020,thickness=.009,slider_length=.034,slider_width=.008,protrusion=.0025,proximal=.035,mass=.060,reference_N=.95,kind='constant'),dict(name='middle-variable',length=.146,width=.0188,thickness=.0085,slider_length=.031,slider_width=.0068,protrusion=.0018,proximal=.028,mass=.053,reference_N=.82,kind='variable')]
 for config in configs:
  c=dict(config);name=c.pop('name');force=c.pop('reference_N');kind=c.pop('kind');out=root/name;build(out,**c)
  estimate=json.loads((out/'once-estimate.json').read_text());estimate['handle_size_WTL_m']=(np.array(estimate['handle_size_WTL_m'])+rng.uniform(-1,1,3)*[.00015,.00010,.00020]).tolist();estimate['slider_size_WTL_m']=(np.array(estimate['slider_size_WTL_m'])+rng.uniform(-1,1,3)*[.00010,.00008,.00015]).tolist();estimate['slider_contact_shift_m']=(np.array(estimate['slider_contact_shift_m'])+rng.uniform(-1,1,3)*[.0001,.00008,.0003]).tolist();estimate['source']='Synthetic once-initial sensor from heldout dimensions, noise seed2026100521; no live state/contact/force, not actual perception';(out/'noisy-once-estimate.json').write_text(json.dumps(estimate,indent=2))
  profile=dict(kind=kind,reference_N=force,damping_Ns_m=25000,reference_statistic='constant capacity' if kind=='constant' else 'mean forward running capacity; directional/startup/spatial assumptions retained',scope='Predeclared necessary-neighbor engineering sensitivity, no measured curve');(out/'resistance.json').write_text(json.dumps(profile,indent=2));rows.append(dict(name=name,split='heldout',asset_directory=str(out),physical_parameters=c,profile=profile,initial_estimate=str(out/'noisy-once-estimate.json'),hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()}))
 manifest=dict(scope=__doc__,seed=2026100521,entries=rows,execution_gate='Only after candidate selection frozen; do not retune on these outcomes',actor_asset_id_input=False,training_registry='runs/newknife-20261005/batch/config/registry.json');Path('research/newknife-20261005/NECESSARY-HELDOUTS-v1.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
