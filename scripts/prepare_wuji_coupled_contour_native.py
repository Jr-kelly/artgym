"""Retimed and densely checked coupled contour before native physics.

Geometry, issued-motor feasibility and endpoint path reachability only.
No actual bearing, B capability or fresh-task acceptance.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.check_wuji_action_quality import HandIntersection
from scripts.wuji_measured_hold_reference import measured_hold_path
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--functional-end-row',type=int);p.add_argument('--contact-limited-pd-reference',action='store_true');p.add_argument('--partial-preview',action='store_true');p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=json.load(open(a.geometry));original_pass=bool(z['geometry_pass']);assert original_pass or a.partial_preview or a.functional_end_row is not None
 if a.functional_end_row is not None:
  z['rows']=z['rows'][:a.functional_end_row+1];assert not any(r['self'] for r in z['rows']);assert len(z['rows'])>=2
 complete=original_pass or a.functional_end_row is not None;source=z['source'];s=np.load(Path(source)/'takeover.npz');q0=s['robot_q'].astype(float);issued=s['issued_target'].astype(float);preload=issued[7:]-q0[7:];anchor=issued[7:]-np.array(z['rows'][0]['hand_q']);O=transform(s['object_state'][:3],s['object_state'][3:7]);k=G2Kinematics();g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');H=HandIntersection();n0=np.array(z['rows'][0]['normal_outward_knife']);rows=[];checks=[];reference=[]
 record('coupled_contour_dense_native_preparation_started',[str(a.geometry),str(a.output)],{'scope':__doc__,'uncertainty':'Are branch transitions collisionclear and wholethumb continuously near body, with real acquired motor headroom and full30mm reference?','decision':'Fullclear -> native physicaltransfer/fullB; collision/gap -> rejectcourse and refine transition, no state insertion'},next_step='Dense wholehand/knife transition then native fullB immediately ifclear')
 def add(arm,hand,normal,phase):
  normal=normal/np.linalg.norm(normal);X=np.linalg.inv(O)@k.forward(arm);bad=H.inspect(hand);by={f:min(x['gap_lower_bound_m'] for x in g.gaps(hand,X,float(s['slider_q']),f,certify_clearance_m=.0001)) for f in ['thumb','index','middle','ring','pinky']};u=np.clip((normal[1]-n0[1])/(1-n0[1]),0,1);u=u**3*(10-15*u+6*u*u);motor=hand+anchor;motor[16:]-=preload[16:]*u;motor_margin=float(np.minimum(motor-g.w.lower,g.w.upper-motor).min());time=len(rows)/30;row={'time_s':time,'arm_q':arm.tolist(),'hand_q':hand.tolist(),'wrist_in_knife':X.tolist(),'normal_outward_knife':normal.tolist(),'phase':phase};rows.append(row);checks.append({'time_s':time,'self':bad,'knife_gap_m_by_digit':by,'motor_margin_rad':motor_margin});reference.append(np.r_[arm+(issued[:7]-q0[:7]),motor])
 raw=z['rows'];add(np.array(raw[0]['arm_q']),np.array(raw[0]['hand_q']),np.array(raw[0]['normal_outward_knife']),raw[0]['phase'])
 for before,after in zip(raw,raw[1:]):
  aa=np.array(before['arm_q']);bb=np.array(after['arm_q']);ha=np.array(before['hand_q']);hb=np.array(after['hand_q']);na=np.array(before['normal_outward_knife']);nb=np.array(after['normal_outward_knife']);extra=np.zeros(20);extra[16:]=abs(preload[16:])*1.875*abs(nb[1]-na[1])/(1-n0[1]);ticks=max(1,int(np.ceil(max(abs(bb-aa).max()/.004,((abs(hb-ha)+extra)/.020).max()))))
  for j in range(1,ticks+1):
   f=j/ticks;add(aa*(1-f)+bb*f,ha*(1-f)+hb*f,na*(1-f)+nb*f,after['phase'])
 final=rows[-1];X=np.array(final['wrist_in_knife']);path_error=None;path_problem=None
 try:
  if not complete:raise ValueError('Incompleteprefix preview: endpoint B reference deliberately skipped')
  _,audit=measured_hold_path(final['hand_q'],X[:3,:3].T@np.array([0,1.,0]),X[:3,:3].T@np.array([0,0,1.]),np.linspace(0,.03,31));path_error=max(r['FK_position_error_m'] for r in audit['rows'])
 except ValueError as e:path_problem=str(e)
 summary={'planned_path_complete':complete,'source_entire_geometry_pass':original_pass,'selected_functional_end_row':a.functional_end_row,'scope':__doc__,'frames':len(rows),'duration_s':rows[-1]['time_s'],'self_frames':sum(bool(r['self']) for r in checks),'minimum_knife_gap_m':min(min(r['knife_gap_m_by_digit'].values()) for r in checks),'maximum_thumb_gap_m':max(r['knife_gap_m_by_digit']['thumb'] for r in checks),'minimum_uncorrected_motor_margin_rad':min(r['motor_margin_rad'] for r in checks),'hand_motor_slew_max_rad':float(abs(np.diff(np.array(reference)[:,7:],axis=0)).max()),'arm_motor_slew_max_rad':float(abs(np.diff(np.array(reference)[:,:7],axis=0)).max()),'endpoint_full30mm_FK_error_m':path_error,'endpoint_full30mm_problem':path_problem};summary['eligible_for_native']=complete and summary['self_frames']==0 and summary['minimum_knife_gap_m']>=-.0007 and summary['maximum_thumb_gap_m']<.001 and summary['minimum_uncorrected_motor_margin_rad']>=-.0001 and path_problem is None
 (a.output/'dense-geometry.json').write_text(json.dumps({'summary':summary,'rows':checks},indent=2));(a.output/'reference.json').write_text(json.dumps({'rows':rows,'scope':__doc__},indent=2))
 summary['contact_limited_pd_diagnostic']=bool(a.contact_limited_pd_reference and complete and summary['self_frames']==0 and summary['maximum_thumb_gap_m']<.001 and summary['minimum_uncorrected_motor_margin_rad']>=-.001 and path_problem is None and summary['hand_motor_slew_max_rad']<=.025 and summary['arm_motor_slew_max_rad']<=.006)
 if summary['eligible_for_native'] or summary['contact_limited_pd_diagnostic']:
  duration=rows[-1]['time_s'];motor={'required_actual_source':source,'development_abort_on_translation_m':.08,'rows':[{'time_s':0.,'arm_q':issued[:7].tolist(),'hand_q':issued[7:].tolist()}],'contact_contour_course':{'reference':str(a.output/'reference.json'),'start_s':0.,'end_s':duration,'side_to_front_seconds':duration,'retain_acquired_pressure':True,'preload_release_basis':'normal-turn','whole_wrist_pose_feedback':True,'knife_pose_coordinates':'live-sim-oracle'},'retained_push_skill':{'start_s':duration,'preparation_seconds':4.,'knife_spec':'assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json','entry_reference_adaptation':'measured-hold','entry_pressure_coordinates':'cartesian-normal','task_stroke_m':.03},'geometric_reference_assessment':summary,'scope':'Contact-limited finite PD native diagnostic: referenceoverlap is disclosed, referenceq is not actualpose. Actual q/contacts/quality/B must be measured. Actualsegment ifnativeexecutes; live sim_oracle wholewristfeedback and knowngeometry fingercourse; no actualstatewrites. Bcomplete actor/history/reference/pressure/nonthumb retained. Source missingcontactcache/estimatedrobotvelocity, notfresh fulltask.'};(a.output/'motor.json').write_text(json.dumps(motor,indent=2))
 print(json.dumps(summary),flush=True);record('coupled_contour_dense_native_preparation_terminal',[str(a.output/'dense-geometry.json'),str(a.output/'reference.json')],summary,next_step='Native coupledtransfer+fullB now ifeligible; rejection -> exact transition geometry repair, no knownbadnative launch')
if __name__=='__main__':main()
