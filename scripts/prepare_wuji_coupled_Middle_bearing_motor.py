"""Three measured primary contacts carry while a coordinated Middle acquires body.

All force allocations are gravity proxies, never measured tangential forces.
Captured residual actuator torque and original normal budget are preserved for
existing contacts. Only the new contact receives its existing .15N reference.
Original meshes, actuator limits, PD, and B remain unchanged. Native contact and
continuous carrying are required; restored segments do not certify a fresh demo.
"""
import argparse,json,math,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,minimize
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.wuji_exact_knife_intersection import exact_hand_knife_intersection
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);G=json.load(open(a.geometry));C=json.load(open(a.calibration));assert G['passed']and C['feasible']and G['source']==C['source'];src=Path(G['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for name,meshes in g.meshes.items():g.meshes[name]=[(v,np.unique(n,axis=0))for v,n in meshes]
O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);actual=z['robot_q'].astype(float);issued=z['issued_target'].astype(float);L0=invO@f.kin.forward(actual[:7]);h0=actual[7:];kp=np.array(json.load(open('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json'))['direct_pickup']['hand_kp']);keys=C['keys'];M=np.array(C['material_points_link_m']);N=np.array(C['normals_knife']);F0=np.array(C['allocated_total_force_proxies_N']);ids=[np.arange(4),np.arange(4),np.arange(16,20)];com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);wrench=np.array(C['desired_gravity_wrench']);scale=np.array([1,1,1,100,100,100]);budget=C['measured_normal_budget_N'];path=G['rows'].copy();name='hand_r_middle_pad_link';V=np.concatenate([v for v,n in g.meshes[name]]);last=path[-1];h=np.array(last['hand_q']);L=np.array(last['wrist_in_knife']);T=L@g.w.forward(h)[name];P=V@T[:3,:3].T+T[:3,3];m=V[P[:,0].argmax()];goal=np.array([-.0095,-.004,(T[:3,:3]@m+T[:3,3])[2]]);began=time.monotonic();failure=None
record('actual_coupled_primary_Middle_motor_started_v956',[str(a.geometry),str(a.calibration)],dict(scope=__doc__,primary_normal_budget_N=budget,new_bearing_reference_N=.15),next_step='Originalmesh/H +bounded newMiddle closure +gravity torque transport ->ONE actualnewbodybearing beforeThumb rolls')
def residual(x):
 q=h.copy();q[4:8]=x;F=g.w.forward(q);T=L@F[name];r=list((T[:3,:3]@m+T[:3,3]-goal)*3000);r.extend((x-h[4:8])*.02)
 r.extend(min(0.,c['gap_lower_bound_m']-.0005)*4000 for c in g.pair_gaps(q,f.H.pairs,certify_clearance_m=.0005))
 r.extend(min(0.,c['gap_lower_bound_m']+.000025)*4000 for c in g.gaps(q,L,float(z['slider_q']),'middle',frames=F,certify_clearance_m=.0002));return np.array(r)
fit=least_squares(residual,h[4:8],bounds=(g.w.lower[4:8]+.005,g.w.upper[4:8]-.005),max_nfev=50,diff_step=1e-5);closed=h.copy();closed[4:8]=fit.x;T=L@g.w.forward(closed)[name];error=float(np.linalg.norm(T[:3,:3]@m+T[:3,3]-goal));closure=dict(point_error_m=error,hand_q=closed.tolist(),arm_q=last['arm_q'],wrist_in_knife=last['wrist_in_knife'],index=len(path),phase=1.,scope='Original corner closure, new bearing not yet proven');path.append(closure)
if error>.00015:failure='NewMiddle original body corner closure unreachable'
cert=[]
for segment,(A,B)in enumerate(zip(path[:-1],path[1:])):
 if failure:break
 qa=np.r_[A['arm_q'],A['hand_q']];qb=np.r_[B['arm_q'],B['hand_q']];count=max(2,int(np.ceil(abs(qb-qa).max()/.008))+1)
 for u in np.linspace(0,1,count):
  q=qa*(1-u)+qb*u;h=q[7:];L=invO@f.kin.forward(q[:7]);H=f.H.inspect(h);bad=[];checks=[]
  for digit in ['middle','thumb']:
   for c in g.gaps(h,L,float(z['slider_q']),digit,certify_clearance_m=.0002):
    allowed=(digit=='thumb'and c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link']);limit=-.00029 if allowed else -.000025 if digit=='middle'and c['knife_link']=='link_0'else -.00001
    if c['gap_lower_bound_m']<limit:
     e=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),c);checks.append(e)
     if not e['no_intersection']:bad.append(c)
  cert.append(dict(segment=segment,fraction=float(u),self=H,knife_violations=bad,exact_checks=checks))
  if H or bad:failure='Original dense mesh/H invalid';break

