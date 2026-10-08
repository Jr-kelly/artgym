"""Original-mesh four-bearing guide with captured normal-budget gravity proxies.

Uses only the qualified prefix of a bounded planner. Tangential forces remain
inferred; native normals and carrying decide success. Captured residual motor
torques retain loads not identified by the four-contact model. No common gain,
pressure increase, live finger tracker, physical alteration or task-success claim.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.g2_kinematics import transform,minimal_alignment
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import convex_intersection_radius
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v980');p.add_argument('--native-contact-capacity-diagnostic',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.loads(a.geometry.read_text());src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 path=[]
 for r in geo['rows']:
  if r['self']or not r['finite_original_body_patches']or r['Thumb_target_error_m']>.0003 or r['retained_contact_normal_error_m']>.00025:break
  path.append(r)
 assert len(path)>1,'No useful qualified prefix'
 actual=z['robot_q'].astype(float);issued=z['issued_target'].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);L0=invO@f.kin.forward(actual[:7]);names=geo['names'];digits=['index','middle','pinky','thumb'];ids=[np.arange(0,4),np.arange(4,8),np.arange(8,12),np.arange(16,20)];hulls=[ConvexHull(np.concatenate([v for v,norm in g.meshes[n]]))for n in names];M0=np.array([path[0]['contact_material_points'][n]for n in names]);N0=np.array(geo['measured_normals_knife']);FN0=np.array(geo['measured_normal_vectors_N']);budget=float(geo['measured_normal_budget_N']);kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);wrench=np.r_[O[:3,:3].T@np.array([0.,0.,.055*9.81]),np.zeros(3)];scale=np.array([1,1,1,100,100,100]);corrections=[];nativeh=actual[7:];Fh=g.w.forward(nativeh)
 for n,H,m,N in zip(names,hulls,M0,N0):
  T=L0@Fh[n];e=H.equations[:,:3]@m+H.equations[:,3];corrections.append(minimal_alignment(H.equations[e.argmax(),:3],T[:3,:3].T@N))
 def geometry(L,h,M):
  frames=g.w.forward(h);P=[];N=[]
  for n,H,m,R in zip(names,hulls,M,corrections):
   T=L@frames[n];P.append(T[:3,:3]@m+T[:3,3]);e=H.equations[:,:3]@m+H.equations[:,3];N.append(T[:3,:3]@R@H.equations[e.argmax(),:3])
  return np.array(P),np.array(N)
 def allocate(L,h,M,previous):
  P,N=geometry(L,h,M);B=np.empty((6,12))
  for i,point in enumerate(P):
   for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
  def slack(x):
   F=x.reshape(4,3);fn=np.sum(F*N,1);ft=F-fn[:,None]*N;return np.r_[.8**2*fn**2-np.sum(ft**2,1),fn-.01,budget-fn.sum()]
  fit=minimize(lambda x:float(np.sum((x-previous.ravel())**2)),previous.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:(B@x-wrench)*scale),dict(type='ineq',fun=slack)],options=dict(maxiter=200,ftol=1e-12));err=float(np.linalg.norm((B@fit.x-wrench)*scale));s=float(slack(fit.x).min());return fit.x.reshape(4,3),dict(valid=bool(err<1e-5 and s>=-1e-7),scaled_wrench_error=err,cone_slack=s,normal_budget_N=budget,normal_loads_N=np.sum(fit.x.reshape(4,3)*N,1).tolist(),forces_knife_proxies_N=fit.x.reshape(4,3).tolist(),solver=fit.message)
 def jac(L,h,n,m,idx):
  J=np.empty((3,4))
  for j,c in enumerate(idx):
   up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[n];B=L@g.w.forward(down)[n];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
  return J
 record('actual_four_bearing_motor_precheck_started_'+a.version,[str(a.geometry)],dict(scope=__doc__,qualified_prefix_poses=len(path),full_geometry_pass=geo['passed'],measured_normal_budget_N=budget),next_step='Originaldensemesh/H and gravityproxy; one shortactualThumbbodyrelative migration/H/carry then functionalcap continuation')
 initialF,initialfit=allocate(L0,nativeh,M0,FN0);failure=None if initialfit['valid']else 'Original budget initial gravity proxy';residuals=[kp[idx]*(issued[7:][idx]-nativeh[idx])-jac(L0,nativeh,n,m,idx).T@F for n,m,idx,F in zip(names,M0,ids,initialF)];base_radii={};parts=g.knife_geometry.collision_parts(float(z['slider_q']))
 def radii(h,L):
  frames=g.w.forward(h);out={}
  for d in digits:
   for c in g.gaps(h,L,float(z['slider_q']),d,frames=frames,certify_clearance_m=.0002):
    if c['gap_lower_bound_m']>0:continue
    T=L@frames[c['hand_link']];knife=next(p for p in parts if p['link']==c['knife_link']and p['index']==c.get('knife_component',0));key=(c['hand_link'],c['knife_link'],c.get('knife_component',0));out[key]=max(convex_intersection_radius(v@T[:3,:3].T+T[:3,3],knife['vertices'])for v,n in g.meshes[c['hand_link']])
  return out
 base_radii=radii(nativeh,L0);cert=[];fits=[initialfit];rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,.5]];clock=.5;previous=issued.copy();lastF=initialF.copy()
 if failure is None:
  for seg,(A,B)in enumerate(zip(path[:-1],path[1:])):
   qa=np.r_[A['arm_q'],A['hand_q']];qb=np.r_[B['arm_q'],B['hand_q']]
   for u in np.linspace(0,1,max(2,int(math.ceil(abs(qb-qa).max()/.012))+1)):
    q=qa*(1-u)+qb*u;h=q[7:];L=invO@f.kin.forward(q[:7]);H=f.H.inspect(h);r=radii(h,L);bad=[dict(hand_link=k[0],knife_link=k[1],component=k[2],radius_m=v,source_radius_m=base_radii.get(k,0.))for k,v in r.items()if v>max(0.,base_radii.get(k,0.))+.00001];cert.append(dict(segment=seg,fraction=float(u),self=H,original_knife_excess_intersections=bad))
    # This extra captured-radius+10um check is an offline model assumption,
    # not an original PhysX limit. A separately labelled capacity diagnostic
    # may test existing intended body contacts under unchanged physical meshes,
    # PD, effort and force-budget guide. It never passes that geometric audit.
    # Distal skin may roll LINK4 <-> PAD on the original body. These are
    # intended contact surfaces of the four already bearing digits, not new
    # proximal fingers passing through the knife. Actual original collision
    # response, native normals and H remain authoritative for the diagnostic.
    bearing_distal={name for d in digits for name in ['hand_r_'+d+'_link4','hand_r_'+d+'_pad_link']}
    allowed_existing=bool(a.native_contact_capacity_diagnostic and all(b['hand_link']in bearing_distal and b['knife_link']=='link_0'and b['component']==0 for b in bad))
    if H or (bad and not allowed_existing):failure='Original dense hull/H constraint';break
   if failure:break
 if failure is None:
  for i,row in enumerate(path):
   L=np.array(row['wrist_in_knife']);h=np.array(row['hand_q']);M=np.array([row['contact_material_points'][n]for n in names]);F,fit=allocate(L,h,M,lastF);fits.append(fit)
   if not fit['valid']:failure='Original captured normal budget gravity proxy';break
   lastF=F.copy();motor=issued[7:].copy()
   for n,m,idx,F,res in zip(names,M,ids,F,residuals):motor[idx]=h[idx]+(jac(L,h,n,m,idx).T@F+res)/kp[idx]
   arm=np.array(row['arm_q'])+issued[:7]-actual[:7];q=np.r_[arm,motor];margin=float(np.minimum(q-np.r_[f.kin.lower,g.w.lower],np.r_[f.kin.upper,g.w.upper]-q).min())
   if margin<=0:failure='Original motor target limit';break
   clock+=max(1,int(math.ceil(max(abs(q[:7]-previous[:7]).max()/.004,abs(q[7:]-previous[7:]).max()/.012))))/30.;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist()));previous=q
 passed=failure is None;out=dict(passed=passed,failure=failure,source=str(src),full_geometry_pass=geo['passed'],captured_radius_geometric_audit_passed=bool(all(not c['original_knife_excess_intersections']for c in cert)),native_contact_capacity_diagnostic=a.native_contact_capacity_diagnostic,physical_constraints_modified=False,qualified_prefix_poses=len(path),dense_certificates=cert,gravity_proxy_fits=fits,seconds=clock+1.5,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
 if passed:
  rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(rows=rows,required_actual_source=str(src),development_abort_on_translation_m=.015,scope=__doc__),indent=2))
 record('actual_four_bearing_motor_precheck_terminal_'+a.version,[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,dense_samples=len(cert),qualified_prefix_poses=len(path),seconds=clock+1.5),next_step='One native loadedThumb side-to-front short segment ifvalid; no fullA rerun until actualfunctional contact improvement');print(json.dumps({k:v for k,v in out.items()if k not in['dense_certificates','gravity_proxy_fits']}))
if __name__=='__main__':main()
