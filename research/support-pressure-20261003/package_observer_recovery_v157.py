"""Currentround optional observer recovery; no raw-history duplicate archive."""
import pathlib,json,hashlib,tarfile
from scripts.record_wuji_support_goal import record
R=pathlib.Path(__file__).resolve().parents[2];B=R/'runs/support-pressure-20261003';out=B/'delivery/support-observer-recovery.tar.gz';assert not out.exists()
files=[]
for folder in [B/'observer-head-v149',B/'figures/support-observer-v152']:
 files.extend(p for p in folder.rglob('*') if p.is_file())
for v in ['fit','fresh']:
 p=B/'observer-data-packed-v155'/(v+'.npz');files.extend([p,p.with_suffix(p.suffix+'.json')]);folder=B/('observer-data-'+v+'-v148');files.extend(p for p in folder.iterdir() if p.is_file() and p.name!='data.npz')
for folder in (B/'train').glob('*-support-observer-v150-retry1'):
 files.extend(p for p in folder.iterdir() if p.is_file() and p.name in ['update_000800.pth','update_000800.sha256','args.json','config.yaml','scene.json','learning.jsonl'])
files.extend((B/'checkpoints').glob('strong750-support-observer-v150.*'))
files=sorted(set(files));record('observer_recovery_v157_package_started',config={'files':len(files)},evidence=str(out.relative_to(R)),next='Optionalnotadopted observerhead/inputcodec/three50update fullstates. No repeatedoldweights orprivate media.')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
entries=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
with tarfile.open(out,'w:gz',compresslevel=1) as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(R)),recursive=False)
r=dict(group='learning',archive=out.name,bytes=out.stat().st_size,sha256=sha(out),files=entries,scope='Optionalcurrentroundnotadopted observerroute; packedinputlosslesslyunpacks originalorder/data, head andall3 actual50update fullstates. Fitting!=behavior!=independent!=hardware.')
out.with_suffix(out.suffix+'.manifest.json').write_text(json.dumps(r,indent=2));record('observer_recovery_v157_package_closed',evidence=str(out.relative_to(R))+'.manifest.json',config={'bytes':r['bytes'],'files':len(files)},sha256=r['sha256'],next='Uploadoptionalnewrecoverydata, finalreceipts/source/evidence; no further no-gain training.');print(json.dumps({k:v for k,v in r.items() if k!='files'}))
