"""Single-digit unload/return plan, with full convex preflight at 31 samples."""
import json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.audit_g2_side_pickup_candidate import radius
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'configs/g2_functional_v2';r=json.loads((d/'A00-reference.json').read_text());s=np.array(r['state']);g=DigitGeometry(knife_spec=ROOT/r['knife_spec']);obj=transform(s[40:43],s[43:47]);q=s[20:40].copy();point=g.w.contacts(q)[0][0]
 dest,err=g.w.solve_finger('thumb',point+obj[:3,1]*.008,q)
 audit=[]
 for u in np.linspace(0,1,31):
  qi=q+(dest-q)*u;frames=g.w.forward(qi);intersections=[]
  for n,meshes in g.meshes.items():
   if '_thumb_' not in n:continue
   t=np.linalg.inv(obj)@frames[n]
   for v,_ in meshes:
    local=v@t[:3,:3].T+t[:3,3]
    for part in g.knife_geometry.collision_parts(s[54]):
     rad=radius(local,part['vertices'])
     if rad is None or rad>1e-5:intersections.append([n,part['link'],rad])
  for row in g.self_gaps(qi,'thumb'):
   if row['gap_lower_bound_m']>=0:continue
   aa,bb=row['moving_link'],row['other_link'];a=np.concatenate([v for v,_ in g.meshes[aa]])@frames[aa][:3,:3].T+frames[aa][:3,3];b=np.concatenate([v for v,_ in g.meshes[bb]])@frames[bb][:3,:3].T+frames[bb][:3,3];rad=radius(a,b)
   if rad is None or rad>1e-5:intersections.append([aa,bb,rad])
  audit.append(dict(fraction=float(u),intersections=intersections,thumb_gap_m=g.minimum_gap(qi,np.linalg.inv(obj),s[54])))
 plan=dict(scope='Preset-only thumb unloading motor path; nonthumb references held exactly; not acquisition',ik_residual_m=err,displacement_m=.008,stages=[dict(name='reference_hold',seconds=1,hold=True),dict(name='thumb_unload',seconds=1,indices=[16,17,18,19],target=dest[16:].tolist()),dict(name='thumb_clear_hold',seconds=1,hold=True,require_clear=True),dict(name='thumb_return',seconds=1,indices=[16,17,18,19],target=q[16:].tolist())],audit=audit,limits_ok=bool((dest>=g.w.lower).all() and (dest<=g.w.upper).all()),numerical_intersection_radius_threshold_m=1e-5)
 (d/'thumb-release-v1.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(dict(ik=err,q=dest[16:].tolist(),gap=audit[-1]['thumb_gap_m'],overlap_samples=sum(bool(a['intersections']) for a in audit))))
if __name__=='__main__':main()
