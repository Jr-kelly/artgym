"""Reuse the proven Pinky/Ring conversion on an actual partial wrist flip.

Old three bearing fingers and arm keep their recorded issued targets. Only the
two previously unused fingers move. Original meshes, H, PD and actuator limits
remain; a nominal path is not evidence of new bearing. Native load must precede
any old support retirement. This restored development lacks solver caches and
raw robot velocities and does not certify a fresh continuous demonstration.
"""
import argparse, json, math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import exact_hand_knife_intersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v975');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 old=Path('runs/flat-table-20261006/direct/preparation/actual-static-primary-two-idle-finger-bearing-v923r2/result.json');geo=json.loads(old.read_text());assert geo['passed'];z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);ids=np.arange(8,16);pid=np.arange(8,12);name='hand_r_pinky_pad_link'
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 V=np.concatenate([v for v,n in g.meshes[name]])
 def vertices(h):
  T=L@g.w.forward(h)[name];return V@T[:3,:3].T+T[:3,3]
 def foot(h):
  P=vertices(h);w=np.exp((P[:,1]-P[:,1].max())/.0002);return w@P/w.sum()
 path=[h0.copy()]
 for r in geo['rows'][1:]:
  h=h0.copy();h[ids]=np.array(r['hand_q'])[ids];path.append(h)
 last=path[-1].copy();target=foot(last).copy();target[1]=-.004
 def residual(x):
  h=last.copy();h[pid]=x;P=vertices(h);r=list((foot(h)[[0,2]]-target[[0,2]])*800);r.append((P[:,1].max()+.004)*1000);r.extend(min(0.,c['gap_lower_bound_m']+.0002)*1400 for c in g.gaps(h,L,float(z['slider_q']),'pinky',certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend((x-last[pid])*.02);return np.array(r)
 record('partial_flip_cached_bearing_precheck_start_'+a.version,[str(a.source),str(old)],dict(scope=__doc__,old_three_bearing_targets='exact recorded issued targets',new_reference_normal_N=.15),next_step='Original dense mesh/H; one native actual backbearing if valid')
 fit=least_squares(residual,last[pid],bounds=(g.w.lower[pid]+.015,g.w.upper[pid]-.015),max_nfev=60,diff_step=1e-5);closed=last.copy();closed[pid]=fit.x;path.append(closed);cert=[];failure=None
 for seg,(A,B)in enumerate(zip(path[:-1],path[1:])):
  for u in np.linspace(0,1,max(2,int(math.ceil(abs(B-A).max()/.02))+1)):
   h=A*(1-u)+B*u;H=f.H.inspect(h);viol=[]
   for d in ['pinky','ring']:
    for c in g.gaps(h,L,float(z['slider_q']),d,certify_clearance_m=.0002):
     if c['gap_lower_bound_m']<-.00021:
      ex=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),c)
      if not ex['no_intersection']:viol.append(ex)
   cert.append(dict(segment=seg,fraction=float(u),self=H,original_knife_intersections=viol))
   if H or viol:failure='Original dense H/knife path';break
  if failure:break
 kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,1.]];clock=1.;previous=issued[7:].copy()
 if failure is None:
  for i,h in enumerate(path):
   motor=issued[7:].copy();motor[ids]=h[ids]+(issued[7:][ids]-h0[ids])*(1-min(i/4.,1.))
   if i==len(path)-1:
    v=V[vertices(h)[:,1].argmax()];J=np.empty((3,4))
    for j,c in enumerate(pid):
     up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[name];B=L@g.w.forward(down)[name];J[:,j]=(A[:3,:3]@v+A[:3,3]-B[:3,:3]@v-B[:3,3])/2e-5
    motor[pid]+=J.T@np.array([0.,.15,0.])/kp[pid]
   if np.minimum(motor-g.w.lower,g.w.upper-motor).min()<=0:failure='Original motor joint limit';break
   clock+=max(1,int(math.ceil(abs(motor-previous).max()/.012)))/30.;rows.append(dict(time_s=clock,arm_q=issued[:7].tolist(),hand_q=motor.tolist()));previous=motor
 passed=failure is None;out=dict(passed=passed,failure=failure,source=str(a.source),dense_samples=cert,closed_pad_bounds_m=[vertices(closed).min(0).tolist(),vertices(closed).max(0).tolist()],seconds=clock+1.5,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
 if passed:
  rows.append(dict(rows[-1],time_s=clock+1.5));(a.output/'motor.json').write_text(json.dumps(dict(rows=rows,required_actual_source=str(a.source),development_abort_on_translation_m=.015,scope=__doc__,new_digit='pinky'),indent=2))
 record('partial_flip_cached_bearing_precheck_terminal_'+a.version,[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,dense_samples=len(cert),seconds=clock+1.5,closed_pad_bounds_m=out['closed_pad_bounds_m']),next_step='Actual newPinky/body load,H/carry before Thumb withdrawal, then coupled functional PAD conversion and fullB30');print(json.dumps({k:v for k,v in out.items()if k!='dense_samples'}))
if __name__=='__main__':main()
