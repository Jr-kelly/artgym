"""Declare two unused joint conditions and freeze baseline+prefix candidate.
No controller retuning is permitted after their physical outcomes.
"""
import datetime,json,hashlib
from pathlib import Path
import numpy as np
from scripts.build_wuji_newknife import build
D=Path('research/contact-transfer-20261006');root=Path('assets/objects/knife_wuji_contact_transfer_20261006/frozen-v1');assert not root.exists();rng=np.random.default_rng(2026100601);records=[]
cases=[dict(name='upper-geometry-friction',length=.1475,width=.01975,thickness=.0088,slider_length=.0336,slider_width=.0078,protrusion=.0024,proximal=.034,mass=.059,reference_N=.93,kind='variable',options=['--hand-friction','.75','--knife-friction','1.7','--observation-noise','.001']),dict(name='mid-high-delay',length=.1455,width=.0193,thickness=.0082,slider_length=.0324,slider_width=.0072,protrusion=.0021,proximal=.0315,mass=.056,reference_N=1.25,kind='constant',options=['--actuation-delay-frames','1','--observation-noise','.001','--observation-bias','.0005'])]
for c in cases:
 c=dict(c);name=c.pop('name');force=c.pop('reference_N');kind=c.pop('kind');options=c.pop('options');folder=root/name;build(folder,**c);estimate=json.loads((folder/'once-estimate.json').read_text())
 for key,bound in [('handle_size_WTL_m',[.00015,.00010,.00020]),('slider_size_WTL_m',[.00010,.00008,.00015]),('slider_contact_shift_m',[.00010,.00008,.00030])]:estimate[key]=(np.array(estimate[key])+rng.uniform(-1,1,3)*bound).tolist()
 estimate['source']='New frozen synthetic engineering estimate, seed2026100601; not real perception';(folder/'noisy-once-estimate.json').write_text(json.dumps(estimate,indent=2));(folder/'resistance.json').write_text(json.dumps(dict(kind=kind,reference_N=force,damping_Ns_m=25000,scope='Passive capacity assumption; variable retains existing startup/spatial factors once'),indent=2));records.append(dict(name=name,asset_directory=str(folder),physical_parameters=c,initial_estimate=str(folder/'noisy-once-estimate.json'),reference_N=force,kind=kind,native_options=options,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}))
files=['scripts/select_wuji_feasible_prefix.py','scripts/prepare_wuji_newknife_case.py','scripts/run_wuji_singlepush.py','scripts/g2_r800_policy.py','scripts/wuji_scheduled_thumb_reference.py','scripts/wuji_joint_deflection_pressure.py','runs/singlepush-20261005/configs/reference-path-drive.json','runs/newknife-20261005/configs/pressure120.json','runs/newknife-20261005/train/center-tail-constant-motor-v1/update_000100.pth']
freeze=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),entries=records,candidate='Retained singlepush actor/control plus estimate-only longest geometrically certified prefix; final-target guard retained as development diagnostic, not promoted because14.56mm fails',actor_unchanged=True,hardware_ready=False,required_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},scope=__doc__,execution_rule='Physical simulation only; audit actual compensated targets afterward and report deployment gap separately. Never promote uncertified hardware targets.')
(D/'FROZEN-JOINT-VALIDATION.json').write_text(json.dumps(freeze,indent=2))
print(json.dumps(freeze))
