"""Package finite AT/AU prototype recovery, fixeddevelopment checks and exacthead."""
import pathlib,json,hashlib,tarfile
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';base=R/'runs/robust-knife-family-20261003';out=base/'delivery/closing-context-adaptation-evidence.tar.gz';assert not out.exists();files=[]
for name in ['closing-context-AT-v1','closing-context-AU-v1']:
 folder=base/'train'/name;complete=json.loads((folder/'complete.json').read_text());assert complete['update']==350
 files.extend(f for f in folder.iterdir() if f.is_file() and (f.suffix in ['.json','.jsonl','.yaml'] or f.name in ['update_000350.pth','update_000350.sha256']))
files.extend(f for f in (base/'train/closing-context-P50-v1').iterdir() if f.is_file())
for name in ['closing-context-initial-development-v1','closing-context-AT-final-development-v1','closing-context-AU-final-development-v1']:
 folder=base/'checks'/name;assert (folder/'report.json').is_file();files.extend(f for f in folder.iterdir() if f.is_file())
for name in ['closing-context-AT-training-v1','closing-context-AU-training-v1','closing-context-initial-development-v1','closing-context-AT-final-development-v1','closing-context-AU-final-development-v1']:
 folder=base/'jobs'/name;assert json.loads((folder/'result.json').read_text())['exit_code']==0;files.extend(f for f in folder.iterdir() if f.is_file())
files.extend([D/'context_conditioned_residual_experiment.py',D/'CLOSING-CONTEXT-REPRODUCE.md',D/'closing-context-conditioned-pair-preregistration.json',D/'closing-context-input-semantic-replay-audit.json',D/'closing-context-pinned-helper-and-head-identity.json',D/'closing-context-paired-development-summary.json',D/'closing-hold-identifiability-8s-v1/ridge-models.npz',pathlib.Path(__file__).resolve()]);assert all(f.is_file() for f in files)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
files=sorted(set(files));entries=[{'path':str(f.relative_to(R)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files];record('closing_context_pair_recovery_package_started',config={'files':len(files),'originalprimaryunchanged':True},next='Archiveactualfinal350 models/Adam/RNG, allfixedfulltraces anddevelopmententry')
with tarfile.open(out,'w:gz',compresslevel=1) as tar:
 for f in files:tar.add(f,arcname=str(f.relative_to(R)),recursive=False)
m={'archive':out.name,'archive_bytes':out.stat().st_size,'archive_sha256':sha(out),'files':entries,'scope':'Separate155D cachedmeasuredcontext developmentprototype. Pairedfinite training+fixed512 developmentchecks, notoriginalP50/nativehardware/332 primaryindependent results. Restorealongsideprimarysource/models/assets tocontinue thisprototype.'};mp=out.with_suffix(out.suffix+'.manifest.json');mp.write_text(json.dumps(m,indent=2));record('closing_context_pair_recovery_package_completed',evidence=str(mp.relative_to(R)),archive_sha256=m['archive_sha256'],next='Uploadandactualdownload verify; nogeneralization claim fromdevelopment counts');print({k:v for k,v in m.items() if k!='files'})
