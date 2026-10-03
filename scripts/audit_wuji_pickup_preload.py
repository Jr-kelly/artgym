"""Certify the changed touch-to-preload command segment, original meshes/table."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--outward-per-height',type=float,default=0.,help='Exact commanded Cartesian extraction slope, positive means world-X outward');a=p.parse_args();assert not a.output.exists()
 j=json.loads(a.plan.read_text());world=np.array(json.loads(a.localization.read_text())['object_world_matrix']);w=world@np.array(j['wrist_in_knife']);g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');rows=[]
 for u in np.linspace(0,1,21):
  if j.get('lift_preload_height_m'):
   first,last=j['lift_preload_height_m'];height=first+(last-first)*u
   q=np.array(j['close_q'])*(1-u)+np.array(j['post_lift_close_q'])*u;current=w.copy();current[2,3]+=height;current[0,3]-=a.outward_per_height*height
  else:q=np.array(j['touch_q'])*(1-u)+np.array(j['close_q'])*u;current=w
  frames=g.w.forward(q);bad=[]
  for f in FINGERS:bad += [r for r in g.self_gaps(q,f,certify_clearance_m=.000015) if r['gap_lower_bound_m']<.000015-1e-9]
  table=[]
  for name,meshes in g.meshes.items():
   mat=current@frames[name]
   for v,n in meshes:
    v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];pv=(v-np.array([.60,-.25,.725]))@axes.T;r=abs(axes)@np.array([.30,.40,.025]);table.append(float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max()))
  rows.append(dict(fraction=float(u),minimum_table_gap_m=min(table),uncertified_self_pairs=bad))
 passed=all(not r['uncertified_self_pairs'] and r['minimum_table_gap_m']>.0003 for r in rows)
 result=dict(passed=passed,rows=rows,args=vars(a),source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),scope='Changed touch-to-preload motor segment only; prior open-to-touch and lateral approach evidence still required. Commanded knife compression allowed, no physical position reset.')
 a.output.write_text(json.dumps(result,default=str,indent=2));print(json.dumps(dict(passed=passed,minimum_table_gap_m=min(r['minimum_table_gap_m'] for r in rows),uncertified_samples=sum(bool(r['uncertified_self_pairs']) for r in rows))));assert passed
if __name__=='__main__':main()
