"""Freeze disjoint source-local perturbations before any policy evaluation."""
from pathlib import Path
import hashlib,json,datetime
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics
R=Path(__file__).resolve().parents[1]
def main():
 d=R/'research/unified-policy-20260930/data';d.mkdir(parents=True,exist_ok=False)
 source=R/'research/multigrasp-20260928/data/candidates.npy';bases=np.load(source);hand=WujiKinematics()
 hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32)
 entries=[];seen=set()
 for split,n,seed in [('train',128,2026093001),('development',32,2026093002),('promotion',64,2026093003),('final',128,2026093004)]:
  chunks=[]
  for row in range(4):
   actual_seed=seed*100+row
   a=states_for_seed(bases[row:row+1],actual_seed,hand,trials=n)
   for item in a:
    digest=hashlib.sha256(item.tobytes()).hexdigest();assert digest not in seen;seen.add(digest)
   p=d/f'{split}-source{row}.npy';np.save(p,a);chunks.append(a)
   entries.append(dict(split=split,source=row,n=n,seed=actual_seed,path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  p=d/f'{split}-all.npy';np.save(p,np.concatenate(chunks));entries.append(dict(split=split,source='all',n=n*4,path=str(p.relative_to(R)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 (d/'manifest.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),entries=entries,base_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),split_rule='Whole trajectories; train first96 episodes/source/protocol for fitting, last32 held out; final unavailable for selection',scope='Trained base grasp neighbourhoods; 0/1/2 two near-duplicate clusters; source3 additional base',unique_states=len(seen)),indent=2)+'\n')
if __name__=='__main__':main()
