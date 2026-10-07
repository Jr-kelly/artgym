"""Capture this development source's genuine native thumb/slider material.

Normal contributions do not contain tangential or total axial force.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.wuji_direct_contact_prior import source_contacts
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.record_wuji_flat_table_event import record

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--stroke-m',type=float,default=.026)
    a=p.parse_args();trial,rows,end=source_contacts(a.source)
    cs=[c for r in rows if r['time_s']>end-.2 for c in r['contacts'] if c['hand_link']=='hand_r_thumb_pad_link' and c['knife_link']=='link_1']
    if not cs:raise ValueError('Actual source lacks genuine pad-slider contact')
    s=np.load(a.source/'takeover.npz');report=json.loads((trial/'report.json').read_text())
    g=DigitGeometry(max_face_axes=10,knife_spec=Path(report['physical_asset']).parent/'spec.json')
    L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@G2Kinematics().forward(s['robot_q'][:7])
    T=L@g.w.forward(s['robot_q'][7:])['hand_r_thumb_pad_link']
    N=np.mean([c['force_normal_contribution_knife_N'] for c in cs],axis=0);N/=np.linalg.norm(N)
    cfg=dict(material_point=np.mean([c['position_hand_link_m'] for c in cs],axis=0).tolist(),local_normal=(T[:3,:3].T@N).tolist(),stroke_m=a.stroke_m,source=str(a.source),native_records=len(cs),scope=__doc__)
    if a.output.exists():raise FileExistsError(a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(cfg,indent=2))
    record('direct_actual_pad_material_captured',[str(a.output)],config=cfg,next_step='Use actual material for motor-only stroke; native displacement/support decides acceptance')
    print(json.dumps(cfg))

if __name__=='__main__':main()
