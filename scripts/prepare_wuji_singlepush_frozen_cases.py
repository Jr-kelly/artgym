"""Predeclare new unused joint conditions, before final controller selection/physics."""
import datetime,hashlib,json
from pathlib import Path
import numpy as np
from scripts.build_wuji_newknife import build

def main():
 root=Path('assets/objects/knife_wuji_singlepush_20261005/frozen-v1');assert not root.exists();rng=np.random.default_rng(2026100581);rows=[]
 configs=[dict(name='near-small',length=.142,width=.0185,thickness=.0075,slider_length=.031,slider_width=.0065,protrusion=.0017,proximal=.0285,mass=.052,reference_N=.65,kind='constant',options=['--observation-noise','.001']),dict(name='near-large',length=.147,width=.0196,thickness=.0087,slider_length=.0332,slider_width=.0076,protrusion=.0023,proximal=.033,mass=.058,reference_N=.90,kind='variable',options=['--hand-friction','.75','--knife-friction','1.7']),dict(name='shift-delay',length=.1445,width=.0192,thickness=.0081,slider_length=.0323,slider_width=.0071,protrusion=.0021,proximal=.0308,mass=.056,reference_N=.85,kind='variable',options=['--actuation-delay-frames','1','--observation-noise','.001','--observation-bias','.0005'])]
 for config in configs:
  c=dict(config);name=c.pop('name');force=c.pop('reference_N');kind=c.pop('kind');options=c.pop('options');out=root/name;build(out,**c);estimate=json.loads((out/'once-estimate.json').read_text())
  for key,bound in [('handle_size_WTL_m',[.00015,.00010,.00020]),('slider_size_WTL_m',[.00010,.00008,.00015]),('slider_contact_shift_m',[.00010,.00008,.00030])]:estimate[key]=(np.array(estimate[key])+rng.uniform(-1,1,3)*bound).tolist()
  estimate['source']='Synthetic once estimate with predeclared seed2026100581; engineering sensitivity, not calibrated perception';(out/'noisy-once-estimate.json').write_text(json.dumps(estimate,indent=2));(out/'resistance.json').write_text(json.dumps(dict(kind=kind,reference_N=force,damping_Ns_m=25000,scope='Passive capacity assumption; variable keeps existing startup/spatial factors once'),indent=2));rows.append(dict(name=name,asset_directory=str(out),initial_estimate=str(out/'noisy-once-estimate.json'),physical_parameters=c,reference_N=force,kind=kind,native_options=options,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}))
 Path('research/singlepush-20261005/NECESSARY-FROZEN-CASES-v1.json').write_text(json.dumps(dict(declared_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=2026100581,scope=__doc__,entries=rows,execution_gate='Freeze final actor/controller before physics; common initial-estimate adaptation only; never retune after outcomes'),indent=2))
if __name__=='__main__':main()
