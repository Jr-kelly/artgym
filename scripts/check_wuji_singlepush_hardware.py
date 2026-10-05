"""Task trajectory composite load audit, not measured hardware capability."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_kinematics import WujiKinematics
def main():
 p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();z=np.load(a.trial/'trace.npz');h=WujiKinematics();xml=ET.parse('assets/robots/g2_wuji/g2_wuji.urdf');links={n.get('name'):n for n in xml.findall('link')};limits={j.get('name'):j.find('limit') for j in xml.findall('joint')};ids=np.flatnonzero(z['time']>=16)[::3];dt=.1;centers={};rotations={};frames=[];joints=[];points=[]
 for i in ids:
  q=z['q'][i];wf=np.eye(4);wf[:3,:3]=Rotation.from_quat(z['wrist'][i,3:7]).as_matrix();wf[:3,3]=z['wrist'][i,:3];f={n:wf@m for n,m in h.forward(q).items()};frames.append(f);js=[]
  for parent,child,origin,index,axis in h.joints:
   if index is not None and index>=16:
    m=f[parent]@origin;js.append((m[:3,3],m[:3,:3]@axis))
  joints.append(js);m=f['hand_r_thumb_pad_link'];points.append(m[:3,:3]@h.contact_points['thumb']+m[:3,3])
  for name in links:
   if name.startswith('hand_r_thumb'):
    inert=links[name].find('inertial');com=np.fromstring(inert.find('origin').get('xyz','0 0 0'),sep=' ');centers.setdefault(name,[]).append(f[name][:3,:3]@com+f[name][:3,3]);rotations.setdefault(name,[]).append(f[name][:3,:3])
 tau_gravity=np.zeros((len(ids),4));tau_dynamic=tau_gravity.copy()
 for name,c in centers.items():
  inert=links[name].find('inertial');mass=float(inert.find('mass').get('value'));v=inert.find('inertia');I=np.array([[float(v.get('ixx')),float(v.get('ixy')),float(v.get('ixz'))],[float(v.get('ixy')),float(v.get('iyy')),float(v.get('iyz'))],[float(v.get('ixz')),float(v.get('iyz')),float(v.get('izz'))]]);c=np.array(c);acc=np.gradient(np.gradient(c,dt,axis=0),dt,axis=0);rots=np.array(rotations[name]);omega=np.zeros((len(ids),3));omega[:-1]=Rotation.from_matrix(rots[1:]@rots[:-1].transpose(0,2,1)).as_rotvec()/dt;omega[-1]=omega[-2];alpha=np.gradient(omega,dt,axis=0)
  downstream=4 if name.endswith('pad_link') else int(name[-1])
  for k in range(len(ids)):
   iw=rots[k]@I@rots[k].T;moment=iw@alpha[k]+np.cross(omega[k],iw@omega[k])
   for j,(origin,axis) in enumerate(joints[k][:downstream]):
    J=np.cross(axis,c[k]-origin);tau_gravity[k,j]+=J@np.array([0,0,mass*9.81]);tau_dynamic[k,j]+=J@(mass*acc[k])+axis@moment
 effort=np.array([float(limits[n].get('effort')) for n in h.names[16:]]);rows=[];e=json.loads((a.trial/'extension-evaluation.json').read_text());normal=e['cap_normal_p05_N']
 for normal_name,normal in [('p05',e['cap_normal_p05_N']),('mean',e['cap_normal_mean_N']),('peak',e['cap_normal_peak_N'])]:
  for axial in [.73549875,1.,1.25,1.5]:
   composite=[]
   for k,i in enumerate(ids):
    bodyR=Rotation.from_quat(z['object'][i,3:7]).as_matrix();reaction=bodyR@np.array([0,normal,-axial]);J=np.stack([np.cross(axis,points[k]-origin) for origin,axis in joints[k]],axis=1);composite.append(J.T@reaction+tau_gravity[k]+tau_dynamic[k])
   comp=np.array(composite);rows.append(dict(assumed_axial_load_N=axial,normal_scenario=normal_name,assumed_normal_N=normal,combined_abs_torque_max_Nm=np.abs(comp).max(0).tolist(),fraction_of_urdf_effort_max=(np.abs(comp)/effort).max(0).tolist(),tightest_joint=h.names[16+int(np.argmax((np.abs(comp)/effort).max(0)))],within_model_limits=bool((np.abs(comp)<=effort).all())))
 q=z['q'][ids];target=z['applied_target'][ids][:,json.loads((a.trial/'physics.json').read_text())['hand_indices']];velocity=np.gradient(q,dt,axis=0);vel_limits=np.array([float(limits[n].get('velocity')) for n in h.names]);position_margin=np.minimum(q-h.lower,h.upper-q);samples=[]
 for t in [16,18,20.1]:
  i=int(np.argmin(abs(z['time']-t)));samples.append(dict(time_s=float(z['time'][i]),hand_measured_rad=z['q'][i].tolist(),hand_commanded_rad=z['applied_target'][i,json.loads((a.trial/'physics.json').read_text())['hand_indices']].tolist(),arm_measured_rad=z['arm_q'][i].tolist(),normal_force_N=None,axial_force_N=None,hardware_effort_A=None))
 physics=json.loads((a.trial/'physics.json').read_text());arm_names=[physics['robot_dof_names'][i] for i in physics['arm_indices']];arm_lower=np.array([float(limits[n].get('lower')) for n in arm_names]);arm_upper=np.array([float(limits[n].get('upper')) for n in arm_names]);arm_vel=np.array([float(limits[n].get('velocity')) for n in arm_names]);arm_q=z['arm_q'][ids];arm_velocity=np.gradient(arm_q,dt,axis=0);thumb_margin=np.minimum(q[:,16:]-h.lower[16:],h.upper[16:]-q[:,16:]);
 result=dict(urdf_sha256=hashlib.sha256(Path('assets/robots/g2_wuji/g2_wuji.urdf').read_bytes()).hexdigest(),trace_sha256=hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),thumb_position_margin_min_by_joint_rad=thumb_margin.min(0).tolist(),thumb_velocity_limit_fraction_max_by_joint=(abs(velocity[:,16:])/vel_limits[16:]).max(0).tolist(),arm_names=arm_names,arm_position_min_margin_rad=float(np.minimum(arm_q-arm_lower,arm_upper-arm_q).min()),arm_velocity_limit_fraction_max=float((abs(arm_velocity)/arm_vel).max()),simulation_thumb_kp_Nm_per_rad=np.array(physics['kp'])[physics['hand_indices']][16:].tolist(),model='G2 right7DOF + Wuji v1 right20DOF',asset='assets/robots/g2_wuji/g2_wuji.urdf',thumb_effort_Nm=effort.tolist(),actuator_profile='wuji_paper_official_actuator: pinned official MJCF sensitivity, explicitly NOT hardware calibration',load_rows=rows,gravity_torque_abs_max_Nm=np.abs(tau_gravity).max(0).tolist(),dynamic_torque_abs_max_Nm=np.abs(tau_dynamic).max(0).tolist(),measured_joint_min_margin_rad=float(position_margin.min()),commanded_joint_min_margin_rad=float(np.minimum(target-h.lower,h.upper-target).min()),measured_velocity_limit_fraction_max=float((abs(velocity)/vel_limits).max()),measurement_pose_samples=samples,sdk_position_units='rad',sdk_effort_units='A filtered drive quantity; NOT Nm or contact force',sdk_default_effort_limit_A=1.5,sdk_actual_device_effort_limits=None,sdk_finger_order=['thumb','index','middle','ring','pinky'],runtime_hand_order=h.names,real_robot_ran=False,hardware_verified=False,sources=['https://docs.wuji.tech/docs/zh/wuji-hand/v1/overview/','https://docs.wuji.tech/docs/zh/wujihandpy/latest/api-reference/'],scope='Offline sampled trajectory load model: combined normal + axial + thumb gravity/inertial terms. Actual body pose used evaluation-only. Contact point, sustained normal and inertial discretization assumptions limit precision; no hardware stiffness/current-to-torque calibration or whole-hand capacity claim.')
 a.output.write_text(json.dumps(result,indent=2));print(json.dumps(rows))
if __name__=='__main__':main()
