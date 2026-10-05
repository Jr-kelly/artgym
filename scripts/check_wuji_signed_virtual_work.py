"""Independent finite-difference virtual work with explicit force convention."""
import argparse,json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();z=np.load(a.trial/'trace.npz');h=WujiKinematics();physics=json.loads((a.trial/'physics.json').read_text());rows=[];eps=1e-6
# Hinge +Z, contact +X, external downward -Y: tau_external=-L*F,
# so static motor must be +L*F. Check displacement virtual work independently.
L=.1;F=np.array([0,-1.25,0]);p0=np.array([L,0,0]);dp=(Rotation.from_rotvec([0,0,eps]).apply(p0)-Rotation.from_rotvec([0,0,-eps]).apply(p0))/(2*eps);ext=F@dp;motor=-ext;assert ext<0 and abs(motor-.125)<1e-10
for t in [16,18,20.1]:
 i=int(np.argmin(abs(z['time']-t)));q=z['q'][i].astype(float);W=np.eye(4);W[:3,:3]=Rotation.from_quat(z['wrist'][i,3:7]).as_matrix();W[:3,3]=z['wrist'][i,:3];frames={k:W@v for k,v in h.forward(q).items()};origins=[];axes=[]
 for parent,child,origin,index,axis in h.joints:
  if index is not None and index>=16:
   T=frames[parent]@origin;origins.append(T[:3,3]);axes.append(T[:3,:3]@axis)
 def point(q):
  T=W@h.forward(q)['hand_r_thumb_pad_link'];return T[:3,:3]@h.contact_points['thumb']+T[:3,3]
 pt=point(q);Ja=np.stack([np.cross(axis,pt-o) for axis,o in zip(axes,origins)],axis=1);Jfd=[]
 for j in range(16,20):
  up=q.copy();dn=q.copy();up[j]+=eps;dn[j]-=eps;Jfd.append((point(up)-point(dn))/(2*eps))
 Jfd=np.stack(Jfd,axis=1);assert np.max(abs(Jfd-Ja))<1e-8
 R=Rotation.from_quat(z['object'][i,3:7]).as_matrix();force_local=np.array([0,1.016675989192831,-1.25]);Fw=R@force_local;d=np.array([.13,-.2,.07,.11]);workw=Fw@(Jfd@d);worklocal=force_local@(R.T@Jfd@d);assert abs(workw-worklocal)<1e-12
 actual=z['torque'][i,np.array(physics['hand_indices'])[16:]];extfd=Jfd.T@Fw;comp=-extfd
 rows.append(dict(time_s=float(z['time'][i]),world_external_on_hand_N=Fw.tolist(),knife_external_on_hand_N=force_local.tolist(),analytic_minus_finite_difference_max_m_per_rad=float(abs(Ja-Jfd).max()),virtual_work_world_J_per_rad=float(workw),virtual_work_knife_J_per_rad=float(worklocal),signed_external_generalized_Nm=extfd.tolist(),required_motor_contact_compensation_Nm=comp.tolist(),raw_sim_motor_Nm=actual.tolist(),same_sign_contact_compensation_vs_raw=(np.sign(comp)==np.sign(actual)).tolist(),scope='Raw actual motor includes gravity, PD tracking, multiple contacts and transients. Force vector and marker assumed; total axial force missing. No numerical equality imposed.'))
a.output.write_text(json.dumps(dict(single_hinge_static=dict(external_generalized_Nm=float(ext),motor_required_Nm=float(motor),old_plus_formula_Nm=float(ext),passed=True),trajectory_checks=rows,equation='tau_motor=M*qdd+C+g-J.T*F_external',independent_virtual_work_pass=True,real_hardware_calibrated=False),indent=2))
print(json.dumps(rows))
