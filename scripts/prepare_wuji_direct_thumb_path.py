"""Fixed acquired support, whole-thumb clear approach to slider roof."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);s=np.load(a.source/'takeover.npz');c=json.load(a.candidate.open());g=DigitGeometry(max_face_axes=12,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));q=s['robot_q'][7:].astype(float);L=np.array(c['wrist_in_knife']);end=np.array(c['hand_q']);name='hand_r_thumb_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);T=L@g.w.forward(end)[name];v=V@T[:3,:3].T+T[:3,3];w=np.exp(-(v[:,1]-v[:,1].min())/.0002);m=w@V/w.sum();T=L@g.w.forward(q)[name];P0=T[:3,:3]@m+T[:3,3];Pend=np.array(c['point']);seed=q[16:].copy();rows=[];D=[]
for t in np.linspace(0,6,25):
 u=smooth((t-.5)/3.5);target=P0*(1-u)+Pend*u;target[1]+=.01*np.sin(np.pi*u)
 def res(x):
  h=q.copy();h[16:]=x;T=L@g.w.forward(h)[name];r=list((T[:3,:3]@m+T[:3,3]-target)*250);r.extend((x-((1-u)*q[16:]+u*end[16:]))*.01);r.extend(min(0,v['gap_lower_bound_m']-.0001)*200 for v in g.gaps(h,L,float(s['slider_q']),'thumb'));return np.array(r)
 fit=least_squares(res,np.clip(seed,g.w.lower[16:]+.025,g.w.upper[16:]-.025),bounds=(g.w.lower[16:]+.025,g.w.upper[16:]-.025),max_nfev=80,diff_step=1e-5);seed=fit.x;h=q.copy();h[16:]=seed;cmd=s['issued_target'][7:].copy();cmd[16:]=seed+(s['issued_target'][7:][16:]-q[16:])*(1-u);rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()));D.append(dict(time_s=float(t),error_m=float(np.linalg.norm(res(fit.x)[:3])/250),gap_m=g.minimum_gap(h,L,float(s['slider_q']),'thumb'),self_intersections=HandIntersection().inspect(h)))
out=dict(rows=rows,material_point=m.tolist(),diagnostics=D,source=str(a.source),actual_slider_q_m=float(s['slider_q']),roof_initial_target=Pend.tolist());(a.output/'approach.json').write_text(json.dumps(out,indent=2));print('maxerror',max(r['error_m'] for r in D),'mingap',min(r['gap_m'] for r in D),'bad',sum(bool(r['self_intersections']) for r in D));record('direct_actual_thumb_path_prepared',[str(a.output/'approach.json')],config={'max_error_m':max(r['error_m'] for r in D),'min_gap_m':min(r['gap_m'] for r in D)},next_step='Execute only actual wholeclear approach; then short originalbrake pressstroke')
