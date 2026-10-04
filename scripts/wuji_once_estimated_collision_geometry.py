"""Build planning collision proxy solely from the declared once-estimate.

The immutable nominal slider shape is a prior. No runtime/validation physical
URDF, asset ID, object truth or force is read. A proxy is not physical evidence.
"""
import hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

def build(estimate,output):
 output=Path(output);output.mkdir(parents=True,exist_ok=False)
 source=Path('assets/objects/knife_wuji_real_size_20261002/000');tree=ET.parse(source/'mobility.urdf');size=np.asarray(estimate['handle_size_WTL_m']);slider=np.asarray(estimate['slider_size_WTL_m']);delta=np.asarray(estimate['slider_contact_shift_m']);origin=np.array([0,.0075,.010624586881962734])+delta;origin[1]+=(size[1]-.012)/2
 shutil.copy2(source/'slider-shoulder.obj',output/'slider-shoulder.obj')
 for box in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):box.set('size',' '.join(map(str,size)))
 for mesh in tree.findall("./link[@name='link_1']/visual/geometry/mesh")+tree.findall("./link[@name='link_1']/collision/geometry/mesh"):mesh.set('scale',' '.join(map(str,slider/np.array([.010,.003,.030]))))
 tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)));tree.write(output/'mobility.urdf',encoding='utf-8',xml_declaration=True)
 spec=dict(asset_urdf=str(output/'mobility.urdf'),file_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()},planning=dict(side_half_width_m=float(size[0]/2),side_contact_y_interval_m=[float(-size[1]/3),float(size[1]/3)]),once_estimate=estimate,scope=__doc__,physical_evidence=False)
 path=output/'spec.json';path.write_text(json.dumps(spec,indent=2));return path


def rematch_open_preform(plan,spec):
 """Try three bounded thumb openings on the once-estimated geometry only.

 No close/reference change, asset identity or force feedback. The entire
 approach and closure still require separate original-mesh certification.
 """
 from scripts.g2_contact_geometry import DigitGeometry
 g=DigitGeometry(knife_spec=spec);w=np.asarray(plan['wrist_in_knife']);start=np.asarray(plan['open_q']);rows=[]
 for extra in [0.,.15,.30]:
  q=start.copy();q[16]-=extra;gap=g.minimum_gap(q,w,g.knife_geometry.lower,'thumb');margin=float(np.minimum(q-g.w.lower,g.w.upper-q).min());pairs=g.self_gaps(q,'thumb')+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);selfgap=min(r['gap_lower_bound_m'] for r in pairs);accepted=gap>=.001 and margin>=.005 and selfgap>=.000015
  rows.append(dict(extra_thumb_open_rad=extra,once_estimated_knife_gap_m=float(gap),original_limit_margin_rad=margin,original_self_gap_m=float(selfgap),accepted=bool(accepted)))
  if accepted:
   plan['open_q']=q.tolist();plan['close_waypoints'][0]['q']=q.tolist();plan['once_estimated_open_preform']=dict(selected_extra_thumb_open_rad=extra,screen=rows,scope='Common bounded estimate-only preform rule; no reference/close targets changed. Full approach/closure certificate pending');return plan
 raise ValueError('No bounded estimated thumb-open preform accepted: '+str(rows))
