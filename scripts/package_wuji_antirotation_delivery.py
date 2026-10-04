"""Exact-byte current-round Release archives, excluding private attachment media."""
import argparse,json,hashlib,tarfile,subprocess,tempfile,shutil
from pathlib import Path
from scripts.record_wuji_antirotation_goal import R,D,record
B=R/'runs/antirotation-grasp-20261004'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):h.update(block)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--group',choices=['runtime','learning','movies','evidence'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();assert not a.output.exists();files=[]
 if a.group=='runtime':
  files=[R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',R/'runs/support-pressure-20261003/train/joint-noisier-continuation-v31/update_000750.pth']
  files += [B/'initial-geometry-v2/projected-00/motor-plan.json',B/'initial-geometry-v2/projected-00/reference-v1.json',B/'pickup-plans-v1/opposed/localization.json',B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json',B/'continuous-plans-v6/lower-side-calibrated/nominal-calibration.json',D/'functional-criterion-v1.json',D/'RUN-V17.sh']
 elif a.group=='learning':
  for folder in (B/'train').iterdir():
   weights=sorted(folder.glob('update_*.pth'))
   if weights:
    files.extend([weights[-1]])
    if weights[-1].with_suffix('.sha256').exists():files.append(weights[-1].with_suffix('.sha256'))
    frozen=folder/'update_000050.pth'
    if frozen.exists():files.extend([frozen,frozen.with_suffix('.sha256')])
   files.extend(f for f in folder.iterdir() if f.is_file() and f.suffix in ['.json','.jsonl','.yaml'])
  files.extend(f for f in (B/'jobs').rglob('*') if f.is_file() and f.name in ['identity.json','result.json'])
  resumed=B/'newprefix-recovery-v1/resumed'
  if resumed.exists():files.extend(f for f in resumed.iterdir() if f.is_file() and f.suffix in ['.pth','.sha256','.json','.jsonl','.yaml'])
  if (B/'newprefix-recovery-v1/resume-receipt.json').exists():files.append(B/'newprefix-recovery-v1/resume-receipt.json')
 elif a.group=='movies':
  for name in ['actual-table-projected-grasp-frozen750-load2-v17','actual-table-projected-grasp-frozen750-load5-v18','actual-table-projected-size08-frozen750-load2-v19','actual-table-projected-retain750-frozen50-load5-v21','actual-table-continuous-prepared-frozen750-load5-v23','actual-table-thin-allcontact-frozen750-load2-v24','actual-table-thin-threegeo-frozen50-load2-v25','actual-table-thin-index-retention-frozen750-load2-v26','actual-table-thin-moment-retention-frozen750-load2-v27','actual-table-nominal-table-prior-range04-frozen50-load2-v32','actual-table-thin-table-prior-range04-frozen50-load2-v33','actual-table-nominal-table-prior-range12-frozen50-load2-v34','actual-table-thin-table-prior-range12-frozen50-load2-v35']:
   folder=B/'continuous'/name
   if not folder.exists():continue
   files.extend(f for f in folder.iterdir() if f.is_file() and (f.suffix in ['.mp4','.png'] or f.name in ['report.json','functional-evaluation.json','physics.json','plan.json']))
  for name in ['actual-table-postlift-ring-brace-frozen750-load5-v36','actual-table-ring-tracking-acquisition-frozen750-load5-v37']:
   folder=B/'continuous'/name
   if folder.exists():files.extend(f for f in folder.iterdir() if f.is_file() and (f.suffix in ['.mp4','.png'] or f.name in ['report.json','functional-evaluation.json','physics.json','plan.json']))
  for collection in ['height-development-four-v1','fresh-joint-validation4-v1','necessary24-frozen25-development-v1']:
   for folder in (B/collection).iterdir() if (B/collection).exists() else []:
    if not folder.is_dir():continue
    files.extend(f for f in folder.iterdir() if f.is_file() and (f.suffix in ['.mp4','.png'] or f.name in ['report.json','functional-evaluation.json','physics.json','plan.json']))
  if (B/'presentation').exists():files.extend(f for f in (B/'presentation').iterdir() if f.is_file() and 'preview' not in f.name and f.suffix in ['.mp4','.png','.json','.html'])
  for figure in ['actual-development-v3','contact-signatures-v1','loaded-return-evidence-v1']:
   if (B/'figures'/figure).exists():files.extend(f for f in (B/'figures'/figure).rglob('*') if f.is_file())
 else:
  files.extend(f for f in B.rglob('*') if f.is_file() and f.suffix in ['.npz','.json','.jsonl','.log','.yaml','.patch','.csv','.txt'] and 'delivery' not in f.relative_to(B).parts)
  files.extend(f for f in D.rglob('*') if f.is_file() and f.suffix in ['.md','.json','.jsonl','.py','.sh'] and f.name!='github-commit-map.json' and '__pycache__' not in f.parts)
 files=sorted(set(files));assert files and all(f.is_file() and R in f.parents for f in files)
 a.output.parent.mkdir(parents=True,exist_ok=True);record('antirotation_delivery_archive_started',config={'group':a.group,'files':len(files)},evidence=str(a.output.relative_to(R)),next='Exact selected bytes and SHA256 manifest; representative restore before final publication')
 with tempfile.TemporaryDirectory(prefix='wuji-archive-snapshot-',dir=str(a.output.parent)) as temporary:
  snapshots=[]
  for f in files:
   target=Path(temporary)/f.relative_to(R);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target);snapshots.append((f,target))
  entries=[dict(path=str(f.relative_to(R)),bytes=snapshot.stat().st_size,sha256=digest(snapshot)) for f,snapshot in snapshots]
  with tarfile.open(a.output,'w:gz',compresslevel=1,dereference=True) as tar:
   for f,snapshot in snapshots:tar.add(snapshot,arcname=str(f.relative_to(R)),recursive=False)
 receipt=dict(group=a.group,archive=a.output.name,bytes=a.output.stat().st_size,sha256=digest(a.output),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),files=entries,scope='Exact archived bytes; code obtained from matching GitHub tag/commit, scientific role separately reported. Private attachment photo/video not included. Learning resume restores model/Adam/RNG with new physical episodes, not bitwise solver state.')
 manifest=a.output.with_suffix(a.output.suffix+'.manifest.json');manifest.write_text(json.dumps(receipt,indent=2));record('antirotation_delivery_archive_completed',config={k:v for k,v in receipt.items() if k!='files'},evidence=str(manifest.relative_to(R)),next='Verify representative extraction/dependency hashes; no success inferred from archive creation');print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
if __name__=='__main__':main()
