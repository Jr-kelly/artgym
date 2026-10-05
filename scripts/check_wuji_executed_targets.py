"""Check saved actual targets including path/pressure/residual output corrections."""
import argparse,json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();z=np.load(a.trial/'trace.npz');phy=json.loads((a.trial/'physics.json').read_text());g=DigitGeometry(max_face_axes=10000,knife_spec=a.knife_spec);rows=[]
for i in np.flatnonzero(z['time']>=16)[::3]:
 q=z['applied_target'][i,phy['hand_indices']];gaps=g.self_gaps(q,'thumb')+g.pair_gaps(q,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]);gap=min(r['gap_lower_bound_m'] for r in gaps);margin=float(np.minimum(q-g.w.lower,g.w.upper-q).min());rows.append(dict(time_s=float(z['time'][i]),target_original_limit_margin_rad=margin,thumb_self_gap_m=gap,thumb_self_clearance_pass=bool(gap>=.000015-1e-7),original_position_limits_pass=bool(margin>=-1e-7)))
a.output.write_text(json.dumps(dict(scope=__doc__,all_clearance_pass=all(r['thumb_self_clearance_pass'] for r in rows),all_position_limits_pass=all(r['original_position_limits_pass'] for r in rows),rows=rows,scope_limit='Saved issued positions only; preload contact and actual joint dynamics differ. Does not replace full continuous behavior or true hardware limit reads.'),indent=2))
print(json.dumps(dict(min_gap_m=min(r['thumb_self_gap_m'] for r in rows),min_margin_rad=min(r['target_original_limit_margin_rad'] for r in rows))))