def jac(L,h,name,m,index):
 J=np.empty((3,4))
 for j,c in enumerate(index):
  u=h.copy();d=h.copy();u[c]+=1e-5;d[c]-=1e-5;A=L@g.w.forward(u)[name];B=L@g.w.forward(d)[name];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
 return J
res=[kp[:4]*(issued[7:11]-h0[:4])-sum((jac(L0,h0,keys[j][0],M[j],ids[j]).T@F0[j]for j in range(2)),np.zeros(4)),kp[16:]*(issued[23:]-h0[16:])-jac(L0,h0,keys[2][0],M[2],ids[2]).T@F0[2]];Fprev=F0.copy();rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,1.]];clock=1.;previous=issued.copy();force_audit=[]
if not failure:
 for index,r in enumerate(path):
  h=np.array(r['hand_q']);L=np.array(r['wrist_in_knife']);frames=g.w.forward(h);P=np.array([(L@frames[n])[:3,:3]@m+(L@frames[n])[:3,3]for (n,k),m in zip(keys,M)]);B=np.empty((6,9))
  for j,point in enumerate(P):
   for k in range(3):v=np.eye(3)[k];B[:,3*j+k]=np.r_[v,np.cross(point-com,v)]
  def cones(x):
   Q=x.reshape(3,3);fn=np.sum(Q*N,1);return np.r_[.64*fn**2-np.sum((Q-fn[:,None]*N)**2,1),fn-.005,budget-fn.sum()]
  fit=minimize(lambda x:float(np.sum((x-Fprev.ravel())**2)),Fprev.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:(B@x-wrench)*scale),dict(type='ineq',fun=cones)],options=dict(maxiter=300,ftol=1e-12));forces=fit.x.reshape(3,3);error=float(np.linalg.norm((B@fit.x-wrench)*scale));slack=float(cones(fit.x).min());audit=dict(index=index,wrench_error=error,cone_slack=slack,force_proxies_N=forces.tolist());force_audit.append(audit)
  if error>1e-5 or slack<-1e-7:failure='Original primary gravity budget infeasible';break
  motor=issued[7:].copy();motor[:4]=h[:4]+(sum((jac(L,h,keys[j][0],M[j],ids[j]).T@forces[j]for j in range(2)),np.zeros(4))+res[0])/kp[:4];motor[16:]=h[16:]+(jac(L,h,keys[2][0],M[2],ids[2]).T@forces[2]+res[1])/kp[16:];motor[4:8]=h[4:8]+(issued[11:15]-h0[4:8])*(1-min(index/4.,1.))
  if index==len(path)-1:motor[4:8]+=jac(L,h,name,m,np.arange(4,8)).T@(np.array([1,1,0])*.15/np.sqrt(2))/kp[4:8]
  arm=np.array(r['arm_q'])+issued[:7]-actual[:7];q=np.r_[arm,motor];margin=float(np.minimum(q-np.r_[f.kin.lower,g.w.lower],np.r_[f.kin.upper,g.w.upper]-q).min());audit['motor_margin_rad']=margin
  if margin<=0:failure='Original motor joint limit';break
  clock+=max(1,int(np.ceil(max(abs(q[:7]-previous[:7]).max()/.004,abs(q[7:]-previous[7:]).max()/.012))))/30.;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist()));previous=q;Fprev=forces
passed=failure is None;out=dict(passed=passed,failure=failure,source=str(src),seconds=clock+1.5,closure=closure,geometry_certificates=cert,wrench_proxies=force_audit,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
if passed:
 rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
record('actual_coupled_primary_Middle_motor_terminal_v956',[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,seconds=out['seconds'],dense_samples=len(cert),closure_error_m=closure['point_error_m']),next_step='ONE actualnewMiddle normalbearing H/carry; ifpositive freshsameepisode andfullB30 promptly, no pressure/gain/stroke grid');print(json.dumps({k:v for k,v in out.items()if k not in['geometry_certificates','wrench_proxies']}))
