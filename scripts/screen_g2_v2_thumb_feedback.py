"""Offline41-knot reach and exact non-target collision audit; no dynamics."""
import json
from pathlib import Path
import numpy as np
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_kinematics import transform
from scripts.g2_v2_thumb_feedback import ThumbFeedback
from scripts.g2_contact_geometry import DigitGeometry
from scripts.audit_g2_side_pickup_candidate import radius
ROOT=Path(__file__).resolve().parents[1]
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,default=ROOT/'configs/g2_functional_v2/thumb-feedback-v1.json');p.add_argument('--output',type=Path,default=ROOT/'runs/g2-functional-v2-20260928/thumb-feedback-v1-geometry.json');args=p.parse_args();assert not args.output.exists()
 run=ROOT/'runs/g2-functional-v2-20260928';src=run/'V2-03-A-level-thumb-release';d=np.load(src/'trace.npz');q=d['q'][-1].astype(float);tar=d['reference_targets'][-1,7:27];w=transform(d['wrist'][-1,:3],d['wrist'][-1,3:]);o=transform(d['object'][-1,:3],d['object'][-1,3:]);g=KnifeGeometry(ROOT/'assets/objects/knife_wuji_measured_box_20260928_v2/000/asset-spec.json');c=json.loads(args.config.read_text());f=ThumbFeedback(c,g,q,tar,w,o,d['slider'][-1]);geom=DigitGeometry(knife_spec=ROOT/'assets/objects/knife_wuji_measured_box_20260928_v2/000/asset-spec.json');rows=[]
 for dist in np.linspace(0,.04,41):
  qt,e=f.solve(q,w,o,float(dist));full=q.copy();full[16:]=qt;f.previous[16:]=qt
  row=dict(distance_m=float(dist),error_m=e,q_thumb=qt.tolist())
  if round(dist*1000)%5==0:
   frames=geom.w.forward(full);t=np.linalg.inv(o)@w;inter=[]
   for name,meshes in geom.meshes.items():
    if '_thumb_' not in name:continue
    v=np.concatenate([v for v,_ in meshes]);tf=t@frames[name];vv=v@tf[:3,:3].T+tf[:3,3]
    for part in g.collision_parts(g.lower+dist):
     rad=radius(vv,part['vertices'])
     if rad is None or rad>1e-5:inter.append(dict(hand=name,knife=part['link'],radius_m=rad,intended=part['link']=='link_1' and name==c['contact_link']))
   for r in geom.self_gaps(full,'thumb'):
    if r['gap_lower_bound_m']>=0:continue
    aa,bb=r['moving_link'],r['other_link'];a=np.concatenate([v for v,_ in geom.meshes[aa]])@frames[aa][:3,:3].T+frames[aa][:3,3];b=np.concatenate([v for v,_ in geom.meshes[bb]])@frames[bb][:3,:3].T+frames[bb][:3,3];rad=radius(a,b)
    if rad is None or rad>1e-5:inter.append(dict(hand=aa,other=bb,radius_m=rad,intended=False))
   row['intersections']=inter
  rows.append(row)
 result=dict(scope='Geometric41-point reach, collision every5mm; planned button compression is motor displacement, not measured force',rows=rows,max_error_m=max(x['error_m'] for x in rows),unintended=[r for row in rows for r in row.get('intersections',[]) if not r['intended']]);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(max_error_m=result['max_error_m'],unintended=result['unintended'])))
if __name__=='__main__':main()
