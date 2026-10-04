"""Original full hull/table SAT diagnosis for estimated thin pickup targets."""
import json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
B=Path('runs/antirotation-grasp-20261004');j=json.loads((B/'initial-geometry-v2/projected-04/closure-plan.json').read_text());g=DigitGeometry();w=np.asarray(json.loads((B/'pickup-plans-v1/opposed/localization.json').read_text())['object_world_matrix'])@np.asarray(j['wrist_in_knife']);rows=[]
for u in [0,.75,1]:
 q=np.asarray(j['touch_q'])*(1-u)+np.asarray(j['close_q'])*u;frames=g.w.forward(q);links=[]
 for name,meshes in g.meshes.items():
  mat=w@frames[name]
  for v,n in meshes:
   v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];pv=(v-[.60,-.25,.725])@axes.T;r=abs(axes)@np.array([.30,.40,.025]);links.append(dict(link=name,gap=float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max())))
 rows.append(dict(fraction=u,nearest=sorted(links,key=lambda r:r['gap'])[:7]))
p=B/'initial-geometry-v2/projected-04/table-conflict-diagnosis.json';p.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
