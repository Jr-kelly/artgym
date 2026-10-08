"""Functional whole-hand endpoint for a relative quarter-roll after real fresh flip.

Derived from current acquired grip and the proven original773 B capability prior.
This is geometric only; it must pass originalfull B physics before transfer learning.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.wuji_measured_hold_reference import measured_hold_path
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);src=Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/simulation');z=np.load(src/'trace.npz');f=FunctionalEntryAffordance();g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json',max_face_axes=8);O=transform(z['object'][-1,:3],z['object'][-1,3:7]);Lcurrent=np.linalg.inv(O)@f.kin.forward(z['arm_q'][-1]);quarter=transform(quaternion=Rotation.from_euler('z',-90,degrees=True).as_quat());L0=quarter@Lcurrent;slider=float(z['slider'][-1]);prior=np.load('runs/flat-table-20261006/direct/development/ideal-tail-30mm-fullB-v773/simulation/trace.npz');initial=prior['q'][119].astype(float);initial[8:12]=z['q'][-1,8:12];Oprior=transform(prior['object'][119,:3],prior['object'][119,3:7]);Xprior=np.linalg.inv(Oprior)@f.kin.forward(prior['arm_q'][119]);end,_=measured_hold_path(initial,Xprior[:3,:3].T@np.array([0,1,0.]),Xprior[:3,:3].T@np.array([0,0,1.]),np.linspace(0,.03,31));ids=np.array(list(range(8))+list(range(12,20)));x0=np.r_[np.zeros(6),initial[ids],end[-1]];lo=np.r_[[-.030]*3,[-.25]*3,g.w.lower[ids]+.045,g.w.lower[16:]+.045];hi=np.r_[[.030]*3,[.25]*3,g.w.upper[ids]-.045,g.w.upper[16:]-.045];x0=np.clip(x0,lo+1e-7,hi-1e-7);names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_ring_pad_link','hand_r_thumb_pad_link'];V={n:np.concatenate([v for v,_ in g.meshes[n]])for n in names};regions=[(np.array([-.007,-.004,-.005]),np.array([.007,-.004,.01])),(np.array([-.007,-.004,-.028]),np.array([.007,-.004,-.015])),(np.array([-.007,-.004,-.060]),np.array([.007,-.004,-.038]))];begin=time.monotonic();calls=[0];best=[float('inf'),x0.copy()];record('functional_relative_quarterroll_endpoint_geometry_started_v879',[str(src/'trace.npz')],dict(scope=__doc__,initial_current_L=Lcurrent.tolist(),quarterrolled_seed_L=L0.tolist(),goal='Threeback-Ybearingpads andthumbfrontcapwhole30mm reference, no fixedq/wrist demand'),next_step='Oneboundedwholehand solve; fullpath/physicalcapacity beforedevelopingrelativecornerrollingtransfer')
 def decode(x):
  L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];h=initial.copy();h[ids]=x[6:22];end=h.copy();end[16:]=x[22:];return L,[h,end]
 def foot(L,F,n,side):
  T=L@F[n];P=V[n]@T[:3,:3].T+T[:3,3];v=side*P[:,1];w=np.exp((v-v.max())/.0002);return w@P/w.sum()
 def residual(x):
  if time.monotonic()-begin>210:raise TimeoutError('Singleoperatinggrip bounded210s')
  L,hs=decode(x);r=[]
  for j,h in enumerate(hs):
   F=g.w.forward(h)
   for n,(low,high)in zip(names[:3],regions):
    P=foot(L,F,n,1);r.extend((P-np.clip(P,low,high))*800)
   P=foot(L,F,names[-1],-1);low=np.array([-.0035,.006,-.042+slider+j*.03]);high=np.array([.0035,.006,-.034+slider+j*.03]);r.extend((P-np.clip(P,low,high))*800)
   for digit in ['index','middle','ring','thumb']:
    for gap in g.gaps(h,L,slider+j*.03,digit,frames=F):
     allowed=(gap['knife_link']=='link_0'and gap['hand_link']in names[:3])or(gap['knife_link']=='link_1'and gap['hand_link']==names[-1]);r.append(min(0.,gap['gap_lower_bound_m']-(-.0002 if allowed else .0002))*1300)
   r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1000 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002))
  r.extend((x[:3]-x0[:3])*2);r.extend((x[3:]-x0[3:])*.01);cost=float(np.dot(r,r));calls[0]+=1
  if cost<best[0]:best[:]=[cost,x.copy()]
  if calls[0]%300==0:print(json.dumps(dict(calls=calls[0],cost=cost,best=best[0],elapsed_s=time.monotonic()-begin)),flush=True)
  return np.array(r)
 failure=None
 try:fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=90,diff_step=1e-5);x=fit.x
 except TimeoutError as e:failure=str(e);x=best[1]
 L,hs=decode(x);arm,ik=f.kin.solve_near(O@L,z['arm_q'][-1].astype(float),max_step=.8,minimum_margin=.06);aff=f.assess_relative(L,hs[0],slider);points=[foot(L,g.w.forward(hs[0]),n,1 if n!=names[-1]else-1).tolist()for n in names];pose_errors=[float(np.linalg.norm(np.array(P)-np.clip(P,*region)))for P,region in zip(points[:3],regions)];H=[f.H.inspect(h)for h in hs];passed=max(pose_errors)<.0006 and aff['tail_roof_distance_m']<.0006 and aff['reference_eligible']and not any(H)and ik['position_m']<.0003 and ik['rotation_rad']<.003;r=dict(wrist_in_knife=L.tolist(),hand_q=hs[0].tolist(),end_hand_q=hs[1].tolist(),arm_q=arm.tolist(),arm_IK=ik,points=points,bearing_errors_m=pose_errors,affordance=aff,self=H,geometry_permits_native=bool(passed),calls=calls[0],failure=failure,elapsed_s=time.monotonic()-begin,scope=__doc__);(a.output/'result.json').write_text(json.dumps(r,indent=2));record('functional_relative_quarterroll_endpoint_geometry_terminal_v879',[str(a.output/'result.json')],dict(passed=bool(passed),bearing_errors_m=pose_errors,affordance=aff,arm_IK=ik,failure=failure),next_step='Feasible operatinggoal originalBcapacity diagnostic first; blocked adjustwholegripcontacttopology, no staticpressure orheadscan');print(json.dumps(r),flush=True)
if __name__=='__main__':main()
