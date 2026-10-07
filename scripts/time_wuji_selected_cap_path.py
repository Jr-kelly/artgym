"""Retain a selected geometric Thumb branch with bounded continuous speed.

Recompute the original motor preload/damping after time allocation. Inspect
joint interpolation, including the free-space branch transition, before native.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser()
 for n in ['path','output']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--maximum-rate',type=float,default=.8)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 d=json.loads(a.path.read_text());s=np.load(Path(d['source'])/'takeover.npz')
 trial=Path(json.loads((Path(d['source'])/'manifest.json').read_text())['source']).parent
 physics=json.loads((trial/'physics.json').read_text());kp=np.array(physics['kp'])[-4:];kd=np.array(physics['kd'])[-4:]
 g=DigitGeometry(max_face_axes=10,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'))
 L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
 material=np.array(json.loads(Path(d['material']).read_text())['material_point'])
 q=np.array([v['hand_q'] for v in d['diagnostics']]);oldtime=np.array([v['time_s'] for v in d['diagnostics']]);fractions=np.array([v['fraction'] for v in d['diagnostics']])
 intervals=np.maximum(np.diff(oldtime),abs(np.diff(q,axis=0)).max(axis=1)/a.maximum_rate)
 times=np.r_[0,np.cumsum(intervals)]
 # Every segment is explicitly sampled; the reverse warm-fit can pick
 # different free-space poses with nearly identical Cartesian sites.
 t=np.linspace(0,times[-1],int(np.ceil(times[-1]*30))+1)
 Q=np.array([[np.interp(v,times,q[:,j]) for j in range(20)] for v in t]);U=np.interp(t,times,fractions)
 velocity=np.gradient(Q[:,16:],t,axis=0);checker=HandIntersection();rows=[];checks=[]
 def point(h):
  T=L@g.w.forward(h)['hand_r_thumb_pad_link'];return T[:3,:3]@material+T[:3,3]
 for i,(age,h,u) in enumerate(zip(t,Q,U)):
  P=point(h);J=np.empty((3,4))
  for j in range(4):
   hh=h.copy();hh[16+j]+=1e-5;J[:,j]=(point(hh)-P)/1e-5
  load=(s['issued_target'][23:]-s['robot_q'][23:])*(1-u)
  load+=np.clip(J.T@np.array([0,-1.4,0])/kp,-.12,.12)*smooth((u-.85)/.15)
  cmd=s['issued_target'][7:].astype(float);cmd[16:]=h[16:]+load+np.clip(kd/kp*velocity[i],-.07,.07)
  cmd[16:]=np.clip(cmd[16:],g.w.lower[16:]+.02,g.w.upper[16:]-.02)
  rows.append(dict(time_s=float(age),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
  gaps=g.gaps(h,L,float(s['slider_q']),'thumb')
  checks.append(dict(time_s=float(age),planned_hand_q=h.tolist(),self=checker.inspect(h),
    body_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_0'),
    housing_cap_gap_m=min(v['gap_lower_bound_m'] for v in gaps if v['knife_link']=='link_1' and v['hand_link']!='hand_r_thumb_pad_link'),
    margin_rad=float(np.minimum(h-g.w.lower,g.w.upper-h).min())))
 jump=float(abs(np.r_[rows[0]['arm_q'],rows[0]['hand_q']]-s['issued_target']).max())
 guard=dict(seconds=float(t[-1]),sourcejump_rad=jump,self_frames=sum(bool(v['self']) for v in checks),
   body_gap_min_m=min(v['body_gap_m'] for v in checks),housing_cap_gap_min_m=min(v['housing_cap_gap_m'] for v in checks),
   minimum_planned_margin_rad=min(v['margin_rad'] for v in checks),maximum_planned_rate_rad_s=float((abs(np.diff(Q,axis=0))/np.diff(t)[:,None]).max()),
   scope='30Hz planned joint-interpolation checks; force reference is proxy; actual native contact/pose required')
 guard['permits_native']=bool(jump<1e-6 and not guard['self_frames'] and guard['body_gap_min_m']>.0001 and guard['housing_cap_gap_min_m']>.0001)
 motor=dict(rows=rows,diagnostics=checks,source=d['source'],material=d['material'],development_abort_on_translation_m=.025,guard=guard,scope=__doc__)
 (a.output/'motor.json').write_text(json.dumps(motor,indent=2));print(json.dumps(guard))
 e=record('selected_cap_path_continuity_and_timing_guard',[str(a.output/'motor.json')],config=guard,next_step='Passing selectedbranch -> nativecap; failedinterpolation -> actualfreewaypoint, no limitrelaxation')
 Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(guard)+'\n')
 if not guard['permits_native']:raise SystemExit(2)

if __name__=='__main__':main()
