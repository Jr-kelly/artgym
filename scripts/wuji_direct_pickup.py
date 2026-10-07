"""Motor-only direct pickup; one explicit pose observation, no state setters."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform

def smooth(u):
 u=np.clip(u,0,1);return u*u*u*(10-15*u+6*u*u)

class DirectPickup:
 def __init__(self,spec,output):
  self.s=spec;self.output=Path(output);self.k=G2Kinematics();self.arm=np.array(spec['initial_arm_q']);self.rows=None
  self.pressure_offset=np.zeros(20)
  if spec.get('loading_motor_prior'):
   prior=json.loads(Path(spec['loading_motor_prior']).read_text());self.loading_times=np.array([r['elapsed_s'] for r in prior['rows']]);self.loading_hands=np.array([r['hand_q'] for r in prior['rows']])
  if spec.get('pregrasp_thumb_mesh_clearance_m') is not None or spec.get('thumb_only_table_clearance_m') is not None or spec.get('early_ring_q') is not None or spec.get('loaded_middle_table_clearance_m') is not None:
   from scripts.g2_contact_geometry import DigitGeometry
   self.clearance_geometry=DigitGeometry(knife_spec=Path(spec['knife_spec']) if spec.get('free_thumb_knife_clearance_m') else None)
  if spec.get('grip_normal_reference_N'):
   from scripts.wuji_kinematics import WujiKinematics
   self.h=WujiKinematics();self.pressure_log=self.output/'direct-grip-pressure.jsonl'
 def command(self,elapsed,actual_object,actual_arm,actual_hand,issued_arm,issued_hand,slider=None):
  if self.rows is None and elapsed>=1:
   O=actual_object.copy();O[0,3]+=self.s.get('pose_bias_x_m',0.);self.observed_object=O;L=np.array(self.s['wrist_in_knife']);W=O@L;start=self.k.forward(issued_arm);arm=actual_arm.astype(float);rows=[];errors=[]
   for t in np.arange(1,self.s['duration_s']+1/60,1/30):
    if t<3:
     u=smooth((t-1)/2);goal=W.copy();goal[2,3]+=self.s.get('pregrasp_clearance_m',0.);goal[:3,3]=start[:3,3]*(1-u)+goal[:3,3]*u;hand=np.array(self.s['open_q'])
    else:
     goal=W.copy()
     goal[2,3]+=self.s.get('pregrasp_clearance_m',0.)*(1-smooth((t-3)/1.))
     if self.s.get('table_pitch_degrees'):
      from scripts.g2_knife_geometry import KnifeGeometry
      angle=float(self.s['table_pitch_degrees'])*smooth((t-5)/1.5)
      tilted=O@transform(quaternion=Rotation.from_euler('x',angle,degrees=True).as_quat())
      tilted=KnifeGeometry(Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')).table_pose(tilted)
      goal=tilted@L;goal[2,3]+=self.s.get('lift_m',.12)*smooth((t-8)/3)
     elif self.s.get('table_rock_degrees'):
      from scripts.g2_knife_geometry import KnifeGeometry
      angle=float(self.s['table_rock_degrees'])*smooth((t-5)/2);tilted=O@transform(quaternion=Rotation.from_euler('z',angle,degrees=True).as_quat());tilted=KnifeGeometry(Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')).table_pose(tilted);goal=tilted@L;goal[2,3]+=self.s.get('lift_m',.12)*smooth((t-7)/3)
     else:goal[2,3]+=self.s.get('lift_m',.12)*smooth((t-5)/3)
     u=smooth((t-3)/2);hand=np.array(self.s['open_q'])*(1-u)+np.array(self.s['close_q'])*u
    if self.s.get('thumb_closure_start_s') is not None:
     u=smooth((t-self.s['thumb_closure_start_s'])/self.s['thumb_closure_duration_s'])
     hand[-4:]=(1-u)*np.array(self.s['open_q'])[-4:]+u*np.array(self.s['close_q'])[-4:]
    if self.s.get('pregrasp_thumb_mesh_clearance_m') is not None and t<5.:
     frames=self.clearance_geometry.w.forward(hand);lowest=np.inf
     for name,parts in self.clearance_geometry.meshes.items():
      if '_thumb_' not in name:continue
      T=goal@frames[name]
      for vertices,_ in parts:
       lowest=min(lowest,float((vertices@T[:3,:3].T+T[:3,3])[:,2].min()))
     goal[2,3]+=max(0.,self.s.get('table_height_m',.75)+self.s['pregrasp_thumb_mesh_clearance_m']-lowest)
    if self.s.get('thumb_only_table_clearance_m') is not None and t<5.:
     # Preserve the successful opposing carriers and wrist. Only the free
     # thumb takes a coordinated table-clear path; no object/physics writes.
     knife_clearance=self.s.get('free_thumb_knife_clearance_m',0.)*(1-smooth((t-3.4)/.6))
     hand=self.clear_thumb(hand,goal,free=t<4.,avoid_object_world=O if knife_clearance>0 else None,knife_clearance_m=knife_clearance)
    arm,e=self.k.solve_near(goal,arm,max_step=.12,minimum_margin=self.s.get('arm_command_margin_rad',0.));rows.append(dict(time_s=float(t),arm_q=arm.tolist(),hand_q=hand.tolist()));errors.append(e)
   self.rows=rows;self.times=np.array([r['time_s'] for r in rows]);self.arms=np.array([r['arm_q'] for r in rows]);self.hands=np.array([r['hand_q'] for r in rows]);self.output.joinpath('direct-pose-and-motor-plan.json').write_text(json.dumps(dict(observation_elapsed_s=float(elapsed),pose_source='sim_estimate' if self.s.get('pose_bias_x_m') else 'sim_oracle',bias_x_m=self.s.get('pose_bias_x_m',0.),observed_object_world=O.tolist(),rows=rows,ik=errors,physical_state_resets=0),indent=2))
  if self.rows is None:return self.arm.copy(),np.array(self.s['open_q'])
  aq=np.array([np.interp(elapsed,self.times,self.arms[:,j]) for j in range(7)]);hq=np.array([np.interp(elapsed,self.times,self.hands[:,j]) for j in range(20)])
  prior_until=self.s.get('loading_motor_prior_until_s',float('inf'))
  if self.s.get('loading_motor_prior') and 4<=elapsed<prior_until:
   hq=np.array([np.interp(elapsed,self.loading_times,self.loading_hands[:,j]) for j in range(20)])
  if self.s.get('loading_motor_prior') and elapsed>=prior_until and not hasattr(self,'loading_prior_transferred'):
   self.pressure_offset=np.clip(issued_hand-hq,-.1,.1);self.loading_prior_transferred=True
   (self.output/'direct-loading-history-transfer.json').write_text(json.dumps(dict(elapsed_s=float(elapsed),previously_issued=issued_hand.tolist(),base_reference=hq.tolist(),acquired_offset=self.pressure_offset.tolist(),scope='Motor preload history only; no physicalstate setter'),indent=2))
  if self.s.get('grip_normal_reference_N') and elapsed>=4 and (not self.s.get('loading_motor_prior') or elapsed>=prior_until):
   kp=np.array(self.s['hand_kp']);W=self.k.forward(actual_arm);diag={}
   loaded=self.s.get('loaded_grip_material_points') is not None and elapsed>=self.s.get('loaded_middle_capture_s',5.5)
   materials=self.s['loaded_grip_material_points'] if loaded else self.s['material_points']
   references={name:(1.4 if '_thumb_' in name else .7) for name in materials} if loaded else self.s['grip_normal_reference_N']
   for name,preferred in references.items():
    finger=name.split('_')[2];ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];m=np.array(materials[name]);d=np.array([1,0,0]) if finger=='thumb' else np.array([-1,0,0]);d=W[:3,:3].T@(actual_object if loaded else self.observed_object)[:3,:3]@d
    def point(q):
     T=self.h.forward(q)[name];return T[:3,:3]@m+T[:3,3]
    P=point(actual_hand);J=np.empty((3,4))
    for j,index in enumerate(ids):
     q=actual_hand.astype(float).copy();q[index]+=1e-5;J[:,j]=(point(q)-P)/1e-5
    tau=kp[ids]*(issued_hand[ids]-actual_hand[ids]);force=np.linalg.solve(J@J.T+np.eye(3)*1e-7,J@tau);estimate=float(d@force);error=float(preferred)-estimate
    support=self.s.get('grip_support_world_up_N',{}).get(finger,0.)*smooth((elapsed-4.8)/.5)
    if support:
     reference=d*float(preferred)+W[:3,:3].T@np.array([0.,0.,support]);vector_error=reference-force
     delta=J.T@vector_error/kp[ids]*.25 if np.linalg.norm(vector_error)>.12 else np.zeros(4)
    else:delta=(J.T@d)*error/kp[ids]*.25 if abs(error)>.12 else np.zeros(4)
    self.pressure_offset[ids]=np.clip(self.pressure_offset[ids]+delta,-.1,.1);diag[name]=dict(preferred_estimated_normal_N=float(preferred),joint_deflection_estimated_N=estimate,reference_world_up_N=float(support),joint_deflection_vector_proxy_handframe_N=force.tolist(),offset_rad=self.pressure_offset[ids].tolist())
   hq=np.clip(hq+self.pressure_offset,self.h.lower,self.h.upper)
   with self.pressure_log.open('a') as f:f.write(json.dumps(dict(elapsed_s=float(elapsed),joints_only_pressure_proxy=diag,scope='Boundedoriginal.1radoffset, nativeforcevaries; noactualcontact/forcefeedback. Normalorientationfromoneinitialpose+measuredarmFK.'))+'\n')
  if self.s.get('thumb_only_table_clearance_m') is not None and elapsed<5.:
   # Predict the next wrist target using the measured tracking transform.
   # A target-only clearance missed the approach's measured 1.45mm lag.
   predicted=self.k.forward(actual_arm)@np.linalg.inv(self.k.forward(issued_arm))@self.k.forward(aq)
   lag=np.clip(actual_hand-issued_hand,-.03,.03) if elapsed<4. else np.clip(actual_hand-issued_hand,-.2,.2) if self.s.get('loaded_thumb_table_joint_lag',False) else np.zeros(20)
   extra_clearance=self.s.get('early_free_thumb_clearance_m')
   clearance_m=self.s['thumb_only_table_clearance_m']
   if extra_clearance is not None:
    # The saved 2.667s native touchdown happened despite the 0.2mm reference.
    # Add free-motion space, then return to the acquired loading envelope.
    active=smooth((elapsed-1.8)/.4)*(1-smooth((elapsed-3.)/.5))
    clearance_m+=(extra_clearance-clearance_m)*active
   knife_clearance=self.s.get('free_thumb_knife_clearance_m',0.)*(1-smooth((elapsed-3.4)/.6))
   hq=self.clear_thumb(hq,predicted,lag,free=elapsed<4.,clearance_m=clearance_m,
       avoid_object_world=actual_object if knife_clearance>0 else None,knife_clearance_m=knife_clearance)
  if self.s.get('loaded_middle_material') is not None and elapsed>=self.s.get('loaded_middle_capture_s',5.5):
   from scipy.optimize import least_squares
   m=np.array(self.s['loaded_middle_material']);name='hand_r_middle_pad_link'
   L=np.linalg.inv(actual_object)@self.k.forward(actual_arm)
   if not hasattr(self,'middle_capture'):
    T=L@self.h.forward(actual_hand)[name];P=T[:3,:3]@m+T[:3,3]
    # The prior is an actual native side contact. Capture this episode's
    # location; only the original 0.7N bounded motor preload remains active.
    self.middle_capture=P.copy()
    self.middle_capture_q=actual_hand[4:8].astype(float).copy()
    self.middle_capture_preload=issued_hand[4:8]-actual_hand[4:8]
    self.middle_capture_offset=self.pressure_offset[4:8].copy()
   seed=actual_hand[4:8].astype(float)
   def residual(x):
    q=actual_hand.astype(float).copy();q[4:8]=x;T=L@self.h.forward(q)[name]
    return np.r_[(T[:3,:3]@m+T[:3,3]-self.middle_capture)*300,(x-self.middle_capture_q)*.08]
   fit=least_squares(residual,np.clip(seed,self.h.lower[4:8]+.02,self.h.upper[4:8]-.02),bounds=(self.h.lower[4:8]+.02,self.h.upper[4:8]-.02),max_nfev=35)
   # Move the reference with the acquired material, retaining its bounded
   # preload. The arm still follows the fixed lift, never chases the object.
   preload=self.middle_capture_preload+self.pressure_offset[4:8]-self.middle_capture_offset
   hq[4:8]=np.clip(fit.x+preload,self.h.lower[4:8]+.01,self.h.upper[4:8]-.01)
   with (self.output/'direct-middle-material-guard.jsonl').open('a') as f:
    f.write(json.dumps(dict(elapsed_s=float(elapsed),captured_point_knife_m=self.middle_capture.tolist(),material_point=m.tolist(),position_error_m=float(np.linalg.norm(residual(fit.x)[:3])/300),actual_relative_wrist=L.tolist(),scope='Sim_oracle live pose hand-only material IK; original bounded preload; no native contact input, object state writes, or object-follow arm'))+'\n')
  if self.s.get('center_side_contacts') and elapsed>=6.5:
   from scipy.optimize import least_squares
   L=np.linalg.inv(actual_object)@self.k.forward(actual_arm)
   if not hasattr(self,'center_capture'):
    F=self.h.forward(actual_hand);self.center_capture={}
    for name,m in self.s['material_points'].items():
     finger=name.split('_')[2];ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];T=L@F[name];P=T[:3,:3]@np.array(m)+T[:3,3]
     self.center_capture[name]=dict(point=P.copy(),q=actual_hand[ids].astype(float).copy(),preload=issued_hand[ids]-actual_hand[ids],offset=self.pressure_offset[ids].copy())
   u=smooth((elapsed-6.5)/1.5)
   for name,m in self.s['material_points'].items():
    finger=name.split('_')[2];ids=[self.h.names.index('hand_r_'+finger+'_joint'+str(j)) for j in range(1,5)];cap=self.center_capture[name];target=cap['point'].copy();target[1]*=1-u;m=np.array(m)
    def residual(x):
     q=actual_hand.astype(float).copy();q[ids]=x;T=L@self.h.forward(q)[name]
     return np.r_[(T[:3,:3]@m+T[:3,3]-target)*300,(x-cap['q'])*.08]
    lower=self.h.lower[ids]+.025;upper=self.h.upper[ids]-.025
    fit=least_squares(residual,np.clip(actual_hand[ids],lower,upper),bounds=(lower,upper),max_nfev=45)
    preload=cap['preload']+self.pressure_offset[ids]-cap['offset'];hq[ids]=np.clip(fit.x+preload,self.h.lower[ids],self.h.upper[ids])
    with (self.output/'direct-side-centering.jsonl').open('a') as f:f.write(json.dumps(dict(elapsed_s=float(elapsed),link=name,target_knife_m=target.tolist(),position_error_m=float(np.linalg.norm(residual(fit.x)[:3])/300),scope='Hand-only truepad middle-side adjustment afterphysicaltablepitch; issuedpreloadcontinuous, no object writes'))+'\n')
  if self.s.get('early_ring_q') is not None:
   from scipy.optimize import minimize
   u=smooth((elapsed-3.)/3.);hq[12:16]=(1-u)*np.array(self.s['open_q'])[12:16]+u*np.array(self.s['early_ring_q'])
   g=self.clearance_geometry
   predicted=self.k.forward(actual_arm)@np.linalg.inv(self.k.forward(issued_arm))@self.k.forward(aq)
   lag=np.clip(actual_hand-issued_hand,-.03,.03)
   def clear_ring(x):
    q=hq.copy();q[12:16]=x;q+=lag;F=g.w.forward(q);values=[]
    for name,parts in g.meshes.items():
     if '_ring_' not in name:continue
     T=predicted@F[name]
     for v,_ in parts:values.append(float((v@T[:3,:3].T+T[:3,3])[:,2].min()-.7502))
    return np.array(values)
   seed=hq[12:16].copy()
   if clear_ring(seed).min()<0:
    fit=minimize(lambda x:float(np.sum((x-seed)**2)),seed,method='SLSQP',bounds=list(zip(g.w.lower[12:16]+.04,g.w.upper[12:16]-.04)),constraints=[dict(type='ineq',fun=clear_ring)],options=dict(maxiter=60,ftol=1e-11))
    if clear_ring(fit.x).min()<-1e-6:raise RuntimeError('Early ring cannot remain above table')
    hq[12:16]=fit.x
  hq=self.clear_loaded_middle(elapsed,actual_object,actual_arm,actual_hand,issued_arm,issued_hand,aq,hq)
  return aq,hq
 def clear_loaded_middle(self,elapsed,O,arm,hand,issued_arm,issued_hand,aq,hq):
  """Project only the loaded Middle motor target above the real table.

  Measured joint deflection predicts the loaded pose. The side-contact
  lateral/longitudinal coordinates are retained while its vertical coordinate
  can move. This uses pose/proprioception, never native contact or state writes.
  """
  if self.s.get('loaded_middle_table_clearance_m') is None or not 3.<=elapsed<=self.s.get('loaded_middle_table_guard_until_s',8.):return hq
  from scipy.optimize import minimize
  g=self.clearance_geometry
  W=self.k.forward(arm)@np.linalg.inv(self.k.forward(issued_arm))@self.k.forward(aq)
  L=np.linalg.inv(O)@W
  lag=np.clip(hand-issued_hand,-.2,.2)
  material=np.array(self.s['material_points']['hand_r_middle_pad_link'])
  floor=self.s.get('table_height_m',.75)+self.s['loaded_middle_table_clearance_m']
  def geometry(x):
   q=hq.astype(float).copy();q[4:8]=x;q+=lag;F=g.w.forward(q)
   T=L@F['hand_r_middle_pad_link'];P=T[:3,:3]@material+T[:3,3]
   height=[]
   for name,parts in g.meshes.items():
    if '_middle_' not in name:continue
    T=W@F[name]
    height.extend(float((v@T[:3,:3].T+T[:3,3])[:,2].min()-floor) for v,_ in parts)
   return P,np.array(height)
  seed=hq[4:8].astype(float);P0,clear=geometry(seed)
  if clear.min()>=0:return hq
  def objective(x):
   P,_=geometry(x)
   # Knife X is the side normal; Z is the longitudinal axis.
   return float(np.sum((x-seed)**2)+np.sum((P[[0,2]]-P0[[0,2]])**2)*9e4)
  lower=g.w.lower[4:8]+.01-lag[4:8];upper=g.w.upper[4:8]-.01-lag[4:8]
  lower=np.maximum(lower,g.w.lower[4:8]+.01);upper=np.minimum(upper,g.w.upper[4:8]-.01)
  fit=minimize(objective,np.clip(seed,lower,upper),method='SLSQP',bounds=list(zip(lower,upper)),
      constraints=[dict(type='ineq',fun=lambda x:geometry(x)[1])],options=dict(maxiter=60,ftol=1e-10))
  P,clear_after=geometry(fit.x)
  if clear_after.min()<-1e-6:raise RuntimeError('Loaded Middle table projection infeasible: '+str(clear_after.min()))
  out=hq.copy();out[4:8]=fit.x
  with (self.output/'direct-loaded-middle-table-guard.jsonl').open('a') as f:
   f.write(json.dumps(dict(elapsed_s=float(elapsed),measured_joint_lag_rad=lag[4:8].tolist(),
       motor_correction_rad=(fit.x-seed).tolist(),predicted_table_clearance_m=float(clear_after.min()+self.s['loaded_middle_table_clearance_m']),
       side_longitudinal_shift_m=(P[[0,2]]-P0[[0,2]]).tolist(),scope='Proprioceptive loaded pose prediction; original PD/physics; not actual contact clearance'))+'\n')
  return out
 def clear_thumb(self,q,W,joint_lag=None,free=True,clearance_m=None,avoid_object_world=None,knife_clearance_m=0.):
  from scipy.optimize import minimize
  g=self.clearance_geometry;original=q[-4:].copy()
  def clearance(x):
   h=q.copy();h[-4:]=x
   if joint_lag is not None:h=h+joint_lag
   frames=g.w.forward(h);values=[]
   for name,parts in g.meshes.items():
    if '_thumb_' not in name:continue
    T=W@frames[name]
    for vertices,_ in parts:
     values.append(float((vertices@T[:3,:3].T+T[:3,3])[:,2].min()-self.s.get('table_height_m',.75)-(self.s['thumb_only_table_clearance_m'] if clearance_m is None else clearance_m)))
   if avoid_object_world is not None:
    L=np.linalg.inv(avoid_object_world)@W
    values.extend(v['gap_lower_bound_m']-knife_clearance_m for v in g.gaps(h,L,0.,'thumb'))
   return np.array(values)
  # Free-motion reserve must not attenuate the original loaded grip preload.
  margin=self.s.get('free_thumb_command_margin_rad',.025) if free else 0.
  lower=g.w.lower[-4:]+margin;upper=g.w.upper[-4:]-margin
  start=np.clip(original,lower,upper)
  if clearance(start).min()>=0:
   out=q.copy();out[-4:]=start;return out
  fit=minimize(lambda x:float(np.sum((x-original)**2)),start,method='SLSQP',bounds=list(zip(lower,upper)),constraints=[dict(type='ineq',fun=clearance)],options=dict(maxiter=60,ftol=1e-11))
  if clearance(fit.x).min()<-1e-6:
   raise RuntimeError('No table-clear thumb path at fixed carrier wrist: '+str(clearance(fit.x).min()))
  out=q.copy();out[-4:]=fit.x;return out
