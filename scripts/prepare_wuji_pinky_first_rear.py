"""Plan a rear ring approach after opening the idle pinky, from actual state."""
import argparse,json,numpy as np
from pathlib import Path
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_direct_pickup import smooth
from scripts.record_wuji_flat_table_event import record
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--endpoint',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=False);source=a.source;s=np.load(source/'takeover.npz');q=s['robot_q'][7:].astype(float);issued=s['issued_target'][7:].astype(float);endpoint=json.loads(a.endpoint.read_text())['diagnostics']['ring_q'];g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));audit=HandIntersection();W=G2Kinematics().forward(s['robot_q'][:7]);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@W
endpoint_metadata=json.loads(a.endpoint.read_text())
if Path(endpoint_metadata['source']).resolve()!=source.resolve():raise ValueError('Ring endpoint belongs to a different actual grasp')
cfg=dict(candidate='D690',grasp_end=str(source),layout='ForwardI/M+Thumb, acquireRearRing; freePinky yieldsoutwardfirst',control='Pinkyjoint2 -0.12rad before Ring approach; no forcegainchange',uncertainty='Fullfacegeometry givesPinkyjoint2 negative derivative opening2.2mm atRingroot; does stagedwholeapproach avoid linearRing/Pinky interference?',decision='Densepath clear andsubmmcontact -> native once; physicalfirstfailure controlsnext.')
e=record('pinky_first_rear_geometry_start',[str(out),str(source/'manifest.json')],config=cfg,next_step=cfg['decision']);Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(cfg)+'\n');rows=[];diagnostics=[]
for t in np.arange(0,3.9+1/60,1/30):
 h=q.copy();h[9]-=.12*smooth(t/.7);u=smooth((t-.75)/2.8);h[12:16]=(1-u)*q[12:16]+u*np.array(endpoint);F=g.w.forward(h);clear=[];gaps=[]
 for digit in ['ring','pinky']:
  for name,parts in g.meshes.items():
   if '_'+digit+'_' not in name:continue
   T=W@F[name];clear.extend(float((V@T[:3,:3].T+T[:3,3])[:,2].min()-.75) for V,_ in parts)
  gaps.extend(g.gaps(h,L,float(s['slider_q']),digit,frames=F))
 selfbad=audit.inspect(h);badgap=[x for x in gaps if x['gap_lower_bound_m']<-.00015 and not(x['knife_link']=='link_0' and x['hand_link'] in ['hand_r_ring_link4','hand_r_ring_pad_link'])];cmd=issued.copy();cmd[8:16]=h[8:16]+issued[8:16]-q[8:16];rows.append(dict(time_s=float(t),arm_q=s['issued_target'][:7].tolist(),hand_q=cmd.tolist()));diagnostics.append(dict(time_s=float(t),self_intersections=selfbad,minimum_changed_digit_table_clearance_m=min(clear),nonbearing_knife_gaps=badgap,planned_q=h.tolist()))
result=dict(path_frames=len(rows),self_frames=sum(bool(x['self_intersections']) for x in diagnostics),minimum_table_clearance_m=min(x['minimum_changed_digit_table_clearance_m'] for x in diagnostics),nonbearing_conflict_frames=sum(bool(x['nonbearing_knife_gaps']) for x in diagnostics),terminal_ring_gap_m=g.minimum_gap(h,L,float(s['slider_q']),'ring'),goal_complete=False)
v=dict(rows=rows,source=str(source),candidate=cfg,geometry_result=result,path_diagnostics=diagnostics,scope='Samecurrentactualgrasp; stagedfreePinkyclearance, no native success orphysicalstate reset');(out/'motor.json').write_text(json.dumps(v,indent=2));e=record('pinky_first_rear_geometry_end',[str(out/'motor.json')],config=result,next_step='Clearpath -> native shortacquisition; otherwise exactremainingtable/self/contactmechanism');Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(result)+'\n');print(json.dumps(result),flush=True)
