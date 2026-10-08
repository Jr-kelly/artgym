"""Project the loaded cap contact curve; reuse valid source poses, check all samples.

The linear jump to two-contact overlap intersects the original knife. This
resolves the contact manifold at small joint increments; no tolerance reduction.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);old=json.load(open(a.geometry));src=Path(old['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
L=np.array(old['rows'][0]['wrist_in_knife']);h0=z['robot_q'][7:].astype(float);rows=old['rows'][:9];began=time.monotonic();failure=None;record('loaded_cap_contact_manifold_curve_refinement_started_v944',[str(a.geometry)],dict(scope=__doc__,first_reused_poses=9,original_dense_failure='943 segment8 fraction1/7 PADbodygap-45.4um; geometryguard unchanged, solvecurvedcontact'),next_step='One contactmanifold projection, originaldensecertification andphysicaloverlap; no newlylowered geometryacceptance')
for seg in [8,9]:
 A=np.array(old['rows'][seg]['hand_q']);B=np.array(old['rows'][seg+1]['hand_q']);count=max(4,int(np.ceil(abs(B-A).max()/.008)));previous=np.array(rows[-1]['hand_q'])[16:]
 for u in np.linspace(0,1,count+1)[1:]:
  phase=old['rows'][seg]['phase']*(1-u)+old['rows'][seg+1]['phase']*u;desired=(A*(1-u)+B*u)[16:];seed=desired.copy()
  def decode(x):h=h0.copy();h[16:]=x;return h
  def residual(x):
   if time.monotonic()-began>150:raise TimeoutError('Bounded curve refinement')
   h=decode(x);G=g.gaps(h,L,float(z['slider_q']),'thumb',certify_clearance_m=.0002);r=list((x-desired)*.15)
   for name in(['hand_r_thumb_link4','hand_r_thumb_pad_link']if phase>=.45 else['hand_r_thumb_link4']):
    gap=next(c['gap_lower_bound_m']for c in G if c['hand_link']==name and c['knife_link']=='link_1'and c['knife_component']==0);r.append((gap-(-.000025 if name.endswith('link4')else .000025))*2000)
   for c in G:
    allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link'];r.append(min(0.,c['gap_lower_bound_m']-(-.00025 if allowed else .00004))*4000)
   r.extend(min(0.,c['gap_lower_bound_m']-.0004)*2500 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0004));return np.array(r)
  try:x=least_squares(residual,np.clip(seed,g.w.lower[16:]+.005,g.w.upper[16:]-.005),bounds=(g.w.lower[16:]+.005,g.w.upper[16:]-.005),max_nfev=35,diff_step=1e-5).x
  except TimeoutError as e:failure=str(e);break
  h=decode(x);G=g.gaps(h,L,float(z['slider_q']),'thumb');H=f.H.inspect(h);v=[c for c in G if c['gap_lower_bound_m']<(-.00028 if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link']else -.00001)];cap4=next(c['gap_lower_bound_m']for c in G if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']=='hand_r_thumb_link4');capP=next(c['gap_lower_bound_m']for c in G if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']=='hand_r_thumb_pad_link');row=dict(index=len(rows),phase=phase,hand_q=h.tolist(),wrist_in_knife=L.tolist(),arm_q=z['robot_q'][:7].tolist(),LINK4_cap_gap_m=cap4,PAD_cap_gap_m=capP,self=H,geometry_violations=v,contact_overlap_required=bool(phase>=.45));rows.append(row);previous=x;print(json.dumps(row),flush=True)
  if H or v or cap4>.0002 or(phase>=.45 and capP>.0002):failure='Original loadedcurve geometry constraint';break
 if failure:break
out=dict(source=old['source'],rows=rows,passed=failure is None,failure=failure,scope=__doc__,elapsed_s=time.monotonic()-began);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('loaded_cap_contact_manifold_curve_refinement_terminal_v944',[str(a.output/'result.json')],dict(passed=out['passed'],poses=len(rows),failure=failure,elapsed_s=out['elapsed_s']),next_step='Validcurve ->fulloriginaldensemesh/H+motorbound andone actualPADcontactoverlap shortsegment; blocked ->jointwrist/Indexbearing roll')
