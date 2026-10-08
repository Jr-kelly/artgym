"""Seat original palm as a body support while actual Thumb/Middle self bearing stays.

Source927 Middle has an indirect ~.26N Thumb self reaction. It cannot be treated
as unloaded just because it has no knife contact. Keep all Thumb/Middle/Pinky/
Ring actual geometry and issued load, allow bounded Index surface rolling and
coupled wrist motion. The original palm approaches the body near +Z48mm before
that existing self support is retired. Original meshes/limits/H; geometry only.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.wuji_exact_knife_intersection import convex_intersection_radius
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--palm-prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--resume',type=Path);p.add_argument('--allow-held-translation',action='store_true');p.add_argument('--rolling-index-skin',action='store_true');p.add_argument('--actual-actuator-headroom',action='store_true');p.add_argument('--version',default='v969');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');C=json.load(open(a.calibration));assert C['source']==str(a.source);prior=min(json.load(open(a.palm_prior)),key=lambda r:r['L1_distance_m']);f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
q0=z['robot_q'].astype(float);h0=q0[7:];O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);L0=invO@f.kin.forward(q0[:7]);T=L0@g.w.forward(h0)['hand_r_base_link'];P0=np.array(prior['palm_point_knife_m']);material=T[:3,:3].T@(P0-T[:3,3]);goal=np.array(prior['body_point_knife_m']);goal[0]-=.0001;goal[1]+=.0001;seed=np.r_[q0[:7],h0[:4],np.zeros(3)]if a.allow_held_translation else np.r_[q0[:7],h0[:4]];boundslo=np.r_[f.kin.lower+.02,g.w.lower[:4]+.005];boundshi=np.r_[f.kin.upper-.02,g.w.upper[:4]-.005];
if a.allow_held_translation:boundslo=np.r_[boundslo,np.full(3,-.03)];boundshi=np.r_[boundshi,np.full(3,.03)]
if a.actual_actuator_headroom:
 offset=z['issued_target'][:7]-q0[:7];boundslo[:7]=f.kin.lower+np.maximum(0.,-offset)+.002;boundshi[:7]=f.kin.upper-np.maximum(0.,offset)-.002
points=np.array(C['points_knife_m']);M=np.array(C['material_points_link_m']);rows=[];began=time.monotonic();failure=None;palmV=g.meshes['hand_r_base_link'][prior['palm_component']][0];parts=g.knife_geometry.collision_parts(float(z['slider_q']));record('actual_loaded_palm_backup_planner_started_'+a.version,[str(a.source),str(a.calibration),str(a.palm_prior)],dict(scope=__doc__,palm_L1_initial_gap_m=prior['L1_distance_m'],original_Thumb_Middle_geometry_preserved=True),next_step='One coupledloadedpalm approach, originaldensemesh/H+nativePALM body normal before withdrawing indirectMiddle support')
if a.rolling_index_skin:
 assert a.allow_held_translation
 skinE=[ConvexHull(g.meshes[name][0][0]).equations for name,k in C['keys'][:2]];skin_faces=[int(np.argmax(E[:,:3]@m+E[:,3]))for E,m in zip(skinE,M[:2])];skin_levels=[float((E[:,:3]@m+E[:,3])[j])for E,m,j in zip(skinE,M[:2],skin_faces)];boundslo=np.r_[boundslo,(M[:2]-.006).ravel()];boundshi=np.r_[boundshi,(M[:2]+.006).ravel()];seed=np.r_[seed,M[:2].ravel()]
def decode(x):
 h=h0.copy();h[:4]=x[7:11];plannedO=O.copy()
 if a.allow_held_translation:plannedO[:3,3]+=x[11:14]
 L=np.linalg.inv(plannedO)@f.kin.forward(x[:7]);return h,L,g.w.forward(h)
if a.resume:
 rows=json.load(open(a.resume))['rows'];seed=np.r_[rows[-1]['arm_q'],rows[-1]['hand_q'][:4],rows[-1].get('object_world_translation_goal_m',[0.,0.,0.])]if a.allow_held_translation else np.r_[rows[-1]['arm_q'],rows[-1]['hand_q'][:4]]
if a.rolling_index_skin:
 if a.resume:seed=np.r_[seed,np.array(rows[-1].get('Index_contact_materials_link_m',M[:2])).ravel()]
 # Retain the last finite old body patches while finger skin rolls thereafter.
 last=rows[-1]if rows else None
 if last:
  F=g.w.forward(last['hand_q']);L=np.array(last['wrist_in_knife']);
  for j,(name,k)in enumerate(C['keys'][:2]):T=L@F[name];points[j]=T[:3,:3]@np.array(last.get('Index_contact_materials_link_m',M[:2]))[j]+T[:3,3]
for index,u in enumerate(np.linspace(0,1,9)):
 if index<len(rows):continue
 desired=P0*(1-u)+goal*u;previous=seed.copy()
 def residual(x):
  if time.monotonic()-began>150:raise TimeoutError('Bounded loaded palm approach')
  h,L,F=decode(x);r=list((x-previous)*.03)
  if a.allow_held_translation:r.extend(x[11:14]*50)
  currentM=M.copy()
  if a.rolling_index_skin:currentM[:2]=x[14:].reshape(2,3)
  actual=[]
  for (name,knife),m in zip(C['keys'],currentM):T=L@F[name];actual.append(T[:3,:3]@m+T[:3,3])
  actual=np.array(actual)
  if a.rolling_index_skin:
   r.extend((actual[:2]-points[:2]).ravel()*2500)
   for j,E in enumerate(skinE):
    v=E[:,:3]@currentM[j]+E[:,3];r.extend(np.maximum(0.,v-.000002)*5000);r.append((v[skin_faces[j]]-skin_levels[j])*2500)
  r.extend((actual[2]-points[2])*4000);r.append((actual[0,0]-points[0,0])*3000);r.append((actual[1,1]-points[1,1])*3000);r.extend((actual[:2]-points[:2]).ravel()*50);r.append(min(0.,actual[0,1]+.0038)*4000);r.append(min(0.,.0038-actual[0,1])*4000);r.append(min(0.,actual[1,0]+.0093)*4000);r.append(min(0.,.0093-actual[1,0])*4000);r.extend(np.maximum(0.,abs(actual[:2]-points[:2])-.008).ravel()*2500)
  T=L@F['hand_r_base_link'];r.extend((T[:3,:3]@material+T[:3,3]-desired)*1800)
  for fraction in[.5,1.]:
   nh,nL,nF=decode(previous*(1-fraction)+x*fraction);r.extend(min(0.,c['gap_lower_bound_m']-.00015)*1400 for c in g.pair_gaps(nh,f.H.pairs,certify_clearance_m=.0002)if not('middle'in c['link_a']+c['link_b']and'thumb'in c['link_a']+c['link_b']))
   for c in g.gaps(nh,nL,float(z['slider_q']),'thumb',frames=nF,certify_clearance_m=.0002):
    allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link'];r.append(min(0.,c['gap_lower_bound_m']-(-.00028 if allowed else .00005))*3000)
  return np.array(r)
 try:seed=previous if index==0 else least_squares(residual,previous,bounds=(boundslo,boundshi),max_nfev=50,diff_step=1e-5).x
 except TimeoutError as e:failure=str(e);break
 h,L,F=decode(seed);actual=[];currentM=M.copy()
 if a.rolling_index_skin:currentM[:2]=seed[14:].reshape(2,3)
 for (name,knife),m in zip(C['keys'],currentM):T=L@F[name];actual.append(T[:3,:3]@m+T[:3,3])
 actual=np.array(actual);T=L@F['hand_r_base_link'];P=T[:3,:3]@material+T[:3,3];H=f.H.inspect(h);rad=[]
 for part in parts:
  if part['link']=='link_0':rad.append(dict(body_component=part['index'],intersection_radius_m=convex_intersection_radius(palmV@T[:3,:3].T+T[:3,3],part['vertices'])))
 row=dict(index=index,phase=float(u),arm_q=seed[:7].tolist(),hand_q=h.tolist(),wrist_in_knife=L.tolist(),Index_contact_materials_link_m=currentM[:2].tolist(),object_world_translation_goal_m=seed[11:14].tolist()if a.allow_held_translation else [0.,0.,0.],palm_material_link_m=material.tolist(),palm_point_knife_m=P.tolist(),palm_position_error_m=float(np.linalg.norm(P-desired)),Thumb_cap_material_error_m=float(np.linalg.norm(actual[2]-points[2])),Index2_normal_error_m=float(abs(actual[0,0]-points[0,0])),Index4_normal_error_m=float(abs(actual[1,1]-points[1,1])),Index_rolling_delta_m=(actual[:2]-points[:2]).tolist(),self=H,palm_body_original_intersections=rad);rows.append(row);print(json.dumps(row),flush=True)
 if H or max(row['Thumb_cap_material_error_m'],row['Index2_normal_error_m'],row['Index4_normal_error_m'])>.0002 or not(-.0038-.00005<=actual[0,1]<=.0038+.00005 and -.0093-.00005<=actual[1,0]<=.0093+.00005) or row['palm_position_error_m']>(.00015 if index==8 else .0007) or max(r['intersection_radius_m']for r in rad)>.00001:failure='Original loaded palm contact/material/H constraint';break
out=dict(passed=len(rows)==9 and failure is None,failure=failure,source=str(a.source),rows=rows,original_actual_primary_bearings=C['keys'],palm_goal_knife_m=goal.tolist(),elapsed_s=time.monotonic()-began,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_loaded_palm_backup_planner_terminal_'+a.version,[str(a.output/'result.json')],dict(passed=out['passed'],failure=failure,poses=len(rows),elapsed_s=out['elapsed_s']),next_step='Valid originalpalm approach ->densemotor +ONE actualPalm normal bearing whileThumb/Middle load kept; newbody beforeindirectMiddle withdrawn, thenPAD/B/fresh');print(json.dumps({k:v for k,v in out.items()if k!='rows'}))
