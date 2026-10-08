"""Read-only B-reference affordance; no motor or physical state mutation.

The tail roof patch is a soft prior from actual773 B-capable geometry.
Only the original full stroke reference IK and actual hand hull reject entry.
Neither proves capacity; original B still executes in current physics.
"""
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_measured_hold_reference import measured_hold_path
from scripts.g2_kinematics import G2Kinematics

class FunctionalEntryAffordance:
 def __init__(self,task_stroke_m=.03):
  self.stroke=float(task_stroke_m)
  if not .020<self.stroke<=.035:raise ValueError('B reference stroke must be >20 mm and <=35 mm')
  self.g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');self.H=HandIntersection();self.kin=G2Kinematics();self.vertices=np.concatenate([v for v,_ in self.g.meshes['hand_r_thumb_pad_link']])
 def assess(self,q27,O,slider,full_path=True):
  return self.assess_relative(np.linalg.inv(O)@self.kin.forward(q27[:7]),q27[7:],slider,full_path)
 def assess_relative(self,X,hand_q,slider,full_path=True):
  """Assess an exact intrinsic pose independently of world arm reachability."""
  T=self.g.w.forward(hand_q)['hand_r_thumb_pad_link'];P=X@T;v=self.vertices@P[:3,:3].T+P[:3,3];weights=np.exp(-(v[:,1]-v[:,1].min())/.0002);foot=weights@v/weights.sum();center=self.g.knife_geometry.joint_xyz+self.g.knife_geometry.axis*slider;roof=float(center[1]+.001);region_low=np.array([-.0035,roof,center[2]-.016]);region_high=np.array([.0035,roof,center[2]-.008]);tail_distance=float(np.linalg.norm(foot-np.clip(foot,region_low,region_high)));normal=X[:3,:3].T@np.array([0,1.,0]);rail=X[:3,:3].T@np.array([0,0,1.]);bad=self.H.inspect(hand_q);error=self.stroke;problem=None
  if full_path:
   try:
    _,audit=measured_hold_path(hand_q,normal,rail,np.linspace(0,self.stroke,int(np.ceil(self.stroke/.001))+1));error=max(r['FK_position_error_m'] for r in audit['rows'])
   except ValueError as exc:
    problem=str(exc)
    # Return a graded original-IK endpoint residual without duplicating
    # the trajectory solver or changing its rejection threshold.
    import ast
    try:error=float(ast.literal_eval(problem.split(': ',1)[1])['FK_position_error_m'])
    except (ValueError,SyntaxError,KeyError):error=self.stroke
  result=dict(foot_in_knife_m=foot.tolist(),tail_roof_distance_m=tail_distance,requested_stroke_m=self.stroke,reference_FK_error_m=error,reference_problem=problem,self_intersections=bad,reference_eligible=bool(full_path and problem is None and not bad),scope=__doc__)
  if abs(self.stroke-.03)<1e-12:result.update(full30mm_FK_error_m=error,full30mm_problem=problem)
  return result
