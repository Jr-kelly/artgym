"""Simple original-PD normal impedance hypothesis, no force equilibrium claim.
A static-wrench optimization failure is not a theorem about the physical grasp.
Known nominal contact Jacobians produce finite targets; actual gravity/free knife
must establish the resulting contact configuration in a labelled held rollout.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--retain-thumb-target',action='store_true',help='Retain supplied known thumb target for index-only insertion, requires zero thumb preference');p.add_argument('--retain-support-target-from',type=Path,help='Keep original finite supportmotor targets while recomputing thumb normalpreload; no forceclaim');p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--project-thumb-self',action='store_true');p.add_argument('--project-active-self',action='store_true',help='Project all requested nonzero nominalfingerloads within originalselfgeometry; forces remain unmeasured');p.add_argument('--normal-preferences',type=float,nargs=5,default=[.9,.4,.55,0.,.5]);a=p.parse_args();assert not a.output.exists();j=json.loads(a.plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;q=np.array(j['touch_q']);w=np.array(j['wrist_in_knife']);normal=np.array(j['contact_normals']);kp=np.array(OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').dof_props.stiffness)
 def points(q):
  frames=h.forward(q);out=[]
  for f,n in zip(FINGERS,normal):
   t=w@frames[j.get('contact_link_by_finger',{}).get(f,'hand_r_'+f+'_pad_link')];v=np.concatenate([v for v,_ in g.meshes[j.get('contact_link_by_finger',{}).get(f,'hand_r_'+f+'_pad_link')]]);v=v@t[:3,:3].T+t[:3,3];pr=v@n;weight=np.exp(-(pr-pr.min())/.0002);out.append(weight@v/weight.sum())
  return np.array(out)
 jac=np.empty((5,3,20))
 for index in range(20):
  delta=np.zeros(20);delta[index]=1e-5;jac[:,:,index]=(points(q+delta)-points(q-delta))/2e-5
 preference=np.array(a.normal_preferences);assert np.all(preference>=0) and np.all(preference<=1.5)
 active=[FINGERS.index(f) for f in j['active_fingers']];inactive=[i for i in range(5) if i not in active];preference[inactive]=0.;forces=-normal*preference[:,None];tau=np.einsum('fij,fi->j',jac,forces);target=np.clip(q+tau/kp,h.lower+.005,h.upper-.005)
 if a.retain_support_target_from:
  retained=np.array(json.loads(a.retain_support_target_from.read_text())['close_q'])
  for f,start in [('index',0),('middle',4),('pinky',8),('ring',12)]:
   if preference[FINGERS.index(f)]==0:target[start:start+4]=retained[start:start+4]
 if a.retain_thumb_target:
  assert a.retain_support_target_from and preference[0]==0 and not a.project_thumb_self
  target[16:]=retained[16:]
 projection=None
 if a.project_thumb_self:
  nominal=target.copy();force_map=np.linalg.pinv(jac[0,:,16:].T)
  def clearance(x):
   full=target.copy();full[16:]=x
   return np.array([r['gap_lower_bound_m'] for r in g.self_gaps(full,'thumb',certify_clearance_m=.000015)])
  def objective(x):return float(np.sum((force_map@(kp[16:]*(x-q[16:]))-forces[0])**2)+.01*np.sum((x-nominal[16:])**2))
  lo=np.maximum(h.lower[16:]+.005,q[16:]-.2);hi=np.minimum(h.upper[16:]-.005,q[16:]+.2)
  fit=minimize(objective,np.clip(target[16:],lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=lambda x:(clearance(x)-.000015)*1000)],options=dict(maxiter=100,ftol=1e-11))
  target[16:]=fit.x;projection=dict(success=bool(fit.success),message=fit.message,nominal_target=nominal.tolist(),minimum_thumb_gap_m=float(clearance(fit.x).min()),nominal_linear_force_after_projection_N=(force_map@(kp[16:]*(fit.x-q[16:]))).tolist(),scope='Known nominal geometry only; actual pressure and closing path separately validated')
 if a.project_active_self:
  starts={'thumb':16,'index':0,'middle':4,'ring':12,'pinky':8};requested=[f for f in FINGERS if preference[FINGERS.index(f)]>0];ids=np.array([k for f in requested for k in range(starts[f],starts[f]+4)]);maps={f:np.linalg.pinv(jac[FINGERS.index(f)][:,starts[f]:starts[f]+4].T) for f in requested};nominal=target.copy()
  def full(x):v=target.copy();v[ids]=x;return v
  def constraints(x):
   v=full(x);return np.array([(r['gap_lower_bound_m']-.000015)*1000 for f in FINGERS for r in g.self_gaps(v,f,certify_clearance_m=.000015)])
  def cost(x):
   v=full(x);value=.01*np.sum((x-nominal[ids])**2)
   for f in requested:
    start=starts[f];value+=np.sum((maps[f]@(kp[start:start+4]*(v[start:start+4]-q[start:start+4]))-forces[FINGERS.index(f)])**2)
   return float(value)
  lo=np.maximum(h.lower[ids]+.005,q[ids]-.2);hi=np.minimum(h.upper[ids]-.005,q[ids]+.2);fit=minimize(cost,np.clip(target[ids],lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=100,ftol=1e-11));target[ids]=fit.x;projection=dict(active_fingers=requested,success=bool(fit.success),message=fit.message,minimum_constraint=float(constraints(fit.x).min()),scope='Knownnominal linearwrench and originalselfgeometry projection; actualpressure/transition physicsunverified')
 gaps=[]
 for f in FINGERS:gaps+=g.self_gaps(target,f,certify_clearance_m=.000015)
 negative=[r for r in gaps if r['gap_lower_bound_m']<.000015-1e-9];passed=not negative
 j['close_q']=target.tolist();j['close_waypoints']=[dict(fraction=0.,q=j['open_q']),dict(fraction=2/3,q=j['touch_q']),dict(fraction=1.,q=target.tolist())]
 j['equilibrium_audit']=dict(method='Simple normal-only impedance hypothesis; no staticwrench optimization or balance claim',optimizer_success=False,normal_impedance_hypothesis=True,planned_force_on_knife_N=forces[active].tolist(),active_fingers=[FINGERS[i] for i in active],normal_N=preference[active].tolist(),nominal_motor_tau_Nm=tau.tolist(),offset_unclipped_rad=(tau/kp).tolist(),offset_actual_rad=(target-q).tolist(),source_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),original_motor_self_geometry_passed=passed,uncertified_self_pairs=negative,scope='Nominal geometric Jacobian-to-PD targets, not measured/constant force. Physics may settle into a different contact pose; original free object, gravity and actuator constraints required.')
 j['equilibrium_audit']['thumb_self_projection']=projection
 j['equilibrium_audit']['retained_support_source']=str(a.retain_support_target_from) if a.retain_support_target_from else None
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(j,indent=2));print(json.dumps(dict(passed=passed,uncertified_pairs=len(negative),normal_preference_N=preference.tolist())));assert passed,'Do not execute uncertified motor self-intersection'
if __name__=='__main__':main()
