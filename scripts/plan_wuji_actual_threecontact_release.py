"""Withdraw the actual three contact materials along their measured normals."""
import argparse,json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--recorded',type=Path,required=True);p.add_argument('--contacts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir();s=np.load(a.recorded/'takeover.npz');r=[json.loads(l) for l in a.contacts.open()][-2];names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_pad_link'];contacts=[max((c for c in r['contacts'] if c['hand_link']==n),key=lambda c:c['normal_magnitude_N']) for n in names];k=G2Kinematics();w=WujiKinematics();q=s['robot_q'][7:].astype(float);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@k.forward(s['robot_q'][:7]);offset=s['issued_target'][7:]-q;rows=[];errs=[];ids=np.r_[np.arange(8),np.arange(16,20)];x=q[ids].copy()
for t in np.linspace(0,3,46):
 u=t/3;u=u*u*(3-2*u);targets=[]
 for c in contacts:
  N=np.array(c['force_normal_contribution_knife_N']);N/=np.linalg.norm(N);targets.append(np.array(c['position_knife_m'])-N*.012*u)
 def residual(xx):
  h=q.copy();h[ids]=xx;F=w.forward(h);result=[]
  for c,goal in zip(contacts,targets):
   T=L@F[c['hand_link']];pt=T[:3,:3]@np.array(c['position_hand_link_m'])+T[:3,3];result.extend((pt-goal)*300)
  result.extend((xx-q[ids])*.02);return result
 fit=least_squares(residual,x,bounds=(w.lower[ids],w.upper[ids]),max_nfev=80);x=fit.x;h=q.copy();h[ids]=x;err=float(np.max(np.abs(residual(x)[:9]))/300);errs.append(err);cmd=np.clip(h+offset*(1-u),w.lower,w.upper);rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()))
rows.insert(0,dict(time_s=0.,arm_q=s['issued_target'][:7].tolist(),hand_q=s['issued_target'][7:].tolist()));rows.append(dict(rows[-1],time_s=5.));result=dict(rows=rows,max_material_error_m=max(errs),contacts=contacts,scope='Actual3contactnormalwithdraw; originalfinitePD; fixedwrist and noobjectstatechanges');(a.output/'support.json').write_text(json.dumps(result,indent=2));record('actual_threecontact_normal_release_planned',[str(a.output/'support.json')],dict(max_material_error_m=max(errs),uncertainty='Actualnormals avoid genericrelease axial ejection?',decision='Goodpointpath->onephysicalrelease; no successfulgeometryclaim'),next_step='Actual5srelease usingnewmaterials');print(max(errs))
