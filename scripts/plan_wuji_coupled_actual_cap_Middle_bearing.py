"""Coupled new-Middle side bearing while all actual Index/Thumb cap bearings stay.

Reuse actual safe927 and prior939 route. Index2 and Thumb axial cap points stay. Index4 may roll tangentially
on the original backside, with no normal separation and a bounded surface region. Added body support must load
before the Thumb leaves its axial cap chamfer; no common pressure/gain scan.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);p.add_argument('--endpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',type=Path);p.add_argument('--back-corner',action='store_true');p.add_argument('--rolling-index-back',action='store_true');p.add_argument('--version',default='v954');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.load(open(a.source/'manifest.json'));prior=json.load(open(a.prior));end=json.load(open(a.endpoint));assert end['endpoint_eligible'];trace=np.load(meta['source']);clock=trace['time'][meta['takeover_index']];C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];contact=min(C,key=lambda r:abs(r['time_s']-clock))['contacts'];f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);q0=z['robot_q'].astype(float);h0=q0[7:];ids=np.r_[np.arange(0,4),np.arange(16,20),np.arange(4,8)];arm0=q0[:7];L0=invO@f.kin.forward(arm0);boundslo=np.r_[f.kin.lower+.02,g.w.lower[ids]+.005];boundshi=np.r_[f.kin.upper-.02,g.w.upper[ids]-.005];bearings=[]
for name in['hand_r_index_link2','hand_r_index_link4','hand_r_thumb_link4']:
 cs=[c for c in contact if c['hand_link']==name and c['knife_link']==('link_1'if name=='hand_r_thumb_link4'else 'link_0')];assert cs;w=np.array([c['normal_magnitude_N']for c in cs]);w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in cs]);T=L0@g.w.forward(h0)[name];point=T[:3,:3]@m+T[:3,3];bearings.append(dict(hand_link=name,material_point=m.tolist(),point_knife_m=point.tolist(),normal_only_knife_N=sum((np.array(c['force_normal_contribution_knife_N'])for c in cs),np.zeros(3)).tolist()))
assert prior['passed'];phases=np.linspace(0,1,len(prior['rows'])).tolist();seed=np.r_[arm0,h0[ids]];began=time.monotonic();rows=[];failure=None;pad='hand_r_thumb_pad_link';bone='hand_r_thumb_link4';record('actual_coupled_three_bearing_newMiddle_started_'+a.version,[str(a.source),str(a.prior),str(a.endpoint)],dict(scope=__doc__,actual_actual_primary_bearings=bearings,original_arm_limit_reserve_rad=.02,old_LINK4_retire_only_after_PAD=True),next_step='Coupled actualIndexbearing/loadedthumbmesh geometry; originaldense interpolation +forceproxy motors thenactualPADload, no fingerfollower/gain/strokegrid')
def decode(x):h=h0.copy();h[ids]=x[7:];L=invO@f.kin.forward(x[:7]);return h,L,g.w.forward(h)
def capgap(G,name):return next(c['gap_lower_bound_m']for c in G if c['hand_link']==name and c['knife_link']=='link_1'and c['knife_component']==0)
if a.resume:
 prior_valid=json.load(open(a.resume));assert prior_valid['source']==str(a.source);rows=prior_valid['rows'];assert not any(r['self']or r['geometry_violations']for r in rows);seed=np.r_[rows[-1]['arm_q'],np.array(rows[-1]['hand_q'])[ids]]
for index,phase in enumerate(phases):
 if index<len(rows):continue
 previous=seed.copy();desired=np.array(prior['rows'][index]['hand_q']);start=previous.copy();start[15:]=desired[4:8]
 def residual(x):
  if time.monotonic()-began>180:raise TimeoutError('Bounded coupled newMiddle bearing geometry')
  h,L,F=decode(x);G=g.gaps(h,L,float(z['slider_q']),'thumb',frames=F,certify_clearance_m=.0002);r=list((x[:7]-arm0)*.005);r.extend((h[ids]-desired[ids])*.04)
  for b in bearings:
   T=L@F[b['hand_link']];point=T[:3,:3]@np.array(b['material_point'])+T[:3,3];
   delta=point-np.array(b['point_knife_m'])
   if a.rolling_index_back and b['hand_link']=='hand_r_index_link4':
    r.append(delta[1]*2500);r.extend(delta[[0,2]]*100);r.extend(np.maximum(0.,np.abs(delta[[0,2]])-np.array([.003,.006]))*2500);r.append(min(0.,point[0]+.0091)*2500);r.append(min(0.,.0091-point[0])*2500)
   else:r.extend(delta*2500)
  name='hand_r_middle_pad_link';T=L@F[name];V=np.concatenate([v for v,Nv in g.meshes[name]]);P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,0]-P[:,0].max())/.00015);foot=w@P/w.sum();goal=np.array(prior['rows'][index]['foot_knife_m']);goal[1]=-.0044 if a.back_corner and index==len(phases)-1 else goal[1];r.extend((foot-goal)*1400)
  for c in g.gaps(h,L,float(z['slider_q']),'middle',frames=F,certify_clearance_m=.0002):
   allowed=c['hand_link']in['hand_r_middle_pad_link','hand_r_middle_link4']and c['knife_link']=='link_0';r.append(min(0.,c['gap_lower_bound_m']-(-.00015 if allowed else .00015))*4000)
  for c in G:
   allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad];r.append(min(0.,c['gap_lower_bound_m']-(-.00028 if allowed else .00015))*4000)
  for fraction in [.5,1.]:
   mh,mL,mF=decode(previous*(1-fraction)+x*fraction);r.extend(min(0.,c['gap_lower_bound_m']-(.001 if'middle'in c['link_a']+c['link_b']else .0003))*2200 for c in g.pair_gaps(mh,f.H.pairs,certify_clearance_m=.001))
   if fraction==.5:
    for c in g.gaps(mh,mL,float(z['slider_q']),'thumb',frames=mF,certify_clearance_m=.0002):
     allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad];r.append(min(0.,c['gap_lower_bound_m']-(-.00028 if allowed else .00015))*4000)
  return np.array(r)
 try:seed=previous if index==0 else least_squares(residual,np.clip(start,boundslo+1e-7,boundshi-1e-7),bounds=(boundslo,boundshi),max_nfev=45,diff_step=1e-5).x
 except TimeoutError as e:failure=str(e);break
 h,L,F=decode(seed);G=g.gaps(h,L,float(z['slider_q']),'thumb');H=f.H.inspect(h);v=[c for c in G if c['gap_lower_bound_m']<(-.00029 if c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in[bone,pad]else -.00001)];errors=[]
 for b in bearings:
  T=L@F[b['hand_link']];errors.append(float(np.linalg.norm(T[:3,:3]@np.array(b['material_point'])+T[:3,3]-b['point_knife_m'])))
 T=L@F['hand_r_middle_pad_link'];V=np.concatenate([v for v,Nv in g.meshes['hand_r_middle_pad_link']]);P=V@T[:3,:3].T+T[:3,3];w=np.exp((P[:,0]-P[:,0].max())/.00015);foot=w@P/w.sum();goal=np.array(prior['rows'][index]['foot_knife_m']);goal[1]=-.0044 if a.back_corner and index==len(phases)-1 else goal[1];middle_error=float(np.linalg.norm(foot-goal));
 row=dict(Middle_foot_knife_m=foot.tolist(),Middle_pad_bounds_knife_m=[P.min(0).tolist(),P.max(0).tolist()],Middle_foot_error_m=middle_error,index=index,phase=phase,arm_q=seed[:7].tolist(),hand_q=h.tolist(),wrist_in_knife=L.tolist(),LINK4_cap_gap_m=capgap(G,bone),PAD_cap_gap_m=capgap(G,pad),Index_material_errors_m=errors,self=H,geometry_violations=v,new_Middle_body_acquire_required=bool(index==len(phases)-1));rows.append(row);print(json.dumps(row),flush=True)

 accepted_errors=errors.copy()
 if a.rolling_index_back:
  b=bearings[1];T=L@F[b['hand_link']];delta=T[:3,:3]@np.array(b['material_point'])+T[:3,3]-b['point_knife_m'];row['Index4_back_surface_rolling_delta_m']=delta.tolist();accepted_errors[1]=abs(float(delta[1]))
  if abs(delta[0])>.003 or abs(delta[2])>.006 or not(-.0091<=b['point_knife_m'][0]+delta[0]<=.0091):failure='Index4 rolled beyond original body support surface';break
 if H or v or max(accepted_errors)>.0002 or row['LINK4_cap_gap_m']>.0002 or middle_error>.0007:failure='Original coupled bearing/contact/H constraint';break
out=dict(source=str(a.source),rows=rows,actual_primary_bearings=bearings,back_corner=a.back_corner,rolling_index_back=a.rolling_index_back,resume=str(a.resume)if a.resume else None,passed=len(rows)==len(phases)and failure is None,failure=failure,elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_coupled_three_bearing_newMiddle_terminal_'+a.version,[str(a.output/'result.json')],dict(passed=out['passed'],poses=len(rows),failure=failure,elapsed_s=out['elapsed_s']),next_step='Validcoupled overlap prefix ->originaldensemesh/H motorprecheck andONE actualPADsupport thencontinuation/fullB30; completefresh episode aftertrueimprovement')
