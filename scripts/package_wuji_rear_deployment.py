"""One current overlay over verified base; old weights are never duplicated."""
import argparse,hashlib,json,tarfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 d=ROOT/'research/rear-sim2real-20261009';bundle=d/'bundle-deploy-v8.json';s=json.loads(bundle.read_text());files=set()
 for n,h in s['required_sha256'].items():
  src=a.base/n
  if not src.is_file() or sha(src)!=h:
   if n.endswith('.pth'):raise ValueError('Base must already hold matching unchanged weights: '+n)
   files.add(n)
 # Current deployment code and one guide/audit. Historical pins/source remain in Git/old Releases.
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*wuji_rear*.py'))
 files.add('scripts/g2_local_python.sh')
 files.update('research/rear-sim2real-20261009/'+n for n in ['bundle-deploy-v8.json','FIRST-HARDWARE-SESSION.md','REPRODUCE.md','RUNTIME-CONTRACT.json','MOUNTING.json'])
 files.update(str(p.relative_to(ROOT)) for p in (d/'v3').rglob('*') if p.is_file() and p.suffix in ['.json','.md','.csv','.png','.html'])
 files.update('research/rear-sim2real-20261009/media/'+n for n in ['front-annotated.png','side-annotated.png','thumb-slider-annotated.png','mounting.png'])
 archive=a.output/'rear-v3-deployment.tar.gz'
 with tarfile.open(archive,'w:gz') as t:
  for n in sorted(files):t.add(ROOT/n,arcname=n,recursive=False)
 shutil.copy2(ROOT/'scripts/restore_wuji_rear_deployment.py',a.output/'restore_wuji_rear_deployment.py')
 print(json.dumps(dict(archive=str(archive),sha256=sha(archive),files=len(files),unchanged_weights_included=False,bundle_sha256=sha(bundle))))
if __name__=='__main__':main()
