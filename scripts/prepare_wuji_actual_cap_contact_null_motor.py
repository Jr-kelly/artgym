"""Selected valid localcap null prefix, measured-normal torque transport only.

Actual Index bearing/wrist targets retained, previously idle Middle clears.
Only actual cap normal is measured; captured remaining motor torque includes
unidentified tangential/dynamic components. Nativecontact/H certify the action.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--selected-last',type=int,default=3);p.add_argument('--rolling-contact-limit-m',type=float,default=.00001);p.add_argument('--version',type=int,default=932);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.loads(a.geometry.read_text());assert len(geo['rows'])>=4;selected=geo['rows'] if a.selected_last<0 else geo['rows'][:a.selected_last+1];assert selected[-1]['workspace30']['reference_eligible']and selected[-1]['contact_error_m']<a.rolling_contact_limit_m and all(not r['self']for r in selected);src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 L=np.array(selected[0]['wrist_in_knife']);material=np.array(geo['material_point_link_m']);normal=np.array(geo['measured_contact_normal_only_knife_N']);name=geo['contact_link'];kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);moving=np.array(geo['moving_joint_indices']);depth={}
 for d in ['middle','thumb']:
  for c in g.gaps(h0,L,float(z['slider_q']),d):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.00001)
 def jac(h):
  J=np.empty((3,4))
  for i,j in enumerate(range(16,20)):
   up=h.copy();down=h.copy();up[j]+=1e-5;down[j]-=1e-5;A=L@g.w.forward(up)[name];B=L@g.w.forward(down)[name];J[:,i]=(A[:3,:3]@material+A[:3,3]-B[:3,:3]@material-B[:3,3])/2e-5
  return J
 residual_torque=kp[16:]*(issued[23:]-h0[16:])-jac(h0).T@normal;samples=[];failure=None;record('actual_safe_cap_null_motor_precheck_started_v%d'%a.version,[str(a.geometry)],dict(scope=__doc__,selected_last_index=selected[-1]['index'],rolling_contact_limit_m=a.rolling_contact_limit_m,original30_workspace_FK_m=selected[-1]['workspace30']['reference_FK_error_m'],contact_error_m=selected[-1]['contact_error_m']),next_step='Denseoriginal mesh/H on valid task-achieving prefix, originalbounds thenone native shortcontact-preserving adjustment andB30 capacity')
 for segment,(A,B)in enumerate(zip(selected[:-1],selected[1:])):
  A=np.array(A['hand_q']);B=np.array(B['hand_q']);n=max(2,int(math.ceil(abs(B-A).max()/.012))+1)
  for u in np.linspace(0,1,n):
   h=A*(1-u)+B*u;bad=f.H.inspect(h);violations=[c for d in ['middle','thumb']for c in g.gaps(h,L,float(z['slider_q']),d,certify_clearance_m=.0002)if c['gap_lower_bound_m']<depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]-.00001];samples.append(dict(segment=segment,fraction=float(u),self=bad,knife_violations=violations))
   if bad or violations:failure='Original dense contact/self constraint';break
  if failure:break
 rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in [0.,1.]];clock=1.;previous=issued[7:].copy()
 if failure is None:
  for r in selected:
   h=np.array(r['hand_q']);motor=issued[7:].copy();motor[moving]=h[moving]+issued[7:][moving]-h0[moving];motor[16:]=h[16:]+(jac(h).T@normal+residual_torque)/kp[16:]
   if np.minimum(motor-g.w.lower,g.w.upper-motor).min()<=0:failure='Originalmotorlimit';break
   clock+=max(1,int(math.ceil(abs(motor-previous).max()/.012)))/30.;rows.append(dict(time_s=clock,arm_q=issued[:7].tolist(),hand_q=motor.tolist()));previous=motor
 passed=failure is None;out=dict(passed=passed,failure=failure,samples=samples,selected_indices=[r['index']for r in selected],scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2))
 if passed:
  rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
 record('actual_safe_cap_null_motor_precheck_terminal_v%d'%a.version,[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,samples=len(samples),seconds=clock+1.5),next_step='Valid smallcapnull ->nativeonlyshort load/H/reference30 proof; thenfulloriginalB inthat sameepisode ifactualentry improved, no strokegrid');print(json.dumps(dict(passed=passed,failure=failure,samples=len(samples),seconds=clock+1.5)))
if __name__=='__main__':main()
