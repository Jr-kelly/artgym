"""Bounded G2 branch check reusing already-audited finger plan unchanged."""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.g2_table_collision import ArmTableCollision
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--lift',type=float,default=.03);p.add_argument('--seed',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 d=json.loads(a.plan.read_text());loc=json.loads(a.localization.read_text());obj=transform(loc['object'][:3],loc['object'][3:]);target=obj@np.array(d['wrist_in_knife']);above=target.copy();above[2,3]+=.16;up=target.copy();up[2,3]+=a.lift;k=G2Kinematics();check=ArmTableCollision(.75)
 seeds=[np.array(json.loads((ROOT/'configs/g2_finger_surface/measured-recorded-rest-pickup-v2-arm-seed.json').read_text())),np.array(json.loads((ROOT/'configs/g2_finger_surface/balanced-side-pinch-v1-arm-seed.json').read_text()))]
 if a.seed:seeds=[np.array(json.loads(a.seed.read_text()))]
 rows=[]
 for i,seed in enumerate(seeds):
  row=dict(seed=i);rows.append(row)
  try:
   grasp,err=k.solve(target,seed,attempts=1);high,herr=k.solve(above,grasp,attempts=1);row.update(grasp=err,above=herr)
   if max(err['position_m'],herr['position_m'])>.0005:raise ValueError('Initial IK residual exceeds.5mm')
   path,ad=plan_translation(k,high,target,4,1/30,check);lift,ld=plan_translation(k,path[-1],up,4,1/30,check)
   row.update(passed=True,approach=ad,lift=ld)
   (a.output/'arm-seed.json').write_text(json.dumps(high.tolist(),indent=2)+'\n');(a.output/'motor-plan.json').write_text(a.plan.read_text());break
  except ValueError as e:row.update(passed=False,failure=str(e))
 (a.output/'audit.json').write_text(json.dumps(dict(rows=rows,scope='CPU continuous G2 IK+table check only; finger plan unchanged, short lift only',passed=any(r.get('passed') for r in rows)),indent=2)+'\n');print(json.dumps([dict(seed=r['seed'],passed=r.get('passed'),failure=r.get('failure')) for r in rows]))
if __name__=='__main__':main()
