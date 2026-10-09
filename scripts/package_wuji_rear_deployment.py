"""One current overlay over verified base; old weights are never duplicated."""
import argparse,hashlib,json,tarfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bundle',default='research/rear-sim2real-20261009/bundle-deploy-v8.json');p.add_argument('--revision',choices=['v3','v4','v5'],default='v3');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 d=ROOT/'research/rear-sim2real-20261009';bundle=ROOT/a.bundle;s=json.loads(bundle.read_text());files=set()
 for n,h in s['required_sha256'].items():
  if sha(ROOT/n)!=h:raise ValueError('Current source does not match requested frozen bundle: '+n)
  src=a.base/n
  if not src.is_file() or sha(src)!=h:
   if n.endswith('.pth'):raise ValueError('Base must already hold matching unchanged weights: '+n)
   files.add(n)
 # Current deployment code and one guide/audit. Historical pins/source remain in Git/old Releases.
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*wuji_rear*.py'))
 files.add('scripts/g2_local_python.sh')
 files.add(str(bundle.relative_to(ROOT)))
 files.update('research/rear-sim2real-20261009/'+n for n in ['FIRST-HARDWARE-SESSION.md','REPRODUCE.md','RUNTIME-CONTRACT.json','MOUNTING.json'])
 # The checksum receipt is written after packaging; including a prior receipt
 # would mislabel this archive and create a circular checksum dependency.
 files.update(str(p.relative_to(ROOT)) for p in (d/a.revision).rglob('*') if p.is_file() and p.name!='PACKAGE-CHECK.json' and p.suffix in ['.json','.md','.csv','.png','.html'])
 files.update('research/rear-sim2real-20261009/media/'+n for n in ['front-annotated.png','side-annotated.png','thumb-slider-annotated.png','mounting.png'])
 archive=a.output/('rear-'+a.revision+'-deployment.tar.gz')
 with tarfile.open(archive,'w:gz') as t:
  for n in sorted(files):t.add(ROOT/n,arcname=n,recursive=False)
 shutil.copy2(ROOT/'scripts/restore_wuji_rear_deployment.py',a.output/'restore_wuji_rear_deployment.py')
 print(json.dumps(dict(archive=str(archive),sha256=sha(archive),files=len(files),unchanged_weights_included=False,bundle_sha256=sha(bundle))))
if __name__=='__main__':main()
