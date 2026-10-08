"""Actual reached cap-bearing source -> functional thumb PAD geometry diagnostic.

Fixed wrist and actual Index bearing. Idle Middle can clear. This checks one
local endpoint and the full original B reference, never proves a supported path.
A new body bearing must be acquired before retiring the actual LINK4 cap clamp.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.wuji_measured_hold_reference import measured_hold_path
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',type=int,default=936);p.add_argument('--roof-region',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
h0=z['robot_q'][7:].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);ids=np.r_[np.arange(4,8),np.arange(16,20)];target=np.array([0.,.006,-.038+float(z['slider_q'])]);began=time.monotonic();pad='hand_r_thumb_pad_link';record('actual_safe_cap_to_functional_PAD_endpoint_started_v%d'%a.version,[str(a.source)],dict(scope=__doc__,target_knife_m=target.tolist(),original_stroke_m=.03),next_step='One8joint endpoint +original30/H; physicalbearingbeforethumbreplacement, no naked-thumb crossing')
def decode(x):h=h0.copy();h[ids]=x;return h
def foot(h,F):
 T=L@F[pad];P=f.vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(P[:,1]-P[:,1].min())/.0002);return w@P/w.sum()
def residual(x):
 if time.monotonic()-began>150:raise TimeoutError('Bounded local functional PAD check')
 h=decode(x);F=g.w.forward(h);P=foot(h,F);goal=np.array([np.clip(P[0],-.002,.002),.00645,np.clip(P[2],-.040,-.034)])if a.roof_region else target;r=list((P-goal)*1600);r.extend((x-h0[ids])*.002)
 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002):r.append(min(0.,c['gap_lower_bound_m']-.00025)*1600)
 for digit in ['middle','thumb']:
  for c in g.gaps(h,L,float(z['slider_q']),digit,frames=F,certify_clearance_m=.0002):
   allowed=c['hand_link']==pad and c['knife_link']=='link_1';r.append(min(0.,c['gap_lower_bound_m']-(-.00015 if allowed else .00015))*4000)
 return np.array(r)
failure=None
try:x=least_squares(residual,np.clip(h0[ids],g.w.lower[ids]+.005,g.w.upper[ids]-.005),bounds=(g.w.lower[ids]+.005,g.w.upper[ids]-.005),max_nfev=90,diff_step=1e-5).x
except TimeoutError as e:failure=str(e);x=h0[ids]
h=decode(x);F=g.w.forward(h);aff=f.assess_relative(L,h,float(z['slider_q']));P=foot(h,F);path=[]
if aff['reference_eligible']:
 q,audit=measured_hold_path(h,L[:3,:3].T@np.array([0,1.,0]),L[:3,:3].T@np.array([0,0,1.]),np.linspace(0,.03,31))
 for thumb,r in zip(q,audit['rows']):
  hB=h.copy();hB[16:]=thumb;path.append(dict(shift_m=r['shift_m'],self=f.H.inspect(hB)))
gaps=g.gaps(h,L,float(z['slider_q']),'thumb');geometric_violations=[c for c in gaps if c['gap_lower_bound_m']<(-.0002 if c['hand_link']==pad and c['knife_link']=='link_1'else 0.)];regionerror=float(np.linalg.norm(P-np.array([np.clip(P[0],-.002,.002),.00645,np.clip(P[2],-.040,-.034)])));out=dict(roof_region=a.roof_region,roof_region_error_m=regionerror,thumb_geometry_violations=geometric_violations,source=str(a.source),scope=__doc__,wrist_in_knife=L.tolist(),hand_q=h.tolist(),source_hand_q=h0.tolist(),foot_in_knife_m=P.tolist(),target_knife_m=target.tolist(),foot_error_m=float(np.linalg.norm(P-target)),affordance=aff,full_original_reference_self=path,endpoint_eligible=bool((regionerror<.0002 if a.roof_region else np.linalg.norm(P-target)<.0005)and not geometric_violations and aff['reference_eligible']and not any(r['self']for r in path)),failure=failure,elapsed_s=time.monotonic()-began);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_safe_cap_to_functional_PAD_endpoint_terminal_v%d'%a.version,[str(a.output/'result.json')],out,next_step='If reachable acquire newbodybearing then supported capLINK4-toPAD rolling; if fixedwristblocked couplewrist+actualIndexmaterial constraint without resettingoriginalB');print(json.dumps(out))
