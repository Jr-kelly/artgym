"""Globally gravity-aware coupled wrist/Index/Thumb reference for loaded cap roll.

Retains actual measured normal budget and original conservative mu=.8. Full
contact forces are inferred static proxies, not measured forces. Contact material
moves on the original Thumb hull; captured residual motor torque is preserved.
Original PD/effort/limits/physics/B unchanged; actual PAD carrying remains required.
"""
import argparse,json,math,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize,linprog
from scipy.spatial import ConvexHull
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform,minimal_alignment
from scripts.wuji_exact_knife_intersection import exact_hand_knife_intersection
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.load(open(a.geometry));cal=json.load(open(a.calibration));assert cal['feasible']and cal['source']==geo['source'];path=geo['rows'];assert not any(r['self']or r['geometry_violations']for r in path);assert max(path[-1]['LINK4_cap_gap_m'],path[-1]['PAD_cap_gap_m'])<.0002;src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
h0=z['robot_q'][7:].astype(float);arm0=z['robot_q'][:7].astype(float);issued=z['issued_target'].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);L0=invO@f.kin.forward(arm0);names=[x[0]for x in cal['keys']];ids=[np.arange(4)for _ in range(2)]+[np.arange(16,20)];M0=np.array(cal['material_points_link_m']);F0=np.array(cal['allocated_total_force_proxies_N']);N0=np.array(cal['normals_knife']);cap=next(c for c in g.knife_geometry.collision_parts(float(z['slider_q']))if c['link']=='link_1'and c['index']==0);capE=ConvexHull(cap['vertices']).equations;kp=np.array(json.load(open('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json'))['direct_pickup']['hand_kp']);scale=np.array([1,1,1,100,100,100]);wrench=np.array(cal['desired_gravity_wrench']);budget=cal['measured_normal_budget_N'];com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);audit=[];certificates=[];failure=None;began=time.monotonic()
def jac(L,h,name,material,index):
 J=np.empty((3,4))
 for j,c in enumerate(index):
  up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[name];B=L@g.w.forward(down)[name];J[:,j]=(A[:3,:3]@material+A[:3,3]-B[:3,:3]@material-B[:3,3])/2e-5
 return J
residual=[kp[:4]*(issued[7:11]-h0[:4])-sum((jac(L0,h0,names[j],M0[j],ids[j]).T@F0[j]for j in range(2)),np.zeros(4)),kp[16:]*(issued[23:]-h0[16:])-jac(L0,h0,names[2],M0[2],ids[2]).T@F0[2]]
record('actual_coupled_cap_gravity_motor_precheck_started_v953',[str(a.geometry),str(a.calibration)],dict(scope=__doc__,original_actual_normal_budget_N=budget,poses=len(path),lastphase=path[-1]['phase']),next_step='One3contact gravitywrench transport andexactdensemesh/H ->ONEshortactualnewPADbearing; no homogeneousforce/gain scan')
# Exact dense interpolation in actual original joint/mesh coordinates.
for seg,(A,B)in enumerate(zip(path[:-1],path[1:])):
 qa=np.r_[A['arm_q'],A['hand_q']];qb=np.r_[B['arm_q'],B['hand_q']];count=max(2,int(np.ceil(abs(qb-qa).max()/.008))+1)
 for u in np.linspace(0,1,count):
  q=qa*(1-u)+qb*u;h=q[7:];L=invO@f.kin.forward(q[:7]);H=f.H.inspect(h);G=g.gaps(h,L,float(z['slider_q']),'thumb',certify_clearance_m=.0002);viol=[];checks=[]
  for c in G:
   allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link'];limit=-.00029 if allowed else -.00001
   if c['gap_lower_bound_m']<limit:
    exact=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),c);checks.append(exact)
    if not exact['no_intersection']:viol.append(c)
  cap4=next(c['gap_lower_bound_m']for c in G if c['hand_link']=='hand_r_thumb_link4'and c['knife_link']=='link_1'and c['knife_component']==0);certificates.append(dict(segment=seg,fraction=float(u),self=H,violations=viol,exact_fallback=checks,LINK4_cap_gap_m=cap4))
  if H or viol or cap4>.0002:failure='Originaldense loadedmesh/H/contact constraint';break
 if failure:break
rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,1.]];clock=1.;previous=issued.copy();Fprev=F0.copy()
def cap_inward(point):
 distance=capE[:,:3]@point+capE[:,3];w=np.exp((distance-distance.max())/.0001);n=-(w@capE[:,:3]);return n/np.linalg.norm(n)
