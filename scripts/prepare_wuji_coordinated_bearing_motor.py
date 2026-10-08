"""Actual-issued preload preservation along a coordinated new-bearing path.

Joint deflection is retained as a motor reference, never interpreted as constant
contact force. The three existing bearing fingers are not withdrawn. The new
ring contact clears the side before a modest back-face preload is commanded.
Original finite PD, effort, friction and geometry determine actual load.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--world-stabilized-feedback',action='store_true');p.add_argument('--whole-wrist-feedback',action='store_true');p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 geo=json.loads(a.geometry.read_text());assert geo['geometry_pass'];src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();initial=z['issued_target'].astype(float);actual=z['robot_q'].astype(float);offset=initial-actual;kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);digit=geo.get('new_bearing_digit','ring');base={'ring':12,'pinky':8}[digit];ids=np.arange(base,base+4);ring='hand_r_'+digit+'_pad_link';clock=0.;prev=initial.copy();rows=[dict(time_s=clock,arm_q=prev[:7].tolist(),hand_q=prev[7:].tolist())];checks=[]
 # One second retains the actual issued command; no automatic force inference.
 clock=1.;rows.append(dict(rows[-1],time_s=clock))
 for r in geo['rows']:
  foot=r.get('bearing_foot_knife_m',r.get('ring_foot_knife_m'));bounds=r.get('bearing_pad_bounds_knife_m',r.get('ring_pad_bounds_knife_m'));L=np.array(r['wrist_in_knife']);h=np.array(r['hand_q']);q=np.r_[r['arm_q'],h]+offset
  # Retire only the ring's old side preload, keeping the three primary fingers.
  clear=0. if geo.get('new_bearing_initially_clear') else min(1.,r['index']/(4. if r['phase']in ('withdraw-whole-pad','clear-whole-back-corner','acquire-back-face') else 8.));q[7+ids]-=offset[7+ids]*clear
  bearing=0.
  if r['phase']in ('enter-back-face','acquire-back-face') and foot[0]<.0092 and (r['phase']=='acquire-back-face' or bounds is None or bounds[1][1]>-.006):
   bearing=.15*min(1.,(r['index']-(geo.get('bearing_acquisition_start_index',12.) if r['phase']=='acquire-back-face' else 8.))/(4. if r['phase']=='acquire-back-face' else 8.))
   T=L@f.g.w.forward(h)[ring];m=T[:3,:3].T@(np.array(foot)-T[:3,3]);J=np.empty((3,4))
   for j,c in enumerate(ids):
    up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@f.g.w.forward(up)[ring];B=L@f.g.w.forward(down)[ring];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
   q[7+ids]+=(J.T@np.array([0.,bearing,0.]))/kp[ids]
  margin=float(np.minimum(q-np.r_[f.kin.lower,f.g.w.lower],np.r_[f.kin.upper,f.g.w.upper]-q).min());assert margin>0,(r['index'],margin)
  frames=max(1,int(np.ceil(max(abs(q[:7]-prev[:7]).max()/.004,abs(q[7:]-prev[7:]).max()/.012))));clock+=frames/30.;rows.append(dict(time_s=clock,arm_q=q[:7].tolist(),hand_q=q[7:].tolist()));rows[-1].update(wrist_in_knife=r['wrist_in_knife'],normal_outward_knife=[-1.,0.,0.]);checks.append(dict(index=r['index'],ring_back_preload_reference_N=bearing,minimum_motor_margin_rad=margin));prev=q
 rows[0].update(wrist_in_knife=geo['rows'][0]['wrist_in_knife'],normal_outward_knife=[-1.,0.,0.]);rows[1].update(wrist_in_knife=geo['rows'][0]['wrist_in_knife'],normal_outward_knife=[-1.,0.,0.]);rows.append(dict(rows[-1],time_s=clock+1.5));out=dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.04,scope=__doc__);
 if a.whole_wrist_feedback or a.world_stabilized_feedback:
  reference=a.output/'whole-wrist-reference.json';reference.write_text(json.dumps(dict(rows=rows),indent=2));out['contact_contour_course']=dict(reference=str(reference),start_s=0.,end_s=clock+1.6,side_to_front_seconds=1.,whole_wrist_pose_feedback=True,preparation_pressure_feedback=False,preload_release_basis='normal-turn',knife_pose_coordinates='live-sim-oracle');
  if a.world_stabilized_feedback:out['contact_contour_course'].update(object_pose_feedback_components='world-stabilized',pose_error_phase_governor=True,end_s=1e9)
  out['scope']+=' Existing whole-arm live object pose feedback; simulation oracle only, no individual finger tracker.'
 (a.output/'motor.json').write_text(json.dumps(out,indent=2));(a.output/'reference-audit.json').write_text(json.dumps(dict(initial_joint_deflection_rad=offset.tolist(),checks=checks,seconds=clock+1.5,scope=__doc__),indent=2))
 record('coordinated_back_bearing_motor_prepared_v897r1',[str(a.geometry),str(a.output/'motor.json'),str(a.output/'reference-audit.json')],dict(seconds=clock+1.5,old_primary_motor_offset='Captured actual issued-minus-position retained along coordinated changing pose',new_bearing_digit=digit,new_bearing_initially_clear=geo.get('new_bearing_initially_clear',False),ring_preload_reference_N=.15,original_ring_reference_v890_N=.2,force_scope='Motor reference only, actual contact force required; multiple actual Index contacts invalidate single-point deflection inference'),next_step='One native actual-state back acquisition; require positive-Y native ring normal and sustained carry/H before old primary withdrawal');print(json.dumps(dict(seconds=clock+1.5)))
if __name__=='__main__':main()
