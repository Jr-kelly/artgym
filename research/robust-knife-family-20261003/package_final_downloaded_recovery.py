"""Portable actual final download restoration/execution evidence, not new primary evaluation."""
import pathlib,json,tarfile,hashlib
from scripts.record_wuji_robust_goal import record
R=pathlib.Path(__file__).resolve().parents[2];D=R/'research/robust-knife-family-20261003';base=R/'runs/robust-knife-family-20261003';plan=json.loads((D/'final-downloaded-validation-recovery-preregistration.json').read_text());assert (D/'final-downloaded-fixed-validation-comparison.json').is_file();files=[]
for row in plan['runs']:
 folder=R/row['output'];assert (folder/'report.json').is_file();files.extend(p for p in folder.rglob('*') if p.is_file());job=base/'jobs'/('release-recovery-'+row['original']);assert json.loads((job/'result.json').read_text())['exit_code']==0;files.extend(p for p in job.iterdir() if p.is_file())
resume=json.loads((D/'final-downloaded-context-resume-execution.json').read_text())
for row in resume['results']:
 folder=R/row['output'];assert json.loads((folder/'complete.json').read_text())['update']==384
 files.extend(p for p in folder.iterdir() if p.is_file())
 job=base/'jobs'/row['name'];assert json.loads((job/'result.json').read_text())['exit_code']==0;files.extend(p for p in job.iterdir() if p.is_file())
for folder in [base/'demo/final-downloaded-P50-heavy-v68',base/'deploy/final-downloaded-P50-offline-v3',base/'demo/final-downloaded-P50-failure-v69',base/'deploy/final-downloaded-P50-failure-offline-v4']:
 assert (folder/'report.json').is_file();files.extend(p for p in folder.rglob('*') if p.is_file())
files.extend(p for p in D.glob('final-downloaded-*') if p.is_file());files.extend([D/n for n in ['restore_final_downloaded_default.py','run_final_downloaded_native_recovery.py','run_final_downloaded_validation_recovery.py','analyze_final_downloaded_recovery.py','package_final_downloaded_recovery.py','run_final_downloaded_context_resume.py','run_final_downloaded_failure_recovery.py']]);files=sorted(set(files));out=base/'delivery/final-downloaded-recovery-evidence.tar.gz';assert not out.exists()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
record('final_downloaded_recovery_execution_evidence_package_started',config={'files':len(files)},next='Archive all seven closed full traces plus actual local full native demo,600sample offline replay and empty restore receipts')
entries=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
with tarfile.open(out,'w:gz',compresslevel=1) as tar:
 for p in files:tar.add(p,arcname=str(p.relative_to(R)),recursive=False)
m={'archive':out.name,'archive_bytes':out.stat().st_size,'archive_sha256':sha(out),'files':entries,'scope':'Actual GitHubdownloaded default5 emptyrestore and full native/replay/fixed332 execution evidence. Recovery repetitions, not new independent bodies; original204/332 remains primary.'};mp=out.with_suffix(out.suffix+'.manifest.json');mp.write_text(json.dumps(m,indent=2));record('final_downloaded_recovery_execution_evidence_package_completed',evidence=str(mp.relative_to(R)),archive_sha256=m['archive_sha256'],next='Upload and realdownload verify every new archive entry before final Release publication');print({k:v for k,v in m.items() if k!='files'})
