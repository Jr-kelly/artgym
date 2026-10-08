"""Transfer Index load to existing Middle/Thumb/Pinky before moving Index clear.

The measured current total normal budget is retained in a conservative gravity
wrench proxy. Middle gains load while Thumb loses it; no homogeneous squeeze or
gain scan. All original physical/actuator limits remain. Retire only the Index
captured load residual, hold the live grasp geometry, then independently verify
native three-bearing carrying before an actual free-Index relocation.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);cal=json.loads(a.calibration.read_text());assert cal['feasible']and cal['body_support_without_Index'];src=Path(cal['source']);z=np.load(src/'takeover.npz');meta=json.loads((src/'manifest.json').read_text());trace=np.load(meta['source']);clock=float(trace['time'][meta['takeover_index']]);C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];cc=min(C,key=lambda r:abs(r['time_s']-clock))['contacts'];f=FunctionalEntryAffordance();g=f.g;h=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);names=['hand_r_index_link4']+[x[0]for x in cal['keys']];ids=[np.arange(4),np.arange(4,8),np.arange(16,20),np.arange(8,12)];M=[];P=[];N=[];FN=[]
 for n in names:
  sel=[c for c in cc if c['hand_link']==n and c['knife_link']=='link_0'];assert sel;w=np.array([c['normal_magnitude_N']for c in sel]);w/=w.sum();M.append(w@np.array([c['position_hand_link_m']for c in sel]));P.append(w@np.array([c['position_knife_m']for c in sel]));F=sum((np.array(c['force_normal_contribution_knife_N'])for c in sel),np.zeros(3));FN.append(F);N.append(F/np.linalg.norm(F))
 M=np.array(M);P=np.array(P);N=np.array(N);FN=np.array(FN);budget=float(cal['measured_normal_budget_N']);com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);wrench=np.array(cal['desired_gravity_wrench']);B=np.empty((6,12));scale=np.array([1,1,1,100,100,100])
 for i,point in enumerate(P):
  for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
 def cones(x):
  F=x.reshape(4,3);fn=np.sum(F*N,1);ft=F-fn[:,None]*N;return np.r_[.8**2*fn**2-np.sum(ft**2,1),fn-.005,budget-fn.sum()]
 record('supported_Index_unload_motor_preparation_start_v996',[str(a.calibration)],dict(scope=__doc__,source=str(src),measured_original_total_normal_budget_N=budget,goal='Actual oldM/Thumb plusactualPinky carries beforeIndexclears, actualIndexnormal low'),next_step='Four->three gravitywrench interpolation withoriginalmotorlimits, then one actualthree-bearing hold; no freeIndexmove beforeloadproof')
 fit=minimize(lambda x:float(np.sum((x-FN.ravel())**2)),FN.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:(B@x-wrench)*scale),dict(type='ineq',fun=cones)],options=dict(maxiter=250,ftol=1e-12));F0=fit.x.reshape(4,3);err=float(np.linalg.norm((B@fit.x-wrench)*scale));slack=float(cones(fit.x).min());failure=None if err<1e-5 and slack>=-1e-7 else 'Initial actualfourbearing originalbudget proxy';F1=np.vstack([np.zeros(3),np.array(cal['allocated_total_force_proxies_N'])]);kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);J=[]
 for n,m,idx in zip(names,M,ids):
  jac=np.empty((3,4))
  for j,c in enumerate(idx):
   up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[n];B_=L@g.w.forward(down)[n];jac[:,j]=(A[:3,:3]@m+A[:3,3]-B_[:3,:3]@m-B_[:3,3])/2e-5
  J.append(jac)
 residual=[kp[idx]*(issued[7:][idx]-h[idx])-jac.T@F for idx,jac,F in zip(ids,J,F0)];rows=[];audit=[]
 if failure is None:
  for tick in range(82):
   t=tick/30.;u=np.clip((t-.2)/1.,0,1);alpha=u**3*(10-15*u+6*u*u);forces=F0*(1-alpha)+F1*alpha;motor=issued[7:].copy()
   for j,(idx,jac,F,res)in enumerate(zip(ids,J,forces,residual)):motor[idx]=h[idx]+(jac.T@F+res*(1-alpha if j==0 else 1.))/kp[idx]
   margin=float(np.minimum(motor-g.w.lower,g.w.upper-motor).min());normal=(forces*N).sum(1);audit.append(dict(time_s=t,transfer_fraction=float(alpha),normal_force_proxies_N=normal.tolist(),total_normal_proxy_N=float(normal.sum()),motor_margin_rad=margin))
   if margin<=0:failure='Original motor limit';break
   rows.append(dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=motor.tolist()))
 passed=failure is None;out=dict(passed=passed,failure=failure,source=str(src),source_H=f.H.inspect(h),initial_proxy_forces_N=F0.tolist(),target_proxy_forces_N=F1.tolist(),initial_proxy_error=err,initial_cone_slack=slack,measured_original_total_normal_budget_N=budget,audit=audit,seconds=2.7,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
 if passed:(a.output/'motor.json').write_text(json.dumps(dict(rows=rows,required_actual_source=str(src),development_abort_on_translation_m=.015,scope=__doc__),indent=2))
 record('supported_Index_unload_motor_preparation_terminal_v996',[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,seconds=2.7,initial_proxy_error=err,initial_cone_slack=slack,source_H=out['source_H'],normalbudget_N=budget),next_step='Actualthree-bearing carrying with lowIndexnormal first; no clearance/reacquisition withoutnativeproof');print(json.dumps(dict(passed=passed,failure=failure,seconds=2.7)))
if __name__=='__main__':main()
