"""Freeze source-labelled 3/16 pools and development perturbations before training."""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.prepare_wuji_command_states import states_for_seed,WujiKinematics
R=Path(__file__).resolve().parents[1];D=R/'research/multigrasp-20260928/data'
def main():
 a=np.load(D/'candidates.npy');indices=list(range(3))+list(range(3,16))
 np.save(D/'more.npy',a[indices]);np.save(D/'historical-reserved.npy',a[[16,17,20,21,22,23]])
 h=WujiKinematics();h.lower=h.lower.astype(np.float32);h.upper=h.upper.astype(np.float32)
 for label,rows in [('dev',indices),('historical-reserved',[16,17,20,21,22,23])]:
  pieces=[states_for_seed(a[i:i+1],2026092802+i,h,trials=8) for i in rows]
  np.save(D/(label+'-perturb.npy'),np.concatenate(pieces))
 sources=[]
 for i,row in enumerate(a):
  sources.append(dict(candidate_row=i,source=('bridge3_train_'+str(i)) if i<3 else ('functional20_train_'+str(i-3)) if i<23 else 'historical_functional20_test',training=i in indices,duplicate_of={18:2,19:1}.get(i)))
 pairs=[]
 for i in range(len(a)):
  for j in range(i):
   mm=float(np.linalg.norm(a[i,40:43]-a[j,40:43])*1000);rad=float((Rotation.from_quat(a[i,43:47]).inv()*Rotation.from_quat(a[j,43:47])).magnitude());q=float(np.sqrt(np.mean((a[i,:20]-a[j,:20])**2)))
   if mm<=5 and rad<=.05 and q<=np.pi/36:pairs.append(dict(i=i,j=j,mm=mm,degrees=float(np.rad2deg(rad)),joint_rms_rad=q))
 report=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sources=sources,training_more_indices=indices,small_count=3,more_count=16,near_duplicate_pairs=pairs,deduplication='5mm + .05rad + 5deg joint RMS; keep original 3 training records but all near-duplicate family members stay training; 3 records represent 2 clusters',reserved_scope='historically observed sources, withheld from this round; NOT new blind test',blind_test='separate newly seeded physical generation; no model-based selection',protocol=dict(duration_seconds=20,command_seconds=[2,5],strict_slider_m=.002,strict_body_drift_m=.01,strict_body_angle_rad=.25,endpoint_hold_seconds=.3,loose_slider_m=.01,selection='highest equally weighted dev strict success across 2/5s at CP250/500/750/1000; ties latest; test never selects',initialization='same random seed; verified initial model tensor digest',train_interactions_per_epoch=163840,planned_epochs=1000,formal_seed=2026092801),sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*.npy')})
 (D/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
