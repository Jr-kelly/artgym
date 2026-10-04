import json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
B=Path('runs/antirotation-grasp-20261004');P=B/'initial-geometry-v4/thin-projected04-complete';j=json.loads((P/'motor-plan.json').read_text());g=DigitGeometry();a=json.loads((B/'pickup-plans-v1/opposed/lateral-acquisition/acquisition-path.json').read_text());w=G2Kinematics().forward(np.asarray(a['approach_q'][-1]));nom=np.asarray(json.loads((B/'pickup-plans-v1/opposed/localization.json').read_text())['object_world_matrix'])@np.asarray(j['wrist_in_knife']);rows=[]
for key in ['open_q','touch_q','close_q']:
 frames=g.w.forward(np.asarray(j[key]));links=[]
 for name,meshes in g.meshes.items():
  mat=w@frames[name]
  for v,n in meshes:
   v=v@mat[:3,:3].T+mat[:3,3];axes=np.r_[np.eye(3),n@mat[:3,:3].T];p=(v-[.60,-.25,.725])@axes.T;r=abs(axes)@np.array([.30,.40,.025]);links.append(dict(link=name,gap=float(np.maximum(p.min(0)-r,-r-p.max(0)).max())))
 rows.append(dict(target=key,nearest=sorted(links,key=lambda x:x['gap'])[:5]))
out=dict(actual_command_wrist_minus_nominal_wrist_m=(w[:3,3]-nom[:3,3]).tolist(),rows=rows);(P/'actual-command-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
