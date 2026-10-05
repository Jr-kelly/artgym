"""Register each selected grip's thumb motor contact to the selected point on the actual closed cap face.

This is an offline geometry/preload hypothesis, not constant force. Body support
targets and original joint/torque limits remain. Actual contacts decide validity.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--lateral-site',type=float,default=0.,help='Virtual motor point only, not actual contact centroid');p.add_argument('--virtual-inset',type=float,default=.0022);p.add_argument('--axial-site',type=float,default=-.02205,help='Offline chosen closedcap face location, within30mm cap length with2mm edge margin; no live slider measurement');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);assert 0<=a.virtual_inset<=.004
 plan=json.loads(a.plan.read_text());g=DigitGeometry();h=g.w;w=np.asarray(plan['wrist_in_knife']);full=np.asarray(plan['close_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);hull=ConvexHull(v);centers=v[hull.simplices].mean(1);normals=hull.equations[:,:3];assert -.03505<=a.axial_site<=-.00905;assert abs(a.lateral_site)<=.005;target=np.array([a.lateral_site,.0092-a.virtual_inset,a.axial_site])
 def sample(x):
  q=full.copy();q[16:]=x;m=w@h.forward(q)['hand_r_thumb_pad_link'];vv=v@m[:3,:3].T+m[:3,3];pr=vv[:,1];weight=np.exp(-(pr-pr.min())/.0002);point=weight@vv/weight.sum();fc=centers@m[:3,:3].T+m[:3,3];support=fc[:,1]<=pr.min()+.0004;facing=float((normals@m[:3,:3].T@[0,-1,0])[support].max()) if support.any() else -1.;gaps=g.self_gaps(q,'thumb',certify_clearance_m=.0001)+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);return point,facing,min(z['gap_lower_bound_m'] for z in gaps)
 def cons(x):
  point,facing,gap=sample(x);return np.r_[(.0002-abs(point-target))*1000,facing-.25,(gap-.0001)*1000]
 def objective(x):
  point,_,_=sample(x);return float(np.sum(((point-target)*250)**2)+.01*np.sum((x-full[16:])**2))
 fit=minimize(objective,np.clip(full[16:],h.lower[16:]+.005,h.upper[16:]-.005),method='SLSQP',bounds=list(zip(h.lower[16:]+.005,h.upper[16:]-.005)),constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=160,ftol=1e-10));point,facing,gap=sample(fit.x);passed=bool(cons(fit.x).min()>-1e-4)
 audit=dict(scope=__doc__,target_motor_point_knife_m=target.tolist(),result_motor_point_knife_m=point.tolist(),virtual_inset_m=a.virtual_inset,minimum_self_gap_m=gap,facing=facing,geometry_passed=passed,optimizer_success=bool(fit.success),message=fit.message,pressure_measured_N=None,full_stroke_verified=False)
 plan['close_q'][16:]=fit.x.tolist();plan['touch_q'][16:]=fit.x.tolist();plan['thumb_registration_audit']=audit;plan['scope']=__doc__;plan['close_waypoints']=[dict(fraction=0.,q=plan['open_q']),dict(fraction=2/3,q=plan['touch_q']),dict(fraction=1.,q=plan['close_q'])]
 (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(a.output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit));assert passed,'Thumb registration geometry rejected'

if __name__=='__main__':main()
