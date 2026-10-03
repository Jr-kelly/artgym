"""Finite normal-PD target hypothesis subject to actual table/self geometry.
Project thumb/middle/pinky targets, retaining a small genuine underside patch.
Estimated linear loads in this offline objective are not constant/measured
contact forces. Free-knife physics must validate pickup before training.
"""
import argparse,json,hashlib,time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--touch-plan',type=Path,required=True);p.add_argument('--nominal-plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();j=json.loads(a.touch_plan.read_text());nominal=json.loads(a.nominal_plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;w=np.array(j['wrist_in_knife']);world=np.array(json.loads(a.localization.read_text())['object_world_matrix']);q0=np.array(j['touch_q']);target=np.array(nominal['close_q']);ids=np.array([4,5,6,7,8,9,10,11,16,17,18,19]);kp=np.array(OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').dof_props.stiffness);normal=np.array(j['contact_normals']);vertices={f:np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]) for f in FINGERS}
 def points(q):
  frames=h.forward(q);out=[]
  for f,n in zip(FINGERS,normal):
   mat=w@frames['hand_r_'+f+'_pad_link'];v=vertices[f]@mat[:3,:3].T+mat[:3,3];pr=v@n;weight=np.exp(-(pr-pr.min())/.0002);out.append(weight@v/weight.sum())
  return np.array(out)
 jac=np.zeros((5,3,20))
 for k in ids:
  delta=np.zeros(20);delta[k]=1e-5;jac[:,:,k]=(points(q0+delta)-points(q0-delta))/2e-5
 maps={f:np.linalg.pinv(jac[FINGERS.index(f)][:,start:start+4].T) for f,start in [('thumb',16),('middle',4),('pinky',8)]}
 desired={f:np.array(nominal['equilibrium_audit']['planned_force_on_knife_N'][nominal['equilibrium_audit']['active_fingers'].index(f)]) for f in ['thumb','middle','pinky']}
 def full(x):q=target.copy();q[ids]=x;return q
 def objective(x):
  q=full(x);value=.01*np.sum((x-target[ids])**2)
  for f,start in [('thumb',16),('middle',4),('pinky',8)]:value+=np.sum((maps[f]@(kp[start:start+4]*(q[start:start+4]-q0[start:start+4]))-desired[f])**2)
  return float(value)
 def tablegaps(q):
  frames=h.forward(q);rows=[]
  for name,meshes in g.meshes.items():
   mat=world@w@frames[name]
   for v,n in meshes:
    v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];pv=(v-np.array([.6,-.25,.725]))@axes.T;r=abs(axes)@np.array([.3,.4,.025]);rows.append(float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max()))
  return np.array(rows)
 def constraints(x):
  q=full(x);values=[]
  for alpha in [.25,.5,.75,1.]:
   current=q0*(1-alpha)+q*alpha;values.extend((tablegaps(current)-.0003)*1000)
   for f in ['thumb','middle','pinky']:values.extend((r['gap_lower_bound_m']-.000015)*1000 for r in g.self_gaps(current,f,certify_clearance_m=.000015))
  pts=points(q)
  for f in ['middle','pinky']:
   point=pts[FINGERS.index(f)];values.extend([(point[0]+.0075)*1000,(-.0045-point[0])*1000])
  return np.array(values)
 lo=np.maximum(h.lower[ids]+.005,q0[ids]-.20);hi=np.minimum(h.upper[ids]-.005,q0[ids]+.20);start=time.monotonic();fit=minimize(objective,np.clip(target[ids],lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=100,ftol=1e-10));q=full(fit.x);passed=bool(constraints(fit.x).min()>=-1e-4);j['close_q']=q.tolist();j['close_waypoints'][-1]['q']=q.tolist();j['table_preload_projection']=dict(passed=passed,optimizer_success=bool(fit.success),message=fit.message,minimum_constraint=float(constraints(fit.x).min()),estimated_linear_forces_N={f:(maps[f]@(kp[start:start+4]*(q[start:start+4]-q0[start:start+4]))).tolist() for f,start in [('thumb',16),('middle',4),('pinky',8)]},seconds=time.monotonic()-start,source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.touch_plan,a.nominal_plan,a.localization]},scope=__doc__);a.output.write_text(json.dumps(j,indent=2));print(json.dumps(j['table_preload_projection']),flush=True);assert passed,'Do not execute rejected table preload'
if __name__=='__main__':main()
