"""Geometry-guided candidate course to a verified functional intake.

Read-only source and ideal goal guide motor commands; no physical state writes.
Static thumb clearance cannot certify carrying. All27 motors remain trainable.
"""
import argparse,json,time
from pathlib import Path
from functools import lru_cache
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 src=Path('runs/flat-table-20261006/direct/recorded/regrasp-v746-actual-3p5-v748');goal=Path('runs/flat-table-20261006/direct/ideal/late-tail-pad-intake-v771');z=np.load(src/'takeover.npz');end=np.load(goal/'takeover.npz');q=z['robot_q'][7:].astype(float);start=q[16:];finish=end['robot_q'][23:].astype(float);g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@G2Kinematics().forward(z['robot_q'][:7]);slider=float(z['slider_q']);rng=np.random.default_rng(20261008774);H=HandIntersection();began=time.monotonic()
 @lru_cache(maxsize=8192)
 def free(values):
  cur=q.copy();cur[16:]=values
  if min(r['gap_lower_bound_m'] for r in g.gaps(cur,L,slider,'thumb',certify_clearance_m=.0001))<-.00055:return False
  return not H.inspect(cur)
 def edge(x,y,res=.05):return all(free(tuple(x*(1-u)+y*u)) for u in np.linspace(0,1,max(2,int(np.ceil(abs(x-y).max()/res))+1)))
 assert free(tuple(start)) and free(tuple(finish))
 trees=[{'nodes':[start],'parents':[-1]},{'nodes':[finish],'parents':[-1]}];active=0;path=None
 def extend(tree,target):
  pts=np.array(tree['nodes']);idx=int(np.argmin(abs(pts-target).max(-1)));x=pts[idx];delta=target-x;norm=np.linalg.norm(delta);y=x+delta*min(1,.18/max(norm,1e-12))
  if not edge(x,y):return None,False
  tree['nodes'].append(y);tree['parents'].append(idx);return len(tree['nodes'])-1,norm<=.18
 def chain(tree,i):
  rows=[]
  while i>=0:rows.append(tree['nodes'][i]);i=tree['parents'][i]
  return rows[::-1]
 for it in range(500):
  if time.monotonic()-began>90:break
  target=trees[1-active]['nodes'][0] if rng.random()<.35 else rng.uniform(g.w.lower[16:]+.015,g.w.upper[16:]-.015)
  j,_=extend(trees[active],target)
  if j is not None:
   for _ in range(25):
    k,hit=extend(trees[1-active],trees[active]['nodes'][j])
    if k is None:break
    if hit:
     left=chain(trees[active],j);right=chain(trees[1-active],k);path=left+right[-2::-1] if active==0 else right+left[-2::-1];break
  if path is not None:break
  active=1-active
 if path is not None:
  simple=[path[0]];i=0
  while i<len(path)-1:
   j=len(path)-1
   while j>i+1 and not edge(path[i],path[j],.025):j-=1
   simple.append(path[j]);i=j
  path=simple
 report={'found':path is not None,'iterations':it+1,'wall_seconds':time.monotonic()-began,'scope':__doc__}
 if path is not None:
  targets=[];waypoints=[path[0]]
  for x,y in zip(path,path[1:]):
   ticks=int(np.ceil(abs(y-x).max()/.023))
   for j in range(1,ticks+1):waypoints.append(x+(y-x)*j/ticks)
  assert all(free(tuple(x)) for x in waypoints)
  issued=z['issued_target'].astype(float);oldoffset=issued[23:]-start
  for i,x in enumerate(waypoints):
   # Preserve initial issued command; release old body-specific preload
   # continuously as the nominal pad acquires the proven cap entry.
   u=i/(len(waypoints)-1);motor=issued.copy();motor[23:]=x+oldoffset*(1-u);motor[7:]=np.clip(motor[7:],g.w.lower,g.w.upper);targets.append(motor)
  # Actual command slew, rather than only geometric q spacing, is bounded.
  motors=[targets[0]]
  for motor in targets[1:]:
   prev=motors[-1];ticks=int(np.ceil(max(abs(motor[:7]-prev[:7]).max()/.006,abs(motor[7:]-prev[7:]).max()/.025)))
   for i in range(1,max(1,ticks)+1):motors.append(prev+(motor-prev)*i/max(1,ticks))
  duration=(len(motors)-1)/30
  recipe={'required_actual_source':str(src),'rows':[{'time_s':i/30,'arm_q':x[:7].tolist(),'hand_q':x[7:].tolist()} for i,x in enumerate(motors)],'target_object_in_wrist':(np.linalg.inv(G2Kinematics().forward(z['robot_q'][:7]))@transform(z['object_state'][:3],z['object_state'][3:7])).tolist(),'target_hand_q':end['robot_q'][7:].astype(float).tolist(),'scope':__doc__};(a.output/'reference.json').write_text(json.dumps(recipe,indent=2))
  motor=dict(recipe,development_abort_on_translation_m=.08,retained_push_skill={'start_s':duration,'preparation_seconds':4,'knife_spec':'assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json','entry_reference_adaptation':'measured-hold','entry_pressure_coordinates':'cartesian-normal','task_stroke_m':.03});(a.output/'motor.json').write_text(json.dumps(motor,indent=2));report.update(duration_s=duration,path=[x.tolist() for x in path],command_slew_max_rad=float(abs(np.diff(np.array(motors),axis=0)).max()))
 (a.output/'geometry.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));record('functional_transfer_course_geometry_complete',[str(a.output/'geometry.json')],report,next_step='Actual recordedentrance transfer+B once; failure->coupled all27course optimization withprovenfunctionalgoal, not newfingertracker')
if __name__=='__main__':main()
