"""Bounded table-corner orientation search for a previously screened new grip.
Passive knife COM stays inside the authored finite table. Search geometry/IK,
not simulation success; actual resting/pickup still require one full rollout.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform,G2Kinematics
from scripts.g2_table_collision import ArmTableCollision

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 j=json.loads(a.plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');k=G2Kinematics();w=np.array(j['wrist_in_knife']);qs=[np.array(j['touch_q']),np.array(j['close_q'])];local=[]
 for q in qs:
  frames=g.w.forward(q);parts=[]
  for name,meshes in g.meshes.items():
   mat=w@frames[name]
   for v,n in meshes:parts.append((name,v@mat[:3,:3].T+mat[:3,3],n@mat[:3,:3].T))
  local.append(parts)
 rows=[];ready=[]
 for corner,y in [('upper',.1485),('lower',-.6485)]:
  for yaw in range(-180,180,15):
   world=transform([.3015,y,.7561],(Rotation.from_euler('z',yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)).as_quat());gaps=[]
   for parts in local:
    for name,v,n in parts:
     v=v@world[:3,:3].T+world[:3,3];axes=np.r_[np.eye(3),n@world[:3,:3].T];pv=(v-np.array([.6,-.25,.725]))@axes.T;r=abs(axes)@np.array([.3,.4,.025]);gaps.append((float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max()),name))
   worst=min(gaps);row=dict(corner=corner,yaw_degrees=yaw,minimum_table_gap_m=worst[0],worst_link=worst[1],geometry_pass=worst[0]>.0003)
   if row['geometry_pass']:
    aq,e=k.solve(world@w,np.array([.3,-.3,0,-1.3,0,0,0]));collisions=ArmTableCollision(.75).collisions(aq);row.update(arm_ik=e,arm_table_collisions=collisions,reachable=e['position_m']<.001 and e['rotation_rad']<.005 and not collisions)
    if row['reachable']:ready.append((worst[0],world,aq,row))
   rows.append(row)
 ready.sort(key=lambda r:r[0],reverse=True)
 if ready:
  gap,world,aq,row=ready[0];(a.output/'localization.json').write_text(json.dumps(dict(object_world_matrix=world.tolist(),object=np.r_[world[:3,3],Rotation.from_matrix(world[:3,:3]).as_quat()].tolist(),grasp_q=aq.tolist(),candidate=row,scope=__doc__),indent=2))
 (a.output/'search.json').write_text(json.dumps(dict(rows=rows,feasible_count=len(ready),best=ready[0][3] if ready else None,scope=__doc__),indent=2));print(json.dumps(dict(geometric_passes=sum(r['geometry_pass'] for r in rows),feasible_count=len(ready),best=ready[0][3] if ready else None)))
if __name__=='__main__':main()
