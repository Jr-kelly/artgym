"""One bounded thumb+middle+ring acquisition alternative, full convex preflight.
Existing five-finger failure loses index early; middle/ring straddle thumb's
long-axis location. No simulated success claim or force assumption.
"""
import json,argparse
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.audit_g2_side_pickup_candidate import radius
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'runs/g2-functional-v2-20260928'
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=base/'geometry-three-finger-v1');parser.add_argument('--shift-z',type=float,default=0.);a=parser.parse_args()
 out=a.output;out.mkdir(exist_ok=False);src=ROOT/'configs/g2_functional_v2/side-pickup-yaw45-compression6.json';p=json.loads(src.read_text());g=DigitGeometry(knife_spec=ROOT/p['knife_spec']);obj=np.array(json.loads((base/'geometry-short-lift-placement/planned-table-pose.json').read_text()));w=np.array(p['wrist_in_knife']);w[2,3]+=a.shift_z;p['wrist_in_knife']=w.tolist()
 for key in ['contact_targets','contact_points']:
  if key in p:
   v=np.array(p[key]);v[:,2]+=a.shift_z;p[key]=v.tolist()
 p['long_axis_grasp_shift_m']=a.shift_z
 inactive=[0,1,2,3,8,9,10,11];opened=np.array(p['open_q']);touch=np.array(p['touch_q']);closed=np.array(p['close_q']);touch[inactive]=opened[inactive];closed[inactive]=opened[inactive]
 graph={}
 for parent,child,_,_,_ in g.w.joints:graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
 pairs=[]
 for i,n in enumerate(sorted(g.meshes)):
  near={n}|graph.get(n,set());near|=set().union(*(graph.get(v,set()) for v in list(near)))
  pairs.extend((n,m) for m in sorted(g.meshes)[i+1:] if m not in near)
 rows=[]
 for phase,a,b in [('open_touch',opened,touch),('touch_close',touch,closed)]:
  for u in np.linspace(0,1,21):
   q=a+(b-a)*u;frames={n:w@f for n,f in g.w.forward(q).items()};vs={n:np.concatenate([v for v,_ in m])@frames[n][:3,:3].T+frames[n][:3,3] for n,m in g.meshes.items()};bad=[];knife=[]
   for a1,b1 in pairs:
    rad=radius(vs[a1],vs[b1])
    if rad is None or rad>1e-5:bad.append(dict(pair=[a1,b1],radius_m=rad))
   if phase=='open_touch':
    for n,v in vs.items():
     for part in g.knife_geometry.collision_parts(p.get('planning_slider_m')):
      rad=radius(v,part['vertices'])
      if rad is None or rad>1e-5:knife.append(dict(hand=n,knife=part['link'],radius_m=rad))
   clearance=min(float((v@obj[2,:3]+obj[2,3]-.75).min()) for v in vs.values());rows.append(dict(phase=phase,u=float(u),table_clearance_m=clearance,self_intersections=bad,knife_intersections=knife))
 passed=all(not r['self_intersections'] and not r['knife_intersections'] and r['table_clearance_m']>=.0005 for r in rows)
 p.update(active_fingers=['thumb','middle','ring'],excluded_fingers=['index','pinky'],touch_q=touch.tolist(),close_q=closed.tolist(),close_waypoints=[dict(fraction=0.,q=opened.tolist()),dict(fraction=2/3,q=touch.tolist()),dict(fraction=1.,q=closed.tolist())],reason='Threefinger measured contacts all at negative long-axis positions and pivot on far table end. Declared longitudinal shift centers support about uniform handle mass; no claim geometric centering implies physical retention.')
 (out/'motor-plan.json').write_text(json.dumps(p,indent=2)+'\n');(out/'audit.json').write_text(json.dumps(dict(passed=passed,rows=rows,reused='Exact same alreadychecked open pose and G2 approach/lift path yaw45. Only active three fingers touch/close.'),indent=2)+'\n');print(json.dumps(dict(passed=passed,bad=[r for r in rows if r['self_intersections'] or r['knife_intersections'] or r['table_clearance_m']<.0005])))
if __name__=='__main__':main()
