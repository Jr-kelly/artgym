"""Preregister new disjoint states; historical final matrices are read only for hashes."""
import datetime,hashlib,json
from pathlib import Path
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics
R=Path(__file__).resolve().parents[1]
D=R/'research/unified-student-20261001/data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 D.mkdir(exist_ok=False)
 old=[]; excluded=set()
 for folder in ['artmanip-recovery-20260930','unified-policy-20260930']:
  root=R.parent/folder
  for p in sorted(root.glob('research/*/data/*final*.npy')):
   a=np.load(p)
   if a.ndim!=2 or a.shape[1]!=75:continue
   excluded.update(hashlib.sha256(row.tobytes()).hexdigest() for row in a)
   old.append(dict(path=str(p),sha256=sha(p),rows=len(a),use='row hash exclusion only'))
 assert old
 bases=np.load(R/'research/multigrasp-20260928/data/candidates.npy');hand=WujiKinematics()
 hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
 seen=set(excluded);entries=[]
 for split,n,seed in [('training',256,2026100101),('development',32,2026100102),('confirmation',64,2026100103),('confirmation-expanded',128,2026100104),('final',128,2026100105)]:
  chunks=[]; hashes=[]
  for source in range(4):
   a=states_for_seed(bases[source:source+1],seed*100+source,hand,trials=n);chunks.append(a)
   for row in a:
    h=hashlib.sha256(row.tobytes()).hexdigest();assert h not in seen;seen.add(h);hashes.append(h)
  p=D/(split+'-all.npy');np.save(p,np.concatenate(chunks))
  entries.append(dict(split=split,n_per_source=n,seed_rule=str(seed)+'*100+source',path=str(p.relative_to(R)),sha256=sha(p),row_sha256=hashes,source_order=[0,1,2,3]))
 manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),entries=entries,historical_exclusion=old,historical_unique=len(excluded),scope='Same trained grasp neighbourhood; clusters [0,1], [2], [3]. No new grasp generalization.',confirmation_rule='32 is screening. Within one episode of any gate trigger64. If64 within one episode of a gate, expand once using separate128 confirmation-expanded. Preserve64 failure. Final never used for selection.',ranking=['input legality and all gates','minimum source S strict','minimum stage hold','minimum body stability','earlier checkpoint'],video_rows=[0,32,64,96],teacher_failure_rows=[0,32,64,97],final_closed=True)
 (D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 from scripts.record_wuji_student_goal import record
 record('data_preregistered',manifest=str((D/'manifest.json').relative_to(R)),manifest_sha256=sha(D/'manifest.json'),historical_unique=len(excluded),next='Teacher fixed-state and newdevelopment recovery; final not transferred')
if __name__=='__main__':main()
