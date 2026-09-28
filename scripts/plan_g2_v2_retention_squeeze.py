"""One evidence-driven extra preload on the balanced three-finger layout.
Only closing MOTOR targets change. No position/force or physics changes.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_side_pickup_candidate import radius
from scripts.g2_kinematics import transform
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--extra',type=float,default=.002);p.add_argument('--raised-clearance',type=float,default=0.);a=p.parse_args();assert 0<a.extra<=.002;assert 0<=a.raised_clearance<=.01;a.output.mkdir(exist_ok=False)
 plan=json.loads(a.plan.read_text());g=DigitGeometry(knife_spec=Path(plan['knife_spec']));w=np.array(plan['wrist_in_knife']);loc=json.loads(a.localization.read_text());obj=transform(loc['object'][:3],loc['object'][3:]);base=np.array(plan['close_q']);idx=[g.w.names.index('hand_r_%s_joint%d'%(f,j)) for f in ['thumb','middle','ring'] for j in range(1,5)];normals=np.array([[-1,0,0],[1,0,0],[1,0,0]])
 def sample(q):
  frames={n:w@t for n,t in g.w.forward(q).items()};vs={n:np.concatenate([v for v,_ in meshes])@frames[n][:3,:3].T+frames[n][:3,3] for n,meshes in g.meshes.items()};points=[]
  for f,norm in zip(['thumb','middle','ring'],normals):
   v=vs['hand_r_%s_pad_link'%f];d=v@norm;weights=np.exp(-(d-d.min())/.0002);points.append(weights@v/weights.sum())
  clearance=min(float((v@obj[2,:3]+obj[2,3]-.75).min()) for v in vs.values());return np.array(points),clearance,vs
 obj[2,3]+=a.raised_clearance
 desired=sample(base)[0]-normals*a.extra
 def residual(x):
  q=base.copy();q[idx]=x;points,height,_=sample(q);return np.r_[(points-desired).ravel()*500,min(height-.00055,0)*1000,(x-base[idx])*.02]
 fit=least_squares(residual,base[idx],bounds=(g.w.lower[idx]+.005,g.w.upper[idx]-.005),max_nfev=120,ftol=1e-10,xtol=1e-10,gtol=1e-10);closed=base.copy();closed[idx]=fit.x
 graph={}
 for parent,child,_,_,_ in g.w.joints:graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
 pairs=[]
 for i,n in enumerate(sorted(g.meshes)):
  near={n}|graph.get(n,set());near|=set().union(*(graph.get(v,set()) for v in list(near)));pairs.extend((n,m) for m in sorted(g.meshes)[i+1:] if m not in near)
 rows=[]
 for u in np.linspace(0,1,21):
  q=(base if a.raised_clearance else np.array(plan['touch_q']))*(1-u)+closed*u;_,height,vs=sample(q);bad=[]
  for n,m in pairs:
   rr=radius(vs[n],vs[m])
   if rr is None or rr>1e-5:bad.append(dict(pair=[n,m],radius_m=rr))
  rows.append(dict(fraction=float(u),table_clearance_m=height,self_intersections=bad))
 errors=np.linalg.norm(sample(closed)[0]-desired,axis=1);passed=bool(max(errors)<.001 and all(r['table_clearance_m']>=.0005 and not r['self_intersections'] for r in rows))
 plan.update(extra_preload_m=a.extra,source_motor_plan=str(a.plan),extra_preload_semantics='Requested soft collision-support point moved inward; motor preload, not measured force/position')
 if a.raised_clearance:
  plan.update(retention_close_q=closed.tolist(),retention_close_start_lift_m=a.raised_clearance,retention_ramp_seconds=.5)
 else:
  plan.update(close_q=closed.tolist(),squeeze_m=float(plan['squeeze_m'])+a.extra);plan['close_waypoints'][-1]['q']=closed.tolist()
 (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2)+'\n');audit=dict(passed=passed,fit_converged=bool(fit.success),contact_errors_m=errors.tolist(),max_motor_change_rad=float(abs(closed-base).max()),rows=rows,scope='Declared motor preload path; original open/touch/G2 preserved. Optional post-lift correction leaves original close byte-identical. Intentional commanded preload overlap is not actual state injection.',raised_clearance_m=a.raised_clearance);(a.output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k!='rows'}))
if __name__=='__main__':main()
