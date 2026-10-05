"""Package new runnable overlay and evidence; reuse immutable old dependencies."""
import argparse,json
from pathlib import Path
from scripts.package_wuji_traction import packet,R
D=Path('research/highload-20261005');B=Path('runs/highload-20261005')
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 files=[x.relative_to(R) for x in (R/'scripts').glob('*.py')]
 files += [x.relative_to(R) for x in (R/D).iterdir() if x.suffix in {'.md','.json'}]
 for pattern in ['configs/**/*.json','planning/**/*','validation/*inputs*/**/*']:
  files += [x.relative_to(R) for x in (R/B).glob(pattern) if x.is_file()]
 rows=[packet(a.output,'highload-overlay',files)]
 if a.evidence:
  files=[]
  for x in (R/B).rglob('*'):
   if x.is_file() and not any(part in {'release','media'} for part in x.relative_to(R/B).parts) and x.suffix in {'.json','.npz','.yaml','.log','.patch'}:files.append(x.relative_to(R))
  for folder in ['capacity/tracking1-load020-added0.05-video-v3','continuous/tracking1-threecycle-video-v1']:
   files += [x.relative_to(R) for x in (R/B/folder).glob('*.jsonl')]
  files += [x.relative_to(R) for x in (R/B/'resources').glob('**/*.jsonl')]
  files += [x.relative_to(R) for x in (R/D).glob('events*.jsonl')]
  rows.append(packet(a.output,'highload-evidence',files))
 (a.output/'packets.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
