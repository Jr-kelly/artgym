"""Coupled wrist/Index/Thumb roll retaining actual Index body material bearings.

Actual safe fresh926 cap-bearing input only; original meshes and limits. The
original LINK4 cap clamp stays until PAD contact overlaps. Geometric feasibility
is not force/carry or fresh-episode proof. Original B itself remains unchanged.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--endpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.load(open(a.source/'manifest.json'));prior=json.load(open(a.prior));end=json.load(open(a.endpoint));assert end['endpoint_eligible'];trace=np.load(meta['source']);clock=trace['time'][meta['takeover_index']];C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];contact=min(C,key=lambda r:abs(r['time_s']-clock))['contacts'];f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);q0=z['robot_q'].astype(float);h0=q0[7:];ids=np.r_[np.arange(0,4),np.arange(16,20)];arm0=q0[:7];L0=invO@f.kin.forward(arm0);boundslo=np.r_[f.kin.lower+.02,g.w.lower[ids]+.005];boundshi=np.r_[f.kin.upper-.02,g.w.upper[ids]-.005];bearings=[]
for name in['hand_r_index_link2','hand_r_index_link4']:
 cs=[c for c in contact if c['hand_link']==name and c['knife_link']=='link_0'];assert cs;w=np.array([c['normal_magnitude_N']for c in cs]);w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in cs]);T=L0@g.w.forward(h0)[name];point=T[:3,:3]@m+T[:3,3];bearings.append(dict(hand_link=name,material_point=m.tolist(),point_knife_m=point.tolist(),normal_only_knife_N=sum((np.array(c['force_normal_contribution_knife_N'])for c in cs),np.zeros(3)).tolist()))
phases=sorted(set([r['phase']for r in prior['rows']]+np.linspace(.55,1,10).tolist()));seed=np.r_[arm0,h0[ids]];began=time.monotonic();rows=[];failure=None;pad='hand_r_thumb_pad_link';bone='hand_r_thumb_link4';record('actual_coupled_loaded_cap_PAD_roll_started_v946',[str(a.source),str(a.prior),str(a.endpoint)],dict(scope=__doc__,actual_Index_bearings=bearings,original_arm_limit_reserve_rad=.02,old_LINK4_retire_only_after_PAD=True),next_step='Coupled actualIndexbearing/loadedthumbmesh geometry; originaldense interpolation +forceproxy motors thenactualPADload, no fingerfollower/gain/strokegrid')
def decode(x):h=h0.copy();h[ids]=x[7:];L=invO@f.kin.forward(x[:7]);return h,L,g.w.forward(h)
def capgap(G,name):return next(c['gap_lower_bound_m']for c in G if c['hand_link']==name and c['knife_link']=='link_1'and c['knife_component']==0)
for index,phase in enumerate(phases):
 previous=seed.copy();desired=np.array(min(prior['rows'],key=lambda r:abs(r['phase']-phase))['hand_q'])
 if phase>.5:desired[16:]=np.array(prior['rows'][-1]['hand_q'])[16:]*(2-2*phase)+np.array(end['hand_q'])[16:]*(2*phase-1)
 start=previous.copy();start[7+4:]=desired[16:]
 def residual(x):
  if time.monotonic()-began>180:raise TimeoutError('Bounded coupled actualcap geometry')
  h,L,F=decode(x);G=g.gaps(h,L,float(z['slider_q']),'thumb',frames=F,certify_clearance_m=.0002);r=list((x[:7]-arm0)*.005);r.extend((h[ids]-desired[ids])*.04)
  for b in bearings:
   T=L@F[b['hand_link']];point=T[:3,:3]@np.array(b['material_point'])+T[:3,3];r.extend((point-b['point_knife_m'])*2500)
  if phase<=.55:r.append((capgap(G,bone)-(-.000264835689 if index==0 else -.000025))*1800)
  if phase>=.45:r.append((capgap(G,pad)-.000025)*1800)
  for c in G:
   allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad];r.append(min(0.,c['gap_lower_bound_m']-(-.00028 if allowed else .00015))*4000)
  for fraction in [.5,1.]:
   mh,mL,mF=decode(previous*(1-fraction)+x*fraction);r.extend(min(0.,c['gap_lower_bound_m']-.0005)*2200 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.0005))
   if fraction==.5:
    for c in g.gaps(mh,mL,float(z['slider_q']),'thumb',frames=mF,certify_clearance_m=.0002):
     allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad];r.append(min(0.,c['gap_lower_bound_m']-(-.00028 if allowed else .00015))*4000)
  if phase>.55:
   T=L@F[pad];P=f.vertices@T[:3,:3].T+T[:3,3];w=np.exp(-(P[:,1]-P[:,1].min())/.0002);point=w@P/w.sum();goal=np.array([np.clip(point[0],-.002,.002),.00615,np.clip(point[2],-.04,-.033)]);r.extend((point-goal)*min(1,(phase-.55)/.25)*1200)
  return np.array(r)
 try:seed=previous if index==0 else least_squares(residual,np.clip(start,boundslo+1e-7,boundshi-1e-7),bounds=(boundslo,boundshi),max_nfev=45,diff_step=1e-5).x
 except TimeoutError as e:failure=str(e);break
 h,L,F=decode(seed);G=g.gaps(h,L,float(z['slider_q']),'thumb');H=f.H.inspect(h);v=[c for c in G if c['gap_lower_bound_m']<(-.00029 if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad]else -.00001)];errors=[]
 for b in bearings:
  T=L@F[b['hand_link']];errors.append(float(np.linalg.norm(T[:3,:3]@np.array(b['material_point'])+T[:3,3]-b['point_knife_m'])))
 row=dict(index=index,phase=phase,arm_q=seed[:7].tolist(),hand_q=h.tolist(),wrist_in_knife=L.tolist(),LINK4_cap_gap_m=capgap(G,bone),PAD_cap_gap_m=capgap(G,pad),Index_material_errors_m=errors,self=H,geometry_violations=v,contact_overlap_required=bool(.45<=phase<=.55));rows.append(row);print(json.dumps(row),flush=True)
 if H or v or max(errors)>.0002 or(phase<=.55 and row['LINK4_cap_gap_m']>.0002)or(phase>=.45 and row['PAD_cap_gap_m']>.0002):failure='Original coupled bearing/contact/H constraint';break
out=dict(source=str(a.source),rows=rows,Index_bearings=bearings,passed=len(rows)==len(phases)and failure is None,failure=failure,elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_coupled_loaded_cap_PAD_roll_terminal_v946',[str(a.output/'result.json')],dict(passed=out['passed'],poses=len(rows),failure=failure,elapsed_s=out['elapsed_s']),next_step='Validcoupled overlap prefix ->originaldensemesh/H motorprecheck andONE actualPADsupport thencontinuation/fullB30; completefresh episode aftertrueimprovement')
