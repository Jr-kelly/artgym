"""Project only floor-crossing rear-ring waypoints; retain the actual grip."""
import argparse,json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--prior',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();source=a.source;prior=a.prior;v=json.loads(prior.read_text());s=np.load(source/'takeover.npz');out=a.output;out.mkdir(parents=True,exist_ok=False);g=DigitGeometry(knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));audit=HandIntersection();q=s['robot_q'][7:].astype(float);W=G2Kinematics().forward(s['robot_q'][:7]);L=np.linalg.inv(transform(s['object_state'][:3],s['object_state'][3:7]))@W;pairs=[p for p in audit.pairs if any('_ring_' in n for n in p)];rows=[];diag=[]
if Path(v['source']).resolve()!=source.resolve():raise ValueError('Floor arc consumes a different actual grasp than its prior path')
config=dict(candidate='D691',grasp_end=str(source),support_layout='ForwardI/M+Thumb with rearRing, stagedPinkyfirst',control='CorrectRingapproach floorcrossing bylocaljointprojection, originalnativephysics retained',uncertainty='690 removedallselfcollision butRingpad crossesfloor .922mm in middle; can samecontactendpoint be reached alonga floorclear jointarc?',decision='Wholepathclear -> native4s acquisition now; no nativeforknownfloorcollision')
e=record('rear_floor_arc_started',[str(out),str(prior)],config=config,next_step=config['decision']);Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(config)+'\n')
def table(h,F):
 values=[]
 for name,parts in g.meshes.items():
  if '_ring_' not in name:continue
  T=W@F[name];values.extend(float((V@T[:3,:3].T+T[:3,3])[:,2].min()-.75) for V,_ in parts)
 return values
for number,previous in enumerate(v['path_diagnostics']):
 h=np.asarray(previous['planned_q']);base=h.copy();F=g.w.forward(h);clear=table(h,F)
 if min(clear)<.0001:
  def residual(x):
   h=base.copy();h[12:16]=x;F=g.w.forward(h);r=list((x-base[12:16])*.05);r.extend(min(0.,gap-.0001)*1000 for gap in table(h,F));r.extend(min(0.,x['gap_lower_bound_m']-.0001)*800 for x in g.pair_gaps(h,pairs,certify_clearance_m=.0001))
   for gap in g.gaps(h,L,float(s['slider_q']),'ring',frames=F):
    allow=gap['hand_link'] in ['hand_r_ring_link4','hand_r_ring_pad_link'] and gap['knife_link']=='link_0';r.append(min(0.,gap['gap_lower_bound_m']-(-.0013 if allow else .0001))*650)
   return np.asarray(r)
  fit=least_squares(residual,base[12:16],bounds=(g.w.lower[12:16]+.035,g.w.upper[12:16]-.035),max_nfev=25,diff_step=1e-5);h[12:16]=fit.x;F=g.w.forward(h);clear=table(h,F)
 cmd=np.asarray(v['rows'][number]['hand_q']);cmd[12:16]+=h[12:16]-base[12:16];rows.append(dict(time_s=previous['time_s'],arm_q=v['rows'][number]['arm_q'],hand_q=cmd.tolist()));diag.append(dict(time_s=previous['time_s'],minimum_ring_table_clearance_m=min(clear),self_intersections=audit.inspect(h),planned_q=h.tolist(),joint_correction_rad=(h[12:16]-base[12:16]).tolist()))
 (out/'planning-checkpoints.json').write_text(json.dumps(dict(rows=rows,path_diagnostics=diag),indent=2))
 if number%20==0:print(json.dumps(dict(frame=number,minfloor=min(clear),self=len(diag[-1]['self_intersections']))),flush=True)
result=dict(path_frames=len(rows),self_frames=sum(bool(r['self_intersections']) for r in diag),minimum_ring_table_clearance_m=min(r['minimum_ring_table_clearance_m'] for r in diag),maximum_floor_correction_rad=max(float(np.max(np.abs(np.asarray(r['joint_correction_rad'])))) for r in diag),terminal_ring_gap_m=g.minimum_gap(h,L,float(s['slider_q']),'ring'),scope='Planningonly; nativecontactnotyetverified')
(out/'motor.json').write_text(json.dumps(dict(rows=rows,source=str(source),configuration=config,geometry_result=result,path_diagnostics=diag),indent=2));e=record('rear_floor_arc_finished',[str(out/'motor.json')],config=result,next_step=config['decision']);Path('research/flat-table-20261006/CONTINUATION.md').open('a').write('\n'+e['utc']+' '+json.dumps(result)+'\n');print(json.dumps(result),flush=True)
