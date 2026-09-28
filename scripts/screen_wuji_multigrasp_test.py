"""Policy-independent source deduplication, posture and thumb path checks."""
import argparse,datetime,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.filter_wuji_fingertip_grasps import posture_mask,ThumbReach,RULES
R=Path(__file__).resolve().parents[1];D=R/'research/multigrasp-20260928/data'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--states',type=Path,default=D/'fresh-candidates.npy');parser.add_argument('--output',type=Path,default=D/'fresh-geometry.json');parser.add_argument('--seed',type=int,default=2026092803);args=parser.parse_args()
 if args.output.exists():raise FileExistsError('Preserve existing screening result')
 p=args.states;states=np.load(p);old=np.load(D/'candidates.npy');mask=posture_mask(states);reach=ThumbReach();meta=json.loads((R/'assets/objects/knife_wuji_fingertip/000/parameters.json').read_text());records=[]
 for i,row in enumerate(states):
  pp=np.linalg.norm(old[:,40:43]-row[40:43],axis=1);rr=(Rotation.from_quat(old[:,43:47])*Rotation.from_quat(row[43:47]).inv()).magnitude();qq=np.sqrt(np.mean((old[:,:20]-row[:20])**2,axis=1));duplicate=np.flatnonzero((pp<=.005)&(rr<=.05)&(qq<=np.pi/36))
  result=reach.check(row,meta) if mask[i] else dict(passed=False,reason='posture_rejected')
  records.append(dict(row=i,posture=bool(mask[i]),old_near_duplicates=duplicate.tolist(),reach=result));print(i,mask[i],result['passed'],flush=True)
 report=dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=args.seed,states_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),rules=RULES,records=records,scope='all records from newly generated seed reserved exclusively for test despite legacy generator train/test filenames; physical screening only; no policy outcomes',next='combine fixed20s hold and >=3 nonthumb contact fraction>=.95, drift<.01m/rotation<.25rad; deduplicate within new set; freeze all qualifying states, no outcome selection')
 args.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