correction=minimal_alignment(cap_inward(np.array(cal['points_knife_m'][2])),N0[2])
if failure is None:
 for row in path:
  if time.monotonic()-began>150:failure='Bounded coupledwrench preparer';break
  h=np.array(row['hand_q']);L=np.array(row['wrist_in_knife']);Fframes=g.w.forward(h);material=M0.copy();P=[];N=N0.copy()
  for j in range(2):T=L@Fframes[names[j]];P.append(T[:3,:3]@material[j]+T[:3,3])
  T=L@Fframes[names[2]];V=np.concatenate([v for v,Nv in g.meshes[names[2]]]);handV=V@T[:3,:3].T+T[:3,3];E=ConvexHull(handV).equations;origin=np.array(cal['points_knife_m'][2])
  if row['index']==0:pa=origin.copy();pb=origin.copy()
  else:
   # Linear closest-pair certificate avoids an under-converged nonlinear projection.
   count=len(E)+len(capE)+12;matrix=np.zeros((count,12));rhs=np.zeros(count);cursor=0
   matrix[:len(E),:3]=E[:,:3];rhs[:len(E)]=-E[:,3];cursor+=len(E)
   matrix[cursor:cursor+len(capE),3:6]=capE[:,:3];rhs[cursor:cursor+len(capE)]=-capE[:,3];cursor+=len(capE)
   for j in range(3):
    matrix[cursor,j]=1;matrix[cursor,3+j]=-1;matrix[cursor,6+j]=-1;cursor+=1
    matrix[cursor,j]=-1;matrix[cursor,3+j]=1;matrix[cursor,6+j]=-1;cursor+=1
    matrix[cursor,3+j]=1;matrix[cursor,9+j]=-1;rhs[cursor]=origin[j];cursor+=1
    matrix[cursor,3+j]=-1;matrix[cursor,9+j]=-1;rhs[cursor]=-origin[j];cursor+=1
   objective=np.r_[np.zeros(6),np.ones(3)*1000,np.ones(3)];projection=linprog(objective,A_ub=matrix,b_ub=rhs,bounds=[(None,None)]*6+[(0,None)]*6,method='highs',options=dict(primal_feasibility_tolerance=1e-9))
   if not projection.success:failure='Original exact skin/cap point linear projection failed';break
   pa=projection.x[:3];pb=projection.x[3:6];pointslack=float(np.min(rhs-matrix@projection.x))
   if pointslack<-1e-8:failure='Original exact projection plane residual';break
   material[2]=T[:3,:3].T@(pa-T[:3,3]);N[2]=correction@cap_inward(pb);N[2]/=np.linalg.norm(N[2])
  P.append(pa);P=np.array(P);B=np.empty((6,9))
  for i,point in enumerate(P):
   for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
  def cones(x):
   forces=x.reshape(3,3);fn=np.sum(forces*N,1);ft=forces-fn[:,None]*N;return np.r_[.8**2*fn**2-np.sum(ft**2,1),fn-.005,budget-fn.sum()]
  fit=minimize(lambda x:float(np.sum((x-Fprev.ravel())**2)),Fprev.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:(B@x-wrench)*scale),dict(type='ineq',fun=cones)],options=dict(maxiter=300,ftol=1e-12));forces=fit.x.reshape(3,3);error=float(np.linalg.norm((B@fit.x-wrench)*scale));slack=float(cones(fit.x).min());entry=dict(index=row['index'],phase=row['phase'],force_proxies_N=forces.tolist(),normal_directions_knife=N.tolist(),contact_points_knife_m=P.tolist(),Thumb_material_link_m=material[2].tolist(),Thumb_original_skin_cap_distance_m=float(np.linalg.norm(pa-pb)),wrench_error=error,cone_slack=slack,solver=fit.message);audit.append(entry)
  if error>1e-5 or slack<-1e-7:failure='Originalnormalbudget gravitywrench infeasible onpath';break
  motor=issued[7:].copy();motor[:4]=h[:4]+(sum((jac(L,h,names[j],material[j],ids[j]).T@forces[j]for j in range(2)),np.zeros(4))+residual[0])/kp[:4];motor[16:]=h[16:]+(jac(L,h,names[2],material[2],ids[2]).T@forces[2]+residual[1])/kp[16:];arm=np.array(row['arm_q'])+issued[:7]-arm0;q=np.r_[arm,motor];margin=float(np.minimum(q-np.r_[f.kin.lower,g.w.lower],np.r_[f.kin.upper,g.w.upper]-q).min());entry['motor_margin_rad']=margin
  if margin<=0:failure='Originalmotorjointlimit';break
  clock+=max(1,int(np.ceil(max(abs(q[:7]-previous[:7]).max()/.004,abs(q[7:]-previous[7:]).max()/.012))))/30.;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist()));previous=q;Fprev=forces
passed=failure is None and len(audit)==len(path);out=dict(passed=passed,failure=failure,source=str(src),original_actual_normal_budget_N=budget,geometry_certificates=certificates,wrench_proxies=audit,seconds=clock+1.5,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2))
if passed:
 rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes());record('actual_coupled_cap_gravity_motor_precheck_terminal_v953',[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,poses=len(audit),dense_samples=len(certificates),seconds=clock+1.5),next_step='Feasiblecoupled wrench ->ONE actualPADbearing >=1s/H/carry thenfunctionalentry/fullB30; infeasibleconservativeproxy ->retainactual927 andnewbodybearing topology, no commonpressureincrease');print(json.dumps({k:v for k,v in out.items()if k not in['geometry_certificates','wrench_proxies']}))
