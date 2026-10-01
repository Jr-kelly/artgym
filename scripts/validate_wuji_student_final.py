"""Enforce a reviewable model/code/cohort freeze before final-data GPU work."""
import hashlib,json
from pathlib import Path

def validate(command,code_hash,root):
 root=Path(root);path=root/'research/unified-student-20261001/final-freeze.json'
 assert path.exists(), 'Final jobs require final-freeze.json before opening final data'
 freeze=json.loads(path.read_text())
 assert freeze['frozen_utc'] and freeze['selection'] and freeze['protocols']==['S2','S5','F']
 assert freeze['code_sha256']==code_hash, 'Executable source changed after final freeze'
 assert not any('train_wuji' in token for token in command), 'Final reserve does not authorize new training'
 allowed=[freeze['teacher']]+freeze['models'];by_path={item['path']:item for item in allowed}
 used=[]
 for token in command:
  candidate=token.split('=',1)[-1]
  if candidate.endswith('.pth'):
   assert candidate in by_path, 'Model was not frozen: '+candidate
   item=by_path[candidate];actual=hashlib.sha256((root/candidate).read_bytes()).hexdigest()
   assert actual==item['sha256'], 'Frozen checkpoint hash mismatch'
   used.append(candidate)
 assert used, 'No frozen checkpoint is referenced by final job'
 cohort=freeze['cohort']
 assert hashlib.sha256((root/cohort['path']).read_bytes()).hexdigest()==cohort['sha256']
 for token in command:
  if token.endswith('final-all.npy'):assert token==cohort['path']
 return dict(freeze_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frozen_models_used=used,final_cohort_sha256=cohort['sha256'])
