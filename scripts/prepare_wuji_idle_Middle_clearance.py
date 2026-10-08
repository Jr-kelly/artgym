"""Clear one unloaded Middle housing before a loaded contact transition.

Actual927 has zero native Middle/body bearing and near-boundary self geometry.
Keep all arm/Index/Thumb and other motor targets exactly issued. Use original
convex-hull gradient for one small unloaded withdrawal, no tracking, force/gain
sweep, old bearing retirement, or altered H/physics. Native carry and H required.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import convex_intersection_radius,exact_hand_knife_intersection
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.load(open(a.source/'manifest.json'));trace=np.load(meta['source']);clock=float(trace['time'][meta['takeover_index']]);C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];native=min(C,key=lambda r:abs(r['time_s']-clock));assert not any('middle'in c['hand_link']and c['knife_link']=='link_0'and c['normal_magnitude_N']>.001 for c in native['contacts']);f=FunctionalEntryAffordance();g=f.g;h0=z['robot_q'][7:].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);pair=['hand_r_middle_link4','hand_r_thumb_pad_link']
def radius(h):
 F=g.w.forward(h);V=[]
 for name in pair:T=F[name];V.append([v@T[:3,:3].T+T[:3,3]for v,n in g.meshes[name]])
 return max(convex_intersection_radius(a,b)for a in V[0]for b in V[1])
r0=radius(h0);grad=np.empty(4)
for j,c in enumerate(range(4,8)):
 u=h0.copy();d=h0.copy();u[c]+=1e-4;d[c]-=1e-4;grad[j]=(radius(u)-radius(d))/.0002
delta=-grad*(r0+.0003)/(grad@grad);assert max(abs(delta))<.025;checks=[];failure=None
for u in np.linspace(0,1,25):
 h=h0.copy();h[4:8]+=delta*u;H=f.H.inspect(h);bad=[]
 for c in g.gaps(h,L,float(z['slider_q']),'middle',certify_clearance_m=.0002):
  if c['gap_lower_bound_m']<-.00001:
   exact=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),c)
   if not exact['no_intersection']:bad.append(dict(collision=c,exact=exact))
 checks.append(dict(fraction=float(u),radius=radius(h),self=H,knife_violations=bad))
 if H or bad:failure='Original dense unloaded withdrawal mesh/H invalid';break
passed=failure is None and checks[-1]['radius']<-.0001;issued=z['issued_target'].astype(float);motor=issued.copy();motor[11:15]+=delta;limits=np.r_[f.kin.lower,g.w.lower];upper=np.r_[f.kin.upper,g.w.upper];assert np.minimum(motor-limits,upper-motor).min()>0;out=dict(passed=passed,failure=failure,source=str(a.source),source_self_radius_m=r0,unloaded_Middle_delta_rad=delta.tolist(),dense_checks=checks,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
if passed:
 rows=[dict(time_s=t,arm_q=q[:7].tolist(),hand_q=q[7:].tolist())for t,q in[(0.,issued),(.5,motor),(2.5,motor)]];(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(a.source),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
record('actual_idle_Middle_clearance_prepared_v966',[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,source_self_radius_m=r0,final_geometry_radius_m=checks[-1]['radius'],delta_rad=delta.tolist(),scope=__doc__),next_step='ONE native unloadedwithdrawal whileoldIndex/Thumb/arm exactissued targets; actualH0 +quietcarry ->reuseactualclear end andnewbodybearing; no force/gain variants');print(json.dumps({k:v for k,v in out.items()if k!='dense_checks'}))
