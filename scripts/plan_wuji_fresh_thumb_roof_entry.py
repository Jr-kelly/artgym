"""Read-only thumb roof reach from an actually completed fresh pickup/flip.

No fixed final joint target; original whole-pad cap patch and complete B stroke
check determine eligibility. A planned pose is not physically reached entry.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'trace.npz');f=FunctionalEntryAffordance();q=np.r_[z['arm_q'][-1],z['q'][-1]].astype(float);O=transform(z['object'][-1,:3],z['object'][-1,3:7]);L=np.linalg.inv(O)@f.kin.forward(q[:7]);slider=float(z['slider'][-1]);V=f.vertices;target=np.array([0.,.006,-.038+slider]);h=q[7:].copy();initial=h[16:].copy();began=time.monotonic();record('actual_fresh_flip_thumb_roof_reach_started_v878',[str(a.source/'trace.npz')],dict(scope=__doc__,target=target.tolist()),next_step='One4joint wholethumb reach check; ifworkspace/H blocked usewholehandcontacttransfer, no forcegrid or forcedNNgoal')
 def geometry(v):
  cur=h.copy();cur[16:]=v;F=f.g.w.forward(cur);T=L@F['hand_r_thumb_pad_link'];P=V@T[:3,:3].T+T[:3,3];weights=np.exp(-(P[:,1]-P[:,1].min())/.0002);foot=weights@P/weights.sum();return cur,F,foot
 def residual(v):
  cur,F,foot=geometry(v);r=list((foot-target)*800)
  for gap in f.g.gaps(cur,L,slider,'thumb',frames=F):
   allowed=gap['knife_link']=='link_1'and gap['hand_link']=='hand_r_thumb_pad_link';r.append(min(0.,gap['gap_lower_bound_m']-(-.00015 if allowed else .0002))*1500)
  r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1000 for c in f.g.self_gaps(cur,'thumb',frames=F,certify_clearance_m=.0002));r.extend((v-initial)*.005);return np.array(r)
 fit=least_squares(residual,np.clip(initial,f.g.w.lower[16:]+.04,f.g.w.upper[16:]-.04),bounds=(f.g.w.lower[16:]+.04,f.g.w.upper[16:]-.04),max_nfev=100,diff_step=1e-5);cur,F,foot=geometry(fit.x);q[7:]=cur;aff=f.assess(q,O,slider);gaps=f.g.gaps(cur,L,slider,'thumb',frames=F);r=dict(source=str(a.source),source_frame=len(z['time'])-1,actual_source_hand=z['q'][-1].tolist(),target_knife_m=target.tolist(),planned_foot=foot.tolist(),foot_error_m=float(np.linalg.norm(foot-target)),planned_q=q.tolist(),planned_hand_q=cur.tolist(),affordance=aff,thumb_gaps=gaps,geometry_permits_transfer=bool(np.linalg.norm(foot-target)<.0005 and aff['reference_eligible']),elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(r,indent=2));record('actual_fresh_flip_thumb_roof_reach_terminal_v878',[str(a.output/'result.json')],dict(foot_error_m=r['foot_error_m'],affordance=aff,planned_thumb=cur[16:].tolist(),geometry_permits_transfer=r['geometry_permits_transfer']),next_step='Reachedgoalworkspaceproofonly; actualnormaloppositionmustpersist acrosscornertransfer, then originalcompleteB capacity. No nakedfree-thumb path withtwo-one-sidedcarriers');print(json.dumps({k:v for k,v in r.items()if k not in ['thumb_gaps']}),flush=True)
if __name__=='__main__':main()
