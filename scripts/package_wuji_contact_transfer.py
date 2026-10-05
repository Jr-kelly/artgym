"""Small overlay over already verified singlepush dependencies, plus new evidence."""
import argparse,json
from pathlib import Path
from scripts.package_wuji_traction import packet,R
D=Path('research/contact-transfer-20261006');B=Path('runs/contact-transfer-20261006')
def public(p):return p.is_file() and not any('private' in x.lower() for x in p.parts) and p.suffix.lower() not in ['.html','.jpg','.jpeg','.png','.mp4']
p=argparse.ArgumentParser();p.add_argument('--baseline-manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
old=json.loads(a.baseline_manifest.read_text())['files'];files=[Path(row['path']) for row in old if (R/row['path']).is_file()]
files+=[p.relative_to(R) for p in (R/'scripts').glob('*.py')]
files+=[p.relative_to(R) for p in (R/'isaacgymenvs/deploy/wuji').glob('*.py')]
files+=[p.relative_to(R) for p in (R/D).iterdir() if public(p) and p.suffix in ['.json','.md']]
for folder in ['assets/objects/knife_wuji_contact_transfer_20261006',str(B/'preparation'),str(B/'frozen')]:
 files+=[p.relative_to(R) for p in (R/folder).rglob('*') if public(p) and p.suffix in ['.json','.urdf','.obj'] and 'simulation' not in p.parts and 'physical-v1' not in p.parts]
files+=[B/'env.sh'];rows=[packet(a.output,'contact-transfer-overlay',files)]
evidence=[p.relative_to(R) for p in (R/B).rglob('*') if public(p) and p.suffix in ['.json','.jsonl','.npz','.log','.sh','.txt'] and not any(x in ['release','restored-verification'] for x in p.parts)]
evidence+=[D/'events.jsonl'];rows.append(packet(a.output,'contact-transfer-evidence',evidence));(a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
