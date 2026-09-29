"""Pack immutable completed run/data directories with per-file hashes."""
import argparse,hashlib,json,tarfile,io,datetime
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--paths',nargs='+',required=True);a=p.parse_args();out=R/'delivery/unified-policy-20260930';out.mkdir(parents=True,exist_ok=True);archive=out/(a.name+'.tar.gz');assert not archive.exists();files=[]
 for relative in a.paths:
  path=R/relative;assert path.exists()
  files.extend([path] if path.is_file() else [x for x in path.rglob('*') if x.is_file()])
 files=sorted(set(files));assert not any(x.is_symlink() for x in files);entries=[dict(path=str(x.relative_to(R)),sha256=sha(x),size=x.stat().st_size) for x in files];manifest=dict(name=a.name,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=entries,restore='python -m scripts.restore_wuji_unified ARCHIVE --output RESTORE_ROOT')
 with tarfile.open(archive,'w:gz',compresslevel=1) as tf:
  raw=(json.dumps(manifest,indent=2)+'\n').encode();info=tarfile.TarInfo('release-manifests/'+a.name+'.json');info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
  for x,e in zip(files,entries):
   tf.add(x,arcname=e['path'],recursive=False);assert sha(x)==e['sha256'],'Source changed during packing'
 receipt=dict(name=a.name,archive=str(archive.relative_to(R)),sha256=sha(archive),size=archive.stat().st_size,files=len(entries));(out/(a.name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
