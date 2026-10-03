"""Small retained developmenttraces, evaluationtruth only as labels."""
import pathlib,json,numpy as np
from scripts.wuji_support_load_proxy import SupportLoadProxy
from scripts.record_wuji_support_goal import record,R,D
B=R/'runs/support-pressure-20261003';rows=[]
record('support_load_proxy_v102_check_started',conclusion='Singleindex-only retention previouslyunloadedother support; firstverify a simpler damped scalarjointtorque projection before coordinatingthreefingers. No proxy is fedtoactor yet.',next='Three retained actualtraces, forceonlylabels; stop if unreliable, no datafitting/search')
for name,label in [('nominal-staged-transfer-v87','nominal'),('raised1-staged-transfer-v87','raised1'),('nominal-index-retention-v44','nominal')]:
 folder=B/'demo'/name;z=np.load(folder/'trace.npz');physics=json.loads((folder/'physics.json').read_text());ids=physics['hand_indices'];motor=json.loads((B/'pressure-config-v35'/label/'motor-plan.json').read_text());normal=np.asarray(motor['wrist_in_knife'])[:3,:3].T@np.array([0.,1.,0.])
 model=SupportLoadProxy(normal,np.asarray(physics['kp'])[ids],np.asarray(physics['kd'])[ids]);observed=z['observed_q'];target=z['target'][:,ids];vel=np.diff(observed,axis=0,prepend=observed[:1])*30;pred=[];torque=[];truth=[]
 # Filter only legal measuredhistory, matching onceissuedtarget at that clock.
 for i in np.flatnonzero((z['time']>=14.25)&(z['time']<=36))[::3]:
  first=max(0,i-4);q=observed[first:i+1].mean(0);qd=vel[first:i+1].mean(0);tar=target[first:i+1].mean(0)
  values=model.estimate(q,tar,qd);pred.append([v['normal_proxy_N'] for v in values]);torque.append([v['unexplained_torque_fraction'] for v in values]);truth.append(z['pair_underside_support_mean_N'][first:i+1][:,[1,2,4]].mean(0))
 pred=np.asarray(pred);truth=np.asarray(truth);torque=np.asarray(torque);stats=[]
 for j,f in enumerate(model.fingers):stats.append(dict(finger=f,MAE_N=float(abs(pred[:,j]-truth[:,j]).mean()),correlation=float(np.corrcoef(pred[:,j],truth[:,j])[0,1]),negative_proxy_fraction=float((pred[:,j]<0).mean()),unexplained_torque_fraction_mean=float(torque[:,j].mean()),actual_mean_N=float(truth[:,j].mean()),proxy_mean_N=float(pred[:,j].mean())))
 rows.append(dict(trace=name,statistics=stats));print(name,json.dumps(stats),flush=True)
p=D/'support-load-proxy-development-v102.json';p.write_text(json.dumps(dict(scope='Developmentevaluationtruth labels only, noactor fittedor onlineforcefeedback; single-normal/PD model engineeringassumptions',cases=rows),indent=2))
record('support_load_proxy_v102_check_closed',evidence=str(p.relative_to(R)),conclusion='Inspect physicalaccuracy/torque residual before deciding controlleruse. This is not measuredcurrent/torque or actualN sensor.',next='Only deploy a coordinatedbounded motorpilot if legalproxy provides a reliableload-retention signal')
