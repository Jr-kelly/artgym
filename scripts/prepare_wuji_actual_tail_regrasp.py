"""Prepare motor-only partial-lift regrasp and full lift from retained v19 prior."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=json.load(open(a.source));z=np.load('runs/flat-table-20261006/development/pose-clamp-v54/simulation/trace.npz');i=np.argmin(abs(z['time']-11.8));O=np.array(s['object_world']);start=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);goal=O@np.array(s['wrist_in_knife']);lift=goal.copy();lift[2,3]+=.16;g=DigitGeometry(knife_spec=a.source.parent/'asset-spec.json');qa=np.array(s['source_q']);qb=np.array(s['hand_q']);rows=[];receipts=[];k=G2Kinematics();arm=np.array(z['arm_q'][i]);slerp=Slerp([0,1],Rotation.from_matrix([start[:3,:3],goal[:3,:3]]))
for t in np.arange(11.8,22+1/60,1/30):
 u=np.clip((t-11.8)/2,0,1);u=u**3*(10-15*u+6*u*u);M=start.copy();M[:3,:3]=slerp(u).as_matrix();M[:3,3]=(1-u)*start[:3,3]+u*goal[:3,3];h=(1-u)*qa+u*qb
 if t>=13.8:
  v=np.clip((t-13.8)/4,0,1);v=v**3*(10-15*v+6*v*v);M[:3,3]=goal[:3,3]*(1-v)+lift[:3,3]*v
 arm,e=k.solve_near(M,arm);rows.append(dict(time_s=float(t),arm_q=arm.tolist(),hand_q=h.tolist(),ik=e))
 if t<13.8 and len(rows)%10==0:
  F=g.w.forward(h);L=np.linalg.inv(O)@M;gap=g.self_gaps(h,'thumb',certify_clearance_m=.0001);height=min((v@(M@F[n])[:3,:3].T+(M@F[n])[:3,3])[:,2].min()-.75 for n,meshes in g.meshes.items() for v,_ in meshes);receipts.append(dict(t=float(t),min_self_gap_m=min(r['gap_lower_bound_m'] for r in gap),min_table_height_m=float(height)))
out=dict(start_s=11.8,rows=rows,scope=__doc__,source=s,path_receipts=receipts,maximum_ik_error_m=max(r['ik']['position_m'] for r in rows));(a.output/'motor.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(max_ik=out['maximum_ik_error_m'],min_self_gap=min(r['min_self_gap_m'] for r in receipts),min_table_height=min(r['min_table_height_m'] for r in receipts))),flush=True);assert out['maximum_ik_error_m']<.005
