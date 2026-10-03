"""Final source delta and recovery receipts; apply after earlier core overlays."""
import pathlib,subprocess,json,tarfile,hashlib
from scripts.record_wuji_support_goal import record
R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003';D=R/'research/support-pressure-20261003';out=B/'delivery/support-final-records.tar.gz'
assert not out.exists()
base='a172d87190b1178f680e60394f19eb1c12a60401'
files=[R/n.decode() for n in subprocess.check_output(['git','diff','--name-only','-z',base,'HEAD'],cwd=R).split(b'\0') if n]
files.extend([D/'STATE.json',D/'HANDOFF.md',D/'events.jsonl',D/'github-commit-map.json',R/'WUJI_GOAL_HANDOFF.md',pathlib.Path(__file__)])
for folder in B.iterdir():
 if folder.is_dir() and ('config' in folder.name or folder.name.startswith('offline-input') or folder.name=='recovery-proof-observer-v158'):
  files.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix in ['.json','.npz','.pth','.sha256','.yaml','.jsonl'])
for name in ['draft-assets-verified-v159.json','standalone-report-contract-v161.json']:
 files.append(B/'delivery'/name)
files=sorted(set(files));assert all(p.is_file() for p in files)
record('final_records_delta_package_started',evidence=str(out.relative_to(R)),config={'source_delta_after':base,'files':len(files)},next='Last overlay updates code/documents and newconfigs; frozen750 retained; journal is packagingtime snapshot')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
entries=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
with tarfile.open(out,'w:gz',compresslevel=1) as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(R)),recursive=False)
r=dict(group='receipts',archive=out.name,bytes=out.stat().st_size,sha256=sha(out),files=entries,scope='ApplyLASTafter default core source/runtime. Finalsource delta, documents/configs and actual805 recoveryproof only; 805 is not adopted, main frozen750 unchanged. Journal snapshot precedes publicpublicationreceipt.')
out.with_suffix(out.suffix+'.manifest.json').write_text(json.dumps(r,indent=2));record('final_records_delta_package_closed',evidence=str(out.relative_to(R))+'.manifest.json',sha256=r['sha256'],config={'bytes':r['bytes'],'files':len(files)},next='Manifest plus verifiedassets andauthorized new publicRelease');print(json.dumps({k:v for k,v in r.items() if k!='files'}))
