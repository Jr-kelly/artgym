"""Content-addressed source evidence for immutable per-job code snapshots (CPU only)."""
import argparse,hashlib,json,tarfile
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--pins',type=Path,required=True);p.add_argument('--identities',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True);blobs=a.output/'blobs';blobs.mkdir();entries=[]
 for identity in json.loads(a.identities.read_text()):
  pin=a.pins/identity['name'];assert pin.is_dir();total=hashlib.sha256();files=[]
  for folder in ['scripts','isaacgymenvs','rl_games']:
   for path in sorted((pin/folder).rglob('*')):
    if path.is_file() and path.suffix in ['.py','.yaml']:
     relative=str(path.relative_to(pin));data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();total.update(relative.encode());total.update(data);dest=blobs/digest
     if not dest.exists():dest.write_bytes(data)
     files.append(dict(path=relative,sha256=digest,size=len(data)))
  assert total.hexdigest()==identity['pinned_source_sha256'],(identity['name'],total.hexdigest(),identity['pinned_source_sha256'])
  entries.append(dict(job=identity['name'],aggregate_sha256=total.hexdigest(),files=files))
 manifest=dict(pins=entries,blobs=len(list(blobs.iterdir())),recovery='Reconstruct each job by writing blobs/<sha256> to its listed relativepath; configurations/assets/weights are separately retained. Aggregate order is scripts,isaacgymenvs,rl_games sorted paths, then path bytes plus file bytes.');(a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 archive=a.output.with_suffix('.tar.gz');assert not archive.exists()
 with tarfile.open(archive,'w:gz') as t:t.add(a.output,arcname=a.output.name)
 print(json.dumps(dict(jobs=len(entries),blobs=manifest['blobs'],archive=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),size=archive.stat().st_size)))
if __name__=='__main__':main()
