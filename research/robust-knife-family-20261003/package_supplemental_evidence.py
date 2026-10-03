"""Archive closed secondary diagnostics only; frozen controller stays unchanged."""
import pathlib,json,tarfile,hashlib
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';base=R/'runs/robust-knife-family-20261003';out=base/'delivery/secondary-context-and-material-evidence.tar.gz'
folders=[base/'estimator'/f'context-prefix{t}-{s}-v1' for t in [8,16] for s in ['train','fresh']]+[D/'holding-geometry-identifiability-v1',D/'closing-hold-identifiability-8s-v1',D/'closing-hold-identifiability-16s-v1',base/'demo/material-sensitivity-P50-low-pair-v67']
files=[f for folder in folders for f in folder.rglob('*') if f.is_file()]
for name in ['analyze_holding_geometry_identifiability.py','analyze_closing_hold_identifiability.py','collect_closing_hold_context.py','package_supplemental_evidence.py','closure-vs-hold-identifiability-preregistration.json','closure-vs-hold-identifiability-summary.json','holding-geometry-identifiability-preregistration.json','effective-pair-friction-sensitivity-preregistration.json','effective-pair-friction-sensitivity-v67.json','engine-material-mixing-diagnostic-v1.json','material-sensitivity-video-review.png','native-contact-documentation-and-interpretation.json']:
 p=D/name;assert p.is_file(),p;files.append(p)
files=sorted(set(files));assert files and not out.exists()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()
record('secondary_context_material_package_started',config={'files':len(files)},evidence=str(out.relative_to(R)),next='Archive actual closed diagnostics separately from332 independent-validation')
entries=[{'path':str(f.relative_to(R)),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
with tarfile.open(out,'w:gz',compresslevel=1) as tar:
 for f in files:tar.add(f,arcname=str(f.relative_to(R)),recursive=False)
m={'archive':out.name,'archive_bytes':out.stat().st_size,'archive_sha256':sha(out),'files':entries,'scope':'Separate geometry-supervision identifiability and material sensitivity diagnostics, not primary independent-validation. Native fullv67 actualsimulation; allcontext512bodyprefixes/labels/models retained; no realrobot actions/humanmedia.'};mp=out.with_suffix(out.suffix+'.manifest.json');mp.write_text(json.dumps(m,indent=2));record('secondary_context_material_package_completed',evidence=str(mp.relative_to(R)),archive_sha256=m['archive_sha256'],next='Upload to draft; verify actual downloaded hash');print({k:v for k,v in m.items() if k!='files'})
