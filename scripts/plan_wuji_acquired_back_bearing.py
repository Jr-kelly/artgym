"""Check one new ring bearing before withdrawing any actual old clamp.

Actual v877 intrinsic pose and the other nineteen motor/state coordinates remain
fixed in this geometry diagnostic. No new follower, pressure or physical mutation.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;h=z['robot_q'][7:].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);name='hand_r_ring_pad_link';V=np.concatenate([v for v,_ in g.meshes[name]]);seed=np.array([.542,-.1,1.177,.053]);lo=np.array([-.007,-.004,-.062]);hi=np.array([.007,-.004,-.035]);begin=time.monotonic();record('new_acquired_ring_back_bearing_geometry_started_v888',[str(a.source)],dict(scope=__doc__,region=[lo.tolist(),hi.tolist()]),next_step='Ifreachable establishactualRingbearingbeforeanyoldThumbrelease; elsewholegripshift withretainedoldcontacts, no4jointtracker')
 def calculate(x):
  q=h.copy();q[12:16]=x;F=g.w.forward(q);T=L@F[name];P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,1]-P[:,1].max())/.0002);point=w@P/w.sum();return q,F,point
 def residual(x):
  q,F,P=calculate(x);r=list((P-np.clip(P,lo,hi))*700);r.extend(min(0.,c['gap_lower_bound_m']+.0003)*1400 for c in g.gaps(q,L,float(z['slider_q']),'ring',frames=F,certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(q,f.H.pairs,certify_clearance_m=.0002));r.extend((x-seed)*.01);return np.array(r)
 fit=least_squares(residual,seed,bounds=(g.w.lower[12:16]+.03,g.w.upper[12:16]-.03),max_nfev=70,diff_step=1e-5);q,F,P=calculate(fit.x);error=float(np.linalg.norm(P-np.clip(P,lo,hi)));bad=f.H.inspect(q);r=dict(hand_q=q.tolist(),wrist_in_knife=L.tolist(),point_knife_m=P.tolist(),contact_error_m=error,self=bad,geometry_pass=bool(error<.0006 and not bad),seconds=time.monotonic()-begin,scope=__doc__);(a.output/'result.json').write_text(json.dumps(r,indent=2));record('new_acquired_ring_back_bearing_geometry_terminal_v888',[str(a.output/'result.json')],r,next_step='ReachableRingbackbearing ->oneactualacquisitionthenoldclamptransfer; blockedRingalone ->coupledgripshift, no new normalpressuregrid');print(json.dumps(r))
if __name__=='__main__':main()
