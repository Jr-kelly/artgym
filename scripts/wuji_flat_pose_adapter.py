"""Pose-conditioned motor regeneration. Consumes explicit base-frame pose estimate."""
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_table_collision import ArmTableCollision

def adapt(estimated_world, nominal_world, acquisition, regrasp, seed, table_y=-.23):
 k=G2Kinematics();delta=estimated_world@np.linalg.inv(nominal_world)
 goal=delta@np.asarray(acquisition['grasp_wrist_world']);start=goal.copy();start[0,3]-=.09
 lifted=delta@np.asarray(acquisition['lift_wrist_world'])
 q=np.asarray(seed).copy();parts={};errors=[];collisions=[]
 table=ArmTableCollision(.75,margin=0.,table_y=table_y)
 def segment(a,b,n):
  nonlocal q
  result=[]
  for u in np.linspace(0,1,n):
   x=u**3*(10-15*u+6*u*u);p=a.copy();p[:3,3]=(1-x)*a[:3,3]+x*b[:3,3]
   q,e=k.solve_near(p,q);errors.append(e);result.append(q.copy())
  return np.asarray(result)
 # Solve once near measured current arm; all execution remains finite motor commands.
 q,e=k.solve(start,q);errors.append(e);parts['start_q']=q.copy()
 parts['approach']=segment(start,goal,91);parts['grasp_q']=q.copy();parts['lift']=segment(goal,lifted,121);parts['lift_q']=q.copy()
 if regrasp:
  rr=[]
  for old in regrasp['arm_q']:
   target=delta@k.forward(old);q,e=k.solve_near(target,q);rr.append(q.copy());errors.append(e)
  parts['regrasp_arm']=np.asarray(rr);parts['expected_knife_world']=(delta@np.asarray(regrasp['expected_knife_world'])).tolist()
 for name in ['approach','lift','regrasp_arm']:
  for i,qi in enumerate(parts.get(name,[])):
   if i%10==0:collisions.extend(dict(part=name,frame=i,**c) for c in table.collisions(qi))
 parts['diagnostics']=dict(max_position_error_m=max(e['position_m'] for e in errors),max_rotation_error_rad=max(e['rotation_rad'] for e in errors),arm_table_collisions=collisions,estimated_world=estimated_world.tolist(),scope='Regenerated IK from declared pose; table edge fixed world X. No physical-state changes; finger/table contact verified by simulation.')
 if parts['diagnostics']['max_position_error_m']>.005:raise RuntimeError(parts['diagnostics'])
 return parts
