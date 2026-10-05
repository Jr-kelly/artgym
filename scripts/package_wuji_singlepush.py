"""Small overlay over immutable wrap dependencies; current evidence, no private media."""
import argparse,json
from pathlib import Path
from scripts.package_wuji_traction import packet,R
D=Path('research/singlepush-20261005');B=Path('runs/singlepush-20261005')
def public(p):return p.is_file() and not any('private' in v.lower() for v in p.parts) and p.suffix.lower() not in ['.html','.jpg','.jpeg','.png','.mp4']
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline-manifest',type=Path,required=True,help='Already verified small predecessor overlay file list');p.add_argument('--overlay-only',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 old=json.loads(a.baseline_manifest.read_text())['files'];files=[Path(r['path']) for r in old if (R/r['path']).is_file() and not r['path'].startswith('research/newknife-20261005/')]
 files+=[p.relative_to(R) for p in (R/'scripts').glob('*.py')]
 files+=[p.relative_to(R) for p in (R/D).iterdir() if public(p) and p.suffix in ['.json','.md']]
 for folder in ['assets/objects/knife_wuji_singlepush_20261005',str(B/'configs'),str(B/'preparation'),str(B/'frozen'),str(B/'hardware')]:
  files+=[p.relative_to(R) for p in (R/folder).rglob('*') if public(p) and p.suffix in ['.json','.urdf','.obj','.csv'] and 'validation-v1' not in p.parts and 'simulation' not in p.parts]
 rows=[packet(a.output,'singlepush-overlay',files)]
 if a.overlay_only:
  (a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows));return
 evidence=[p.relative_to(R) for p in (R/B).rglob('*') if public(p) and p.suffix in ['.json','.jsonl','.npz','.log','.sh','.csv','.txt'] and not any(v in ['release','restore-gate-v1'] for v in p.parts)]
 evidence += [D/'events.jsonl'];rows.append(packet(a.output,'singlepush-evidence',evidence));(a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
