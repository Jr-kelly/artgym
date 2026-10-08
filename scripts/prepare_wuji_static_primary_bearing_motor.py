"""Original-actuator new-bearing motor path retaining actual old three-primary targets.

Offline full original mesh/H interpolation check; single new-finger contact closure
and same .15N Jacobian motor reference. Native normals still certify actual bearing.
No object pose follower, finger servo, added gain, state writer or force measurement.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v922');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.loads(a.geometry.read_text());assert geo['passed']and not geo['endpoint_only'];src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 digit=geo['digit'];ids=np.arange(12,16)if digit=='ring'else np.arange(8,12);moving=np.array(geo.get('moving_joint_indices',ids),dtype=int);checked_digits=['pinky','ring']if digit=='pinky'and 12 in moving else [digit];name='hand_r_'+digit+'_pad_link';V=np.concatenate([v for v,N in g.meshes[name]]);L=np.array(geo['rows'][0]['wrist_in_knife']);h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);record('static_primary_new_bearing_motor_precheck_started_'+a.version,[str(a.geometry)],dict(scope=__doc__,new_digit=digit,original_new_bearing_motor_force_reference_N=.15),next_step='Dense nominal mesh/H then originaltarget/bounds check; oneactualnewbearing only ifpassed')
 def vertices(h):
  T=L@g.w.forward(h)[name];return V@T[:3,:3].T+T[:3,3]
 def foot(h):
  P=vertices(h);w=np.exp((P[:,1]-P[:,1].max())/.0002);return w@P/w.sum()
 def close_residual(x):
  h=last.copy();h[ids]=x;P=vertices(h);r=list((foot(h)[[0,2]]-foot(last)[[0,2]])*800);r.append((P[:,1].max()+.004)*1000);r.extend(min(0.,c['gap_lower_bound_m']+.0002)*1400 for c in g.gaps(h,L,float(z['slider_q']),digit,certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend((x-last[ids])*.02);return np.array(r)
 path=[np.array(r['hand_q'])for r in geo['rows']];last=path[-1];fit=least_squares(close_residual,last[ids],bounds=(g.w.lower[ids]+.015,g.w.upper[ids]-.015),max_nfev=60,diff_step=1e-5);closed=last.copy();closed[ids]=fit.x;path.append(closed);samples=[];failure=None
 for segment,(A,B)in enumerate(zip(path[:-1],path[1:])):
  count=max(2,int(math.ceil(abs(B-A).max()/.025))+1)
  for u in np.linspace(0,1,count):
   h=A*(1-u)+B*u;gap=min([c for d in checked_digits for c in g.gaps(h,L,float(z['slider_q']),d,certify_clearance_m=.0002)],key=lambda c:c['gap_lower_bound_m']);bad=f.H.inspect(h);row=dict(segment=segment,fraction=float(u),min_new_finger_knife_SAT_gap_m=gap['gap_lower_bound_m'],closest_hand_link=gap['hand_link'],self=bad);samples.append(row)
   if gap['gap_lower_bound_m']<-.00021 or bad:failure='Original nominal dense mesh/H route invalid';break
  if failure:break
 rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in [0.,1.]];clock=1.;previous=issued[7:].copy()
 if failure is None:
  for index,h in enumerate(path):
   motor=issued[7:].copy();motor[moving]=h[moving]+(issued[7:][moving]-h0[moving])*(1-min(index/4.,1.))
   if index==len(path)-1:
    # Closed contact base, before force preload; highest-Y original material vertex.
    v=V[vertices(h)[:,1].argmax()];J=np.empty((3,4))
    for j,c in enumerate(ids):
     up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[name];B=L@g.w.forward(down)[name];J[:,j]=(A[:3,:3]@v+A[:3,3]-B[:3,:3]@v-B[:3,3])/2e-5
    motor[ids]+=J.T@np.array([0.,.15,0.])/kp[ids]
   if min(np.minimum(motor-g.w.lower,g.w.upper-motor))<=0:failure='Original motor joint limit';break
   frames=max(1,int(math.ceil(abs(motor-previous).max()/.012)));clock+=frames/30.;rows.append(dict(time_s=clock,arm_q=issued[:7].tolist(),hand_q=motor.tolist()));previous=motor
 passed=failure is None;audit=dict(passed=passed,failure=failure,samples=samples,closed_pad_bounds_knife_m=[vertices(closed).min(0).tolist(),vertices(closed).max(0).tolist()],new_digit=digit,original_new_bearing_motor_force_reference_N=.15,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(audit,indent=2))
 if passed:
  rows.append(dict(rows[-1],time_s=clock+1.5));motor=dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.04,scope=__doc__,new_digit=digit);(a.output/'motor.json').write_text(json.dumps(motor,indent=2))
 record('static_primary_new_bearing_motor_precheck_terminal_'+a.version,[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,dense_samples=len(samples),seconds=clock+1.5,new_digit=digit),next_step='Ifpassed actualstable877 newPinky bearing shortnative, old3 exact targets retained; trueback/load+H beforefreshsameepisode');print(json.dumps(dict(passed=passed,failure=failure,dense_samples=len(samples),seconds=clock+1.5,closed_patch_max_Y_m=float(vertices(closed)[:,1].max()))))
if __name__=='__main__':main()
