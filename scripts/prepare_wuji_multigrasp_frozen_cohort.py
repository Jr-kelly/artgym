"""Prepare one shared final cohort after the novel physical source pool is frozen."""
import argparse,datetime,hashlib,json
from pathlib import Path
import numpy as np
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics
R=Path(__file__).resolve().parents[1];D=R/'research/multigrasp-20260928/data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--novel',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,default=2026092808);a=p.parse_args()
 novel=json.loads((a.novel/'manifest.json').read_text());assert novel['status'] in ['frozen','no_qualified_new_grasps'];assert sha(a.novel/'base.npy')==novel['artifact_sha256']['base.npy']
 freezes={arm:json.loads((R/'runs/multigrasp-20260928'/('development-'+arm)/'frozen.json').read_text()) for arm in 'ABCD'}
 assert all(f['status']=='frozen' for f in freezes.values())
 a.output.mkdir(parents=True,exist_ok=False);old=np.load(D/'candidates.npy');new=np.load(a.novel/'base.npy');hand=WujiKinematics();hand.lower=hand.lower.astype(np.float32);hand.upper=hand.upper.astype(np.float32);pieces=[];rows=[]
 # Original3 +13additional train +6historical diagnostic =22 exact-unique states.
 # Original rows0/1 are one near-family and remain separately labelled, never a blind split.
 ids=list(range(18))+[20,21,22,23]
 for k,i in enumerate(ids):
  source='original_train' if i<3 else 'additional_train' if i<16 else 'historical_diagnostic'
  base=old[i:i+1];piece=states_for_seed(base,a.seed+k,hand,trials=32);pieces.append(piece)
  for j in range(32):rows.append(dict(row=len(rows),cohort=source,source_id='old_candidate_'+str(i),source_row=i,perturbation=j,seed=a.seed+k,independent_new_base=False))
 for k,base in enumerate(new):
  seed=a.seed+1000+k;pieces.append(states_for_seed(base[None],seed,hand,trials=32))
  for j in range(32):rows.append(dict(row=len(rows),cohort='new_unseen',source_id='new_'+str(novel['source_rows'][k]),source_row=novel['source_rows'][k],perturbation=j,seed=seed,independent_new_base=True))
 states=np.concatenate(pieces);np.save(a.output/'states.npy',states)
 manifest=dict(model_freeze_receipts=freezes,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),states_sha256=sha(a.output/'states.npy'),new_base_pool_sha256=sha(a.novel/'base.npy'),new_base_manifest_sha256=sha(a.novel/'manifest.json'),old_source_sha256=sha(D/'candidates.npy'),nominal_records_old=22,old_near_clusters=21,new_base_count=len(new),perturbations_each=32,rows=rows,selection='all preregistered old exact-unique sources plus all physically qualified novel sources; no learned-policy outcome filtering',scope='new perturbations after model selection; historical sources remain labelled historical; zero new sources means no blind grasp conclusion')
 (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items() if k!='rows'}))
if __name__=='__main__':main()
