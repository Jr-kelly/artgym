"""Dense read-only geometry of simultaneous contact pivot and thumb reserve."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_measured_hold_reference import _thumb_geometry,_thumb_frame
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--frame',type=int,required=True);p.add_argument('--env',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'actual-regrasp-traces.npz');q=z['dof'][a.frame,a.env,:27,0].astype(float);o=z['object'][a.frame,a.env];slider=float(z['dof'][a.frame,a.env,27,0]);O=transform(o[:3],o[3:7]);f=FunctionalEntryAffordance();g,chain=_thumb_geometry();X=np.linalg.inv(O)@f.kin.forward(q[:7]);center=np.array(f.assess(q,O,slider,False)['foot_in_knife_m']);arm=q[:7].copy();seed=q[23:].copy();rows=[]
 record('dense_cap_contact_pivot_preflight_started',[str(a.source)],dict(env=a.env,frame=a.frame,angle_deg=20,thumb_reserve_rad=.15,scope=__doc__),next_step='Geometry only; alreadylaunched860 is actualbearing/cap/B test, no inheritedcapacity')
 for u in np.linspace(0,1,31):
  R=Rotation.from_rotvec([0,np.deg2rad(20)*u,0]).as_matrix();Y=X.copy();Y[:3,:3]=R@X[:3,:3];Y[:3,3]=center+R@(X[:3,3]-center)
  def point(v):
   h=q[7:].copy();h[16:]=v;P=Y@_thumb_frame(h,chain);vv=f.vertices@P[:3,:3].T+P[:3,3];w=np.exp(-(vv[:,1]-vv[:,1].min())/.0002);return w@vv/w.sum()
  target3=q[25]+u*max(0.,g.w.lower[18]+.15-q[25])
  def residual(v):return np.r_[(point(v)-center)*1000,(v[2]-target3)*4,(v-seed)*.0001]
  fit=least_squares(residual,np.clip(seed,g.w.lower[16:]+1e-5,g.w.upper[16:]-1e-5),bounds=(g.w.lower[16:]+1e-5,g.w.upper[16:]-1e-5),max_nfev=100,diff_step=1e-5);seed=fit.x;arm,ik=f.kin.solve_near(O@Y,arm,max_step=.08,minimum_margin=.01);qq=q.copy();qq[:7]=arm;qq[23:]=seed;actualX=np.linalg.inv(O)@f.kin.forward(arm);af=f.assess(qq,O,slider,full_path=bool(u==1));gaps=[]
  for digit in ['index','middle','ring','pinky','thumb']:
   gaps.extend(dict(digit=digit,hand_link=x['hand_link'],knife_link=x['knife_link'],gap_m=float(x['gap_lower_bound_m']))for x in f.g.gaps(qq[7:],actualX,slider,digit) if x['gap_lower_bound_m']<-.0002)
  rows.append(dict(progress=float(u),q=qq.tolist(),arm_IK=ik,foot_error_m=float(np.linalg.norm(point(seed)-center)),affordance=af,gaps=gaps))
 result=dict(rows=rows,scope=__doc__+' No physicalstate/motor changes. Signedgaps are meshproxies; nativephysics/B remains acceptance.');(a.output/'result.json').write_text(json.dumps(result,indent=2));(a.output/'preflight.py').write_text(Path(__file__).read_text());record('dense_cap_contact_pivot_preflight_terminal',[str(a.output/'result.json')],dict(last=rows[-1],max_foot_error_m=max(x['foot_error_m']for x in rows),Hbad_frames=sum(bool(x['affordance']['self_intersections'])for x in rows),worst_gap_m=min(x['gap_m']for r in rows for x in r['gaps'])),next_step='860 actualcarrying/contact/B result decides; no staticguide orpressuregrids');print(json.dumps(dict(last=rows[-1],Hbad_frames=sum(bool(x['affordance']['self_intersections'])for x in rows))),flush=True)
if __name__=='__main__':main()
