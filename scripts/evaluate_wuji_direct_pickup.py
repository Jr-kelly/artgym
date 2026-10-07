"""Task-specific actual direct pickup and optional air slider checks."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scripts.g2_kinematics import transform
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--trial',type=Path,required=True);p.add_argument('--prefix-duration',type=float,required=True);p.add_argument('--hold-start',type=float,default=8);p.add_argument('--hold-end',type=float,default=10);p.add_argument('--push-start',type=float);a=p.parse_args();z=np.load(a.trial/'trace.npz');t=z['time']+a.prefix_duration;report=json.loads((a.trial/'report.json').read_text());G=KnifeGeometry(Path(report['physical_asset']).parent/'spec.json');clear=[]
for i in range(len(t)):
 O=transform(z['object'][i,:3],z['object'][i,3:7]);V=np.concatenate([v['vertices'] for v in G.collision_parts(float(z['slider'][i]))]);clear.append(float((V@O[:3,:3].T+O[:3,3])[:,2].min()-.75))
clear=np.array(clear);h=(t>=a.hold_start-1e-6)&(t<=a.hold_end+1e-6);native=[json.loads(l) for l in (a.trial/'knife-contact-pairs.jsonl').open()];table=sum('table' in [r['body0'],r['body1']] for r in native if a.hold_start<=r['time_s']+a.prefix_duration<=a.hold_end);supported=bool((z['finger_body_contacts'][h].sum(1)>0).all());held=bool(h.any() and clear[h].min()>.02 and table==0 and supported)
result={'direct_whole_pickup':held,'hold_elapsed_s':[a.hold_start,a.hold_end],'hold_min_whole_clearance_m':float(clear[h].min()),'hold_table_contact_records':table,'hold_hand_contact_every_saved_frame':supported,'max_whole_clearance_m':float(clear.max()),'max_object_z_m':float(z['object'][:,2].max()),'source_trace_sha256':hashlib.sha256((a.trial/'trace.npz').read_bytes()).hexdigest(),'direct_flip_to_push_complete':False,'simulation_only':True,'real_robot_ran':False,'scope':'Newdirectroute; wholeactualcollisionbounds andnativecontacts. Recordedinitializer ifpresent meansdevelopmentonly. No old98s outcome inherited.'}
(a.trial/'direct-evaluation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));record('direct_actual_stage_evaluation',[str(a.trial/'direct-evaluation.json')],config=result,next_step='Ifactualpickup true addnonthumbsupport/roll usingactualnewstate, elsefirstnativefailurechangescandidate; no unchangedrerun')
