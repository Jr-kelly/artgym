"""One evidence-backed initial candidate; no dynamics or new success claim."""
import json
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import WujiKinematics
from scripts.g2_knife_geometry import KnifeGeometry
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'configs/g2_functional_v2';r=json.loads((ROOT/'configs/g2_finger_surface/operation-target-v1.json').read_text());g=KnifeGeometry(ROOT/'assets/objects/knife_wuji_measured_box_20260928_v2/000/asset-spec.json');w=WujiKinematics()
 s=np.zeros(70);s[:20]=r['measured_hand_q_rad'];s[20:40]=r['actual_hand_motor_targets_rad'];s[40:47]=r['object_in_hand_xyzw'];s[54]=g.lower
 obj=transform(s[40:43],s[43:47]);slider=obj@transform(g.joint_xyz+g.axis*g.lower,Rotation.from_matrix(g.joint_r).as_quat());s[47:50]=slider[:3,3];s[50:54]=Rotation.from_matrix(slider[:3,:3]).as_quat();frames=w.forward(s[:20]);s[55:70]=np.concatenate([frames[n][:3,3] for n in w.config['track_links']])
 (d/'A00-reference.json').write_text(json.dumps(dict(state=s.tolist(),scope='Preset only before first step; candidate from actual old operation evidence, NEW geometry operation UNPROVEN',source_reference='configs/g2_finger_surface/operation-target-v1.json',knife_spec=str(g.urdf.parent.relative_to(ROOT)/'asset-spec.json')),indent=2)+'\n')
 (d/'operation-pose.json').write_text(json.dumps(transform(r['source_world_wrist_xyzw'][:3],r['source_world_wrist_xyzw'][3:]).tolist(),indent=2)+'\n')
 old=json.loads((Path(r['source_run'])/'plan.json').read_text());(d/'operation-seed.json').write_text(json.dumps(old['operation_q'])+'\n')
 print(json.loads((Path(r['source_run'])/'report.json').read_text())['args'])
if __name__=='__main__':main()
