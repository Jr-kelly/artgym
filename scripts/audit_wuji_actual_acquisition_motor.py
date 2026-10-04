"""Audit the issued open approach and complete close waypoints, no dynamics."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_table_collision import ArmTableCollision
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();j=json.loads(a.plan.read_text());path=json.loads(a.acquisition.read_text());g=DigitGeometry();arm=G2Kinematics();table=ArmTableCollision(.75);rows=[];samples=[]
 aq=np.asarray(path['approach_q'])
 for u in np.linspace(0,1,31):
  f=u*(len(aq)-1);i=min(int(f),len(aq)-2);q=aq[i]*(1-(f-i))+aq[i+1]*(f-i);samples.append(('approach',float(u),q,np.asarray(j['open_q'])))
 for wi,(first,last) in enumerate(zip(j['close_waypoints'][:-1],j['close_waypoints'][1:])):
  for u in np.linspace(0,1,21):samples.append(('close-'+str(wi),float(u),aq[-1],np.asarray(first['q'])*(1-u)+np.asarray(last['q'])*u))
 for phase,u,q,hq in samples:
  w=arm.forward(q);frames=g.w.forward(hq);gaps=[]
  for name,meshes in g.meshes.items():
   mat=w@frames[name]
   for v,n in meshes:
    v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];pv=(v-[.60,-.25,.725])@axes.T;r=abs(axes)@np.array([.30,.40,.025]);gaps.append(float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max()))
  bad=[r for f in FINGERS for r in g.self_gaps(hq,f,certify_clearance_m=.000015) if r['gap_lower_bound_m']<.000015-1e-9];rows.append(dict(phase=phase,fraction=u,minimum_table_gap_m=min(gaps),uncertified_self_pairs=bad,arm_table_collisions=table.collisions(q)))
 result=dict(passed=all(r['minimum_table_gap_m']>.0003 and not r['uncertified_self_pairs'] and not r['arm_table_collisions'] for r in rows),rows=rows,plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),acquisition_sha256=hashlib.sha256(a.acquisition.read_bytes()).hexdigest(),scope='73 actual issued approach/close motor samples, original whole hand hulls and G2 table checks; no object/contact force or dynamics claim. Nominal known table and once-estimated motor targets; no physical asset ID.')
 a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True);assert result['passed']
if __name__=='__main__':main()
