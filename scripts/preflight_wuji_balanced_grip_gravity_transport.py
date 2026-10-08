"""Read-only load redistribution for an acquired whole-grip rotation.

Original normal squeeze and all physical limits are unchanged. This fits only
additional tangential finite-PD torques required by the changing gravity vector,
without point following, contact/force feedback or simulator state assignment.
"""
import json,argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--axis-knife',choices=['x','z'],default='z');p.add_argument('--angle-deg',type=float,default=145.);p.add_argument('--rotation-sign',type=int,choices=[-1,1],default=1);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);src=Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-wristcenter-roll-v870/simulation');z=np.load(src/'trace.npz');i=359;q=z['q'][i].astype(float);issued=z['applied_target'][i,7:].astype(float);f=FunctionalEntryAffordance();O=transform(z['object'][i,:3],z['object'][i,3:7]);L=np.linalg.inv(O)@f.kin.forward(z['arm_q'][i]);kp=np.array(json.loads((src.parent/'prefix.json').read_text())['direct_pickup']['hand_kp']);contacts=[json.loads(x)for x in (src/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];boundary=min(contacts,key=lambda r:abs(r['time_s']-z['time'][i]));names=['hand_r_index_link4','hand_r_middle_link4','hand_r_thumb_pad_link'];ids=[np.arange(4),np.arange(4,8),np.arange(16,20)];materials=[];P=[];J=[]
 for name,ji in zip(names,ids):
  cs=[c for c in boundary['contacts']if c['hand_link']==name];assert cs;weights=np.array([c['normal_magnitude_N']for c in cs]);weights/=weights.sum();m=weights@np.array([c['position_hand_link_m']for c in cs]);materials.append(m);T=L@f.g.w.forward(q)[name];P.append(T[:3,:3]@m+T[:3,3]);jac=np.empty((3,4))
  for col,j in enumerate(ji):
   up=q.copy();down=q.copy();up[j]+=1e-5;down[j]-=1e-5;A=L@f.g.w.forward(up)[name];B=L@f.g.w.forward(down)[name];jac[:,col]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
  J.append(jac)
 P=np.array(P);com=np.array([0,.000113841678,-.012053567434]);A=np.zeros((6,6));scale=np.array([1,1,1,100,100,100]);base=O[:3,:3].T@np.array([0,0,.055*9.81]);rows=[]
 for finger in range(3):
  for j in range(2):
   F=np.eye(3)[j+1];A[:,2*finger+j]=np.r_[F,np.cross(P[finger]-com,F)]
 axis=np.array([1,0,0]if a.axis_knife=='x'else[0,0,1])*a.rotation_sign
 for angle in np.linspace(0,a.angle_deg,int(a.angle_deg*2)+1):
  R=O[:3,:3]@Rotation.from_rotvec(axis*np.deg2rad(angle)).as_matrix();delta=R.T@np.array([0,0,.055*9.81])-base;b=np.r_[delta,np.zeros(3)];dforce=np.linalg.lstsq(A*scale[:,None],b*scale,rcond=None)[0].reshape(3,2);h=issued.copy()
  for ji,jac,dF in zip(ids,J,dforce):h[ji]+=jac.T@np.r_[0,dF]/kp[ji]
  residual=A@dforce.reshape(-1)-b;rows.append(dict(angle_deg=float(angle),delta_tangent_knife_N=dforce.tolist(),force_residual_N=residual[:3].tolist(),moment_residual_Nm=residual[3:].tolist(),issued_hand_q=h.tolist(),minimum_motor_limit_margin_rad=float(np.minimum(h-f.g.w.lower,f.g.w.upper-h).min()),motor_delta_abs_max_rad=float(abs(h-issued).max())))
 r=dict(axis_knife=axis.tolist(),angle_deg=a.angle_deg,source_actual_frame=i,source=str(src/'trace.npz'),contact_material_points={n:m.tolist()for n,m in zip(names,materials)},actual_contact_points_knife_m=P.tolist(),rows=rows,max_force_residual_N=max(np.linalg.norm(x['force_residual_N'])for x in rows),max_moment_residual_Nm=max(np.linalg.norm(x['moment_residual_Nm'])for x in rows),minimum_motor_margin_rad=min(x['minimum_motor_limit_margin_rad']for x in rows),max_motor_delta_rad=max(x['motor_delta_abs_max_rad']for x in rows),scope=__doc__);(a.output/'result.json').write_text(json.dumps(r,indent=2));record('wholegrip_gravity_redistribution_preflight_v871',[str(a.output/'result.json')],{k:v for k,v in r.items()if k!='rows'},next_step='Force component unavailable fromtangentonly -> meaningfulwrenchgeometry / wholegripcoupling, not nativebadreference. Feasible originalmotorbounds -> onecurrentfreshactualtest.');print(json.dumps({k:v for k,v in r.items()if k!='rows'}),flush=True)
if __name__=='__main__':main()
