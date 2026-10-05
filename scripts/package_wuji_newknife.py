"""Derived newknife source/runtime overlay and audit evidence. Private inputs excluded."""
import argparse,json
from pathlib import Path
from scripts.package_wuji_traction import packet,R
D=Path('research/newknife-20261005');B=Path('runs/newknife-20261005')
def public(p):return p.is_file() and not any('private' in x.lower() for x in p.parts) and p.suffix.lower() not in {'.html','.jpg','.jpeg'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);sel=json.loads((R/D/'FROZEN-CANDIDATE.json').read_text())
 files=[x.relative_to(R) for x in (R/'scripts').glob('*.py')]
 files += [x.relative_to(R) for x in (R/D).iterdir() if public(x) and x.suffix in {'.json','.md'}]
 files += [Path('research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json')]
 for folder in ([sel['operation_prepared']] if sel.get('operation_prepared') else [])+['assets/objects/knife_wuji_newknife_20261005/nominal-v5','assets/objects/knife_wuji_newknife_20261005/heldout-v1',sel['prepared'],str(B/'configs'),str(B/'batch/config')]:
  files += [x.relative_to(R) for x in (R/folder).rglob('*') if public(x) and x.suffix in {'.json','.urdf','.obj'}]
 if sel.get('trained_checkpoint'):files.append(Path(sel['trained_checkpoint']))
 rows=[packet(a.output,'newknife-overlay',files)]
 if a.evidence:
  files=[x.relative_to(R) for x in (R/B).rglob('*') if public(x) and not any(k in {'release','videos','env'} for k in x.relative_to(R/B).parts) and x.suffix in {'.json','.jsonl','.npz','.log','.yaml','.sh','.txt','.sha256'}]
  files += [x.relative_to(R) for x in (R/D).iterdir() if public(x) and x.suffix in {'.jsonl','.png'}]
  rows.append(packet(a.output,'newknife-evidence',files))
 (a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
