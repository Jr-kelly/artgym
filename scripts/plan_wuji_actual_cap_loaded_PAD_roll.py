"""Loaded original thumb-skin roll from actual LINK4 cap contact to functional PAD.

Retains actual Index/wrist and all idle fingers. Both actual physical hulls must
contact the cap during overlap; original body clearance/H/limits remain. No naked
thumb withdrawal, force/gain grid or motor is inferred from endpoint eligibility.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--endpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');end=json.loads(a.endpoint.read_text());assert end['endpoint_eligible'];f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
h0=z['robot_q'][7:].astype(float);h1=np.array(end['hand_q']);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);began=time.monotonic();seed=h0[16:].copy();rows=[];failure=None;pad='hand_r_thumb_pad_link';bone='hand_r_thumb_link4';record('actual_loaded_cap_LINK4_to_PAD_roll_started_v942',[str(a.source),str(a.endpoint)],dict(scope=__doc__,overlap_range=[.45,.55],original30_reference=True,original_pd_effort=True),next_step='Onlyoriginalwholehull/H valid loadedcontactoverlap -> shortnativephysicalPADload proof beforeLINK4 release; fixedwristblocked ->coupledIndexbearing/wrist')
def decode(x):h=h0.copy();h[16:]=x;return h
def gaps(h):return g.gaps(h,L,float(z['slider_q']),'thumb',certify_clearance_m=.0002)
def selected(G,name):return next(c['gap_lower_bound_m']for c in G if c['hand_link']==name and c['knife_link']=='link_1'and c['knife_component']==0)
baseG=gaps(h0);capdepth=min(-.0002,selected(baseG,bone)-.00001)
for index,u in enumerate(np.linspace(0,1,21)):
 desired=h0[16:]*(1-u)+h1[16:]*u;previous=seed.copy()
 def residual(x):
  if time.monotonic()-began>160:raise TimeoutError('Bounded loadedcap localrolling geometry')
  h=decode(x);G=gaps(h);r=list((x-desired)*.2);cap4=selected(G,bone);capP=selected(G,pad)
  if u<=.55:r.append((cap4-(selected(baseG,bone)if index==0 else -.000025))*2000)
  if u>=.45:r.append((capP-.000025)*2000)
  for fraction in [.5,1.]:
   mh=decode(previous*(1-fraction)+x*fraction);mG=G if fraction==1 else gaps(mh)
   for c in mG:
    allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad];r.append(min(0.,c['gap_lower_bound_m']-(capdepth if allowed else .00004))*4000)
   r.extend(min(0.,c['gap_lower_bound_m']-.0004)*2500 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.0004))
  if u>.9:
   F=g.w.forward(h);T=L@F[pad];P=f.vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(P[:,1]-P[:,1].min())/.0002);foot=w@P/w.sum();goal=np.array([np.clip(foot[0],-.002,.002),.0061,np.clip(foot[2],-.04,-.033)]);r.extend((foot-goal)*1000)
  return np.array(r)
 try:seed=previous if index==0 else least_squares(residual,np.clip(previous,g.w.lower[16:]+.005,g.w.upper[16:]-.005),bounds=(g.w.lower[16:]+.005,g.w.upper[16:]-.005),max_nfev=60,diff_step=1e-5).x
 except TimeoutError as e:failure=str(e);break
 h=decode(seed);G=gaps(h);H=f.H.inspect(h);v=[c for c in G if c['gap_lower_bound_m']<(capdepth-.00001 if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad]else -.00001)];cap4=selected(G,bone);capP=selected(G,pad);loss=cap4>.0002 if u<.45 else max(cap4,capP)>.0002 if u<=.55 else capP>.0002;row=dict(index=index,phase=float(u),hand_q=h.tolist(),wrist_in_knife=L.tolist(),arm_q=z['robot_q'][:7].tolist(),LINK4_cap_gap_m=cap4,PAD_cap_gap_m=capP,self=H,geometry_violations=v,contact_overlap_required=bool(.45<=u<=.55));rows.append(row);print(json.dumps(row),flush=True)
 if v or H or loss:failure='Originalbody/H or loadedcap overlap constraint';break
out=dict(source=str(a.source),endpoint=str(a.endpoint),rows=rows,passed=len(rows)==21 and failure is None,failure=failure,elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_loaded_cap_LINK4_to_PAD_roll_terminal_v942',[str(a.output/'result.json')],out,next_step='Validloadedskin contactpath ->nativeoverlap proof then fulloriginalB30; blocked ->jointwrist/Indexmaterial rolling with meaningfulnewcontact, no pressureloop')
