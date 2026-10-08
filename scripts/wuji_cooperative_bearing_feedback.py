"""One resolved-motion controller for coupled wrist and three fingers.

Explicit simulation pose/joint and native normal interfaces. All 19 active DOFs
are solved together, keeping the loaded cap point and Index2 while Index4 rolls
on its original back surface. Actual hand clearances enter the same solve.
Motor increments retain issued preload; no force/gain sweep or independent
finger trackers. Original physics/PD/limits determine load. New native Middle
bearing must be observed before its acquisition motion stops.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import lsq_linear
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import convex_intersection_radius

class CooperativeBearingFeedback:
 def __init__(self,spec,output):
  self.s=spec;self.f=FunctionalEntryAffordance();self.g=self.f.g
  for name,meshes in self.g.meshes.items():self.g.meshes[name]=[(v,np.unique(n,axis=0))for v,n in meshes]
  geo=json.load(open(spec['geometry']));motor=json.load(open(spec['motor']));pre=json.load(open(spec['precheck']));assert geo['passed']and pre['passed'];self.rows=geo['rows']+[pre['closure']];self.times=np.array([r['time_s']for r in motor['rows'][2:-1]]);assert len(self.times)==len(self.rows);self.ids=np.r_[np.arange(7),np.arange(7,15),np.arange(23,27)];self.step=np.r_[np.full(7,.004),np.full(12,.012)];self.primary_bearings=geo['actual_primary_bearings'];self.names=[b['hand_link']for b in self.primary_bearings]+['hand_r_middle_pad_link'];self.material=[np.array(b['material_point'])for b in geo['actual_primary_bearings']];last=self.rows[-1];L=np.array(last['wrist_in_knife']);T=L@self.g.w.forward(last['hand_q'])[self.names[-1]];V=np.concatenate([v for v,n in self.g.meshes[self.names[-1]]]);P=V@T[:3,:3].T+T[:3,3];self.material.append(V[P[:,0].argmax()]);self.targets=[]
  for r in self.rows:
   L=np.array(r['wrist_in_knife']);F=self.g.w.forward(r['hand_q']);T=L@F[self.names[-1]];self.targets.append(T[:3,:3]@self.material[-1]+T[:3,3])
  self.targets=np.array(self.targets);self.references=np.array([np.r_[r['arm_q'],r['hand_q']]for r in self.rows]);self.hybrid=bool(spec.get('hybrid_normal_feedback'));self.normal_targets=np.array([np.linalg.norm(b['normal_only_knife_N'])for b in self.primary_bearings]);self.normal_axes=np.array([b['normal_only_knife_N']for b in self.primary_bearings])/self.normal_targets[:,None];self.kp=np.r_[[j['stiffness']for j in json.load(open('assets/robots/g2_wuji/audit.json'))['active_arm']],json.load(open('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json'))['direct_pickup']['hand_kp']];self.anchor=None;self.clearance_targets={};self.freeze=False;self.first_load=None;self.course_age=0.;self.last_t=None;self.stream=(Path(output)/'cooperative-bearing-feedback.jsonl').open('w',buffering=1)
 def points(self,q,invO):
  L=invO@self.f.kin.forward(q[:7]);F=self.g.w.forward(q[7:]);return np.array([(L@F[n])[:3,:3]@m+(L@F[n])[:3,3]for n,m in zip(self.names,self.material)])
 def pair_radius(self,h,pair):
  F=self.g.w.forward(h);vertices=[]
  for name in pair:
   T=F[name];vertices.append([v@T[:3,:3].T+T[:3,3]for v,n in self.g.meshes[name]])
  return max(convex_intersection_radius(a,b)for a in vertices[0]for b in vertices[1])
 def command(self,t,O,arm,hand,issued_arm,issued_hand,slider,contacts):
  q=np.r_[arm,hand].astype(float);issued=np.r_[issued_arm,issued_hand].astype(float);invO=np.linalg.inv(O);P=self.points(q,invO)
  if self.anchor is None:self.anchor=P.copy()
  candidate_pairs=[c for c in self.g.pair_gaps(hand,self.f.H.pairs,certify_clearance_m=.0012)if'middle'in c['link_a']+c['link_b']and c['gap_lower_bound_m']<.0012];radii={tuple((c['link_a'],c['link_b'])):self.pair_radius(hand,(c['link_a'],c['link_b']))for c in candidate_pairs};clear=all(radius<=-.0001 for radius in radii.values());dt=0. if self.last_t is None else t-self.last_t;self.last_t=t
  if clear:self.course_age+=max(0.,dt)
  age=self.course_age
  desired=self.anchor.copy();desired[-1]=np.array([np.interp(age,self.times,self.targets[:,j])for j in range(3)]);reference=np.array([np.interp(age,self.times,self.references[:,j])for j in range(27)]);fn=sum(float(c['normal_magnitude_N'])for c in contacts if 'middle'in c['hand_link']and c['knife_link']=='link_0');normal=sum((np.array(c['force_normal_contribution_knife_N'])for c in contacts if 'middle'in c['hand_link']and c['knife_link']=='link_0'),np.zeros(3))
  if fn>=.05 and self.first_load is None:self.first_load=t
  self.freeze=fn>=.05
  J=np.empty((12,19));eps=1e-5
  for j,c in enumerate(self.ids):
   u=q.copy();d=q.copy();u[c]+=eps;d[c]-=eps;J[:,j]=((self.points(u,invO)-self.points(d,invO))/2/eps).ravel()
  selected=np.array([0,1,2,4,6,7,8,9,10,11]);weights=np.array([4,4,4,4,4,4,4,1,1,1]);error=desired-P
  if self.freeze:error[-1]=0.
  force_audit=[]
  if self.hybrid:
   task=[];rhs=[]
   for j,name in enumerate(self.names[:3]):
    n=self.normal_axes[j];Q=J[3*j:3*j+3];e=error[j];actual_force=sum(float(c['normal_magnitude_N'])for c in contacts if c['hand_link']==name and c['knife_link']==('link_1'if j==2 else 'link_0'));desired_force=self.normal_targets[j];normal_row=n@Q;compliance=float(np.sum(normal_row**2/self.kp[self.ids]));closure=(desired_force-actual_force)*compliance if contacts else 0.
    task.append(normal_row*3);rhs.append(np.clip(closure,-.0002,.0002)*3);tangent=np.eye(3)-np.outer(n,n)
    if j!=1:task.extend(tangent@Q*3);rhs.extend(np.clip(tangent@e,-.0002,.0002)*3)
    force_audit.append(dict(name=name,desired_normal_N=float(desired_force),actual_normal_N=actual_force,analytical_normal_compliance_m_per_N=compliance))
   task.extend(J[9:12]);rhs.extend(np.clip(error[-1],-.0002,.0002));A=np.array(task)*self.step[None,:];b=np.array(rhs)
   # World arm posture from the already feasible reference removes free global drift.
   arm_rows=np.zeros((7,19));arm_rows[:,:7]=np.eye(7)*.03;A=np.r_[A,arm_rows*self.step[None,:]];b=np.r_[b,np.clip((reference-q)[:7]*.03,-.0002,.0002)]
  else:A=J[selected]*self.step[None,:]*weights[:,None];b=np.clip(error.ravel()[selected],-.0002,.0002)*weights
  A=np.r_[A,np.eye(19)*.000015];b=np.r_[b,np.clip((reference-q)[self.ids]/self.step,-1,1)*.000015]
  pairs=sorted(candidate_pairs,key=lambda c:radii[(c['link_a'],c['link_b'])],reverse=True)[:2];barriers=[]
  for c in pairs:
   pair=[(c['link_a'],c['link_b'])];key=tuple(pair[0]);radius=self.pair_radius(hand,key)
   if key not in self.clearance_targets:self.clearance_targets[key]=-.00015
   limit=self.clearance_targets[key]
   if radius<=limit+1e-7:continue
   grad=np.zeros(19)
   for j,index in enumerate(self.ids):
    if index<7:continue
    u=hand.copy();d=hand.copy();u[index-7]+=eps;d[index-7]-=eps;gu=self.pair_radius(u,key);gd=self.pair_radius(d,key);grad[j]=-(gu-gd)/2/eps
   A=np.r_[A,(grad*self.step*3)[None,:]];b=np.r_[b,max(0.,radius-limit)*.25*3];barriers.append(dict(pair=pair[0],actual_gap_lower_bound_m=c['gap_lower_bound_m'],exact_intersection_radius_m=radius,target_radius_m=limit))
  delta=lsq_linear(A,b,bounds=(-1,1),tol=1e-7,max_iter=50).x*self.step;accepted=0.
  for fraction in[1.,.5,.25,0.]:
   predicted=q.copy();predicted[self.ids]+=delta*fraction
   if not self.f.H.inspect(predicted[7:]):accepted=fraction;break
  command=issued.copy();command[self.ids]+=delta*accepted;command=np.clip(command,np.r_[self.f.kin.lower,self.g.w.lower],np.r_[self.f.kin.upper,self.g.w.upper]);self.stream.write(json.dumps(dict(time_s=float(t),course_age_s=age,initial_clearance_stage=not clear,hybrid_normal_feedback=self.hybrid,original_primary_normal_targets_N=self.normal_targets.tolist(),normal_feedback_audit=force_audit,primary_errors_m=(desired-P)[:3].tolist(),new_Middle_point_error_m=float(np.linalg.norm(desired[-1]-P[-1])),new_Middle_normal_N=fn,new_Middle_normal_knife_N=normal.tolist(),first_load_time_s=self.first_load,acquisition_frozen=self.freeze,actual_self_barriers=barriers,accepted_fraction=accepted,motor_increment_rad=delta.tolist(),scope=__doc__))+'\n');return command[:7],command[7:]
