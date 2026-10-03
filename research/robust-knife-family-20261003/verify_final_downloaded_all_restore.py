"""Execute the advertised optional full-evidence restore and audit merged frozen inputs."""
import pathlib,json,hashlib,subprocess,datetime
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';root=pathlib.Path('/tmp/wuji-release-download-verification-20261003');plan=json.loads((D/'final-downloaded-all-restore-preregistration.json').read_text());destination=pathlib.Path(plan['destination']);archives=sorted(root.glob('*.tar.gz'));assert len(archives)==17;items=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
for p in archives:
 m=json.loads(p.with_suffix(p.suffix+'.manifest.json').read_text());expected=m.get('archive_sha256',m.get('sha256'));assert sha(p)==expected;items.append({'name':p.name,'bytes':p.stat().st_size,'sha256':expected,'kind':'tar.gz','restore_default':False})
manifest=R/'runs/robust-knife-family-20261003/delivery/all-archives-restore-verification-manifest.json';manifest.write_text(json.dumps({'artifacts':items,'scope':'Actualdownloaded all17 archive verification inventory; finalflatRelease manifest emitted separately'},indent=2));record('actual_downloaded_all17_optional_restore_started',evidence=str(manifest.relative_to(R)),config={'destination':str(destination),'archives':17},next='Execute actual downloaded standalone --all restore into emptydirectory; audit merged frozen runtime/input/model/head identity')
log=D/'final-downloaded-all-restore.log'
with log.open('w') as f:code=subprocess.call(['python3',str(root/'restore_wuji_robust_delivery.py'),'--artifacts',str(root),'--manifest',str(manifest),'--destination',str(destination),'--all'],stdout=f,stderr=subprocess.STDOUT)
assert code==0,(code,str(log));freeze=json.loads((D/'freeze.json').read_text())
for p,h in freeze['released_runtime_files_sha256'].items():assert sha(destination/p)==h,p
for key in ['frozen_inputs_sha256','base_weights_sha256']:
 for p,h in freeze[key].items():assert sha(destination/p)==h,p
assert sha(destination/freeze['policy']['checkpoint_path'])==freeze['policy']['sha256'];head='research/robust-knife-family-20261003/closing-hold-identifiability-8s-v1/ridge-models.npz';assert sha(destination/head)=='55574f5a321c3b3dda1ffd971263baf2aea808d18b25cd444561862994b28168';helper='research/robust-knife-family-20261003/context_conditioned_residual_experiment.py';assert sha(destination/helper)=='40e8796a93a2fc0833e7d2fe75f7870376e18e8c0b4b865221237b2b701211be';j={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'destination':str(destination),'archives_restored':17,'frozen_runtime_files_verified':1258,'frozen_inputs_baseweights_primary_exact':True,'context_actor_helper_and_head_exact':True,'receipt':json.loads((destination/'wuji-restore-receipt.json').read_text()),'scope':'Advertised optional --all function actually executed on all downloaded final archives in another empty directory. Frozen controller/input/model/head intact after evidence merges; no new physics/score/hardware claim.'};p=D/'final-downloaded-all17-merged-restore-audit.json';p.write_text(json.dumps(j,indent=2));record('actual_downloaded_all17_optional_restore_verified',evidence=str(p.relative_to(R)),config={'archives':17,'frozen_runtime_files':1258,'destination':str(destination)},next='Final combined report/checkpoint coverage, resource/provenance audit and exact GitHub Release publication');print({k:v for k,v in j.items() if k!='receipt'})
