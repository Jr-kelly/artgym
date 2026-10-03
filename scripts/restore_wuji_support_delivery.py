"""Restore current-round files plus explicitly selected old dependencies."""
import argparse,datetime,hashlib,json,tarfile
from pathlib import Path

OLD_SOURCE='wuji-g2-source-final.tar.gz'
OLD_MODELS='models-and-recovery-final.tar.gz'
OLD_MODEL_PATHS={
 'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth':'2857950cc37f519bf5248fd46377475582993417fa194e89097804e5bc94aff8',
 'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth':'bbf61592721300b1cf053de8246898a69989ed102b7a034da6fb47cc9a541dcd',
}

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def unpack(path,destination,selected=None):
 with tarfile.open(path,'r:gz') as tar:
  members=tar.getmembers()
  assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
  if selected is not None:
   members=[m for m in members if m.name in selected];assert {m.name for m in members}==set(selected)
  tar.extractall(destination,members=members)

def main():
 p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--old-artifacts',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--learning',action='store_true');p.add_argument('--media',action='store_true');a=p.parse_args()
 manifest=json.loads((a.artifacts/'release-manifest.json').read_text());a.destination.mkdir(parents=True,exist_ok=True);assert not any(a.destination.iterdir()),'Use a new empty recovery directory'
 verified=[]
 for dependency in manifest['old_dependencies']:
  path=a.old_artifacts/dependency['name'];assert path.is_file();assert path.stat().st_size==dependency['bytes'];h=digest(path);assert h==dependency['sha256']
  unpack(path,a.destination,OLD_MODEL_PATHS if dependency['name']==OLD_MODELS else None)
  verified.append(dict(name=path.name,sha256=h,bytes=path.stat().st_size,reused_dependency=True))
 for item in manifest['artifacts']:
  if not (item.get('restore_default') or a.learning and item.get('group')=='learning' or a.media and item.get('group')=='movies'):continue
  path=a.artifacts/item['name'];assert path.stat().st_size==item['bytes'];h=digest(path);assert h==item['sha256'];unpack(path,a.destination)
  members=json.loads((a.artifacts/(item['name']+'.manifest.json')).read_text())['files']
  for member in members:
   restored=a.destination/member['path'];assert restored.is_file() and restored.stat().st_size==member['bytes'];assert digest(restored)==member['sha256']
  verified.append(dict(name=path.name,sha256=h,bytes=path.stat().st_size,members_verified=len(members)))
 for name,expected in OLD_MODEL_PATHS.items():assert digest(a.destination/name)==expected
 receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verified=verified,destination=str(a.destination.resolve()),scope='Single selected-byte recovery. Does not install IsaacGym/Python, restore PhysX internals, establish physicalsuccess, or connect hardware.')
 (a.destination/'wuji-support-restore-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))

if __name__=='__main__':main()
