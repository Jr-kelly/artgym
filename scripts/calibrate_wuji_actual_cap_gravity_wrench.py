"""Conservative static gravity wrench from actual Index/Thumb cap-bearing normals.

Tangential allocations are inferred development proxies. Original measured
normal budget and conservative mu=.8 retained; no increased common pressure,
physical change or total-contact-force measurement is claimed.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.load(open(a.source/'manifest.json'));trace=np.load(meta['source']);clock=trace['time'][meta['takeover_index']];C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];R=min(C,key=lambda r:abs(r['time_s']-clock));contacts=R['contacts'];keys=[('hand_r_index_link2','link_0'),('hand_r_index_link4','link_0'),('hand_r_thumb_link4','link_1')];P=[];N=[];FN=[];M=[];magnitude=[]
for hand,knife in keys:
 cs=[c for c in contacts if c['hand_link']==hand and c['knife_link']==knife];assert cs;w=np.array([c['normal_magnitude_N']for c in cs]);total=w.sum();w/=total;F=sum((np.array(c['force_normal_contribution_knife_N'])for c in cs),np.zeros(3));P.append(w@np.array([c['position_knife_m']for c in cs]));M.append(w@np.array([c['position_hand_link_m']for c in cs]));N.append(F/np.linalg.norm(F));FN.append(F);magnitude.append(total)
P=np.array(P);N=np.array(N);FN=np.array(FN);budget=sum(magnitude);com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);O=transform(z['object_state'][:3],z['object_state'][3:7]);wrench=np.r_[O[:3,:3].T@np.array([0,0,.055*9.81]),np.zeros(3)];B=np.empty((6,9));scale=np.array([1,1,1,100,100,100])
for i,point in enumerate(P):
 for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
def cones(x):
 F=x.reshape(3,3);fn=np.sum(F*N,1);ft=F-fn[:,None]*N;return np.r_[.8**2*fn**2-np.sum(ft**2,1),fn-.005,budget-fn.sum()]
record('actual_cap_normal_budget_gravity_calibration_started_v952',[str(a.source)],dict(scope=__doc__,budget_N=budget,normal_contacts=keys,physical_clock_s=float(R['time_s'])),next_step='Inferfeasiblegravitywrench atmeasurednormalbudget first; then contactnormal/material Jacobiantransport andcapturetorqueresidual, no commonpressureincrease')
fit=minimize(lambda x:float(((x-FN.ravel())**2).sum()),FN.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:(B@x-wrench)*scale),dict(type='ineq',fun=cones)],options=dict(maxiter=300,ftol=1e-12));error=float(np.linalg.norm((B@fit.x-wrench)*scale));slack=float(cones(fit.x).min());out=dict(source=str(a.source),scope=__doc__,feasible=error<1e-5 and slack>-1e-7,keys=keys,material_points_link_m=np.array(M).tolist(),points_knife_m=P.tolist(),normals_knife=N.tolist(),measured_normal_vectors_N=FN.tolist(),measured_normal_budget_N=float(budget),allocated_total_force_proxies_N=fit.x.reshape(3,3).tolist(),desired_gravity_wrench=wrench.tolist(),wrench_error=error,cone_slack=slack,solver=fit.message);(a.output/'calibration.json').write_text(json.dumps(out,indent=2));(a.output/'calibrator.py').write_bytes(Path(__file__).read_bytes());record('actual_cap_normal_budget_gravity_calibration_terminal_v952',[str(a.output/'calibration.json')],out,next_step='Feasible ->one globallyloadaware motortransport actualoverlap; infeasibleproxy -> actualcarry retained, diagnose missingcontact/normalfriction model ratherthanpressure/gain grid');print(json.dumps(out))
