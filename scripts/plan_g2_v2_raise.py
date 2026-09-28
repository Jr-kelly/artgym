"""Finite lift/retract reach check from actual successful short-lift end.
Reads recorded states for planning only. Never creates or resets physics.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.g2_table_collision import ArmTableCollision
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
 x=np.load(a.source/'trace.npz');k=G2Kinematics();check=ArmTableCollision(.75);seed=x['reference_targets'][-1,:7];w=k.forward(seed);rows=[]
 for shift in [[-.03,0,.17],[-.05,0,.17],[-.03,.03,.17]]:
  row=dict(shift=shift);target=w.copy();target[:3,3]+=shift
  try:
   path,audit=plan_translation(k,seed,target,4,1/30,check);row.update(passed=True,audit=audit);rows.append(row);break
  except ValueError as e:row.update(passed=False,error=str(e));rows.append(row)
 (a.output/'audit.json').write_text(json.dumps(dict(source=str(a.source),scope='Read actual short-lift motor end to plan continuous additional17cm rise. No scene state loaded.',rows=rows),indent=2)+'\n');print(json.dumps([{k:v for k,v in r.items() if k!='audit'} for r in rows]))
if __name__=='__main__':main()
