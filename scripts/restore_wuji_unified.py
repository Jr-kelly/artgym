"""Verify and restore this experiment's release archives without overwriting data."""
import argparse,hashlib,json,tarfile,shutil
from pathlib import Path,PurePosixPath
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);root=a.output.resolve()
 with tarfile.open(a.archive,'r:gz') as tf:
  members=tf.getmembers();manifests=[x for x in members if x.name.startswith('release-manifests/') and x.name.endswith('.json')];assert len(manifests)==1;manifest=json.load(tf.extractfile(manifests[0]));expected={x['path']:x for x in manifest['files']};seen=set()
  for member in members:
   parts=PurePosixPath(member.name);assert not parts.is_absolute() and '..' not in parts.parts and member.isfile()
   target=root/member.name;assert target.resolve().is_relative_to(root) if hasattr(Path,'is_relative_to') else str(target.resolve()).startswith(str(root)+'/')
   if member.name not in expected:assert member==manifests[0]
   else:assert member.size==expected[member.name]['size'];seen.add(member.name)
   target.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():
    if member.name in expected:assert sha(target)==expected[member.name]['sha256'],'Refuse to overwrite different existing file'
    else:assert target.read_bytes()==tf.extractfile(member).read(),'Refuse to overwrite different manifest'
   else:
    with tf.extractfile(member) as src,target.open('xb') as dest:shutil.copyfileobj(src,dest)
   if member.name in expected:assert sha(target)==expected[member.name]['sha256']
  assert seen==set(expected)
 print(json.dumps(dict(archive=str(a.archive),archive_sha256=sha(a.archive),restored_files=len(expected),output=str(root),status='verified')))
if __name__=='__main__':main()
