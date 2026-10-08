"""Native capacity probe of the closest safe original Palm approach.

A fixed Palm point reference remains unmet: do not relabel its geometry success.
All old finite body patches, original Index hull contact patches, Thumb cap bearing,
Thumb/Middle self-support geometry and actuator limits are checked instead.
Only actual native Palm/body load plus sustained carrying and H can establish
new bearing. Original PD/effort/mass/friction/brake/B remain unchanged.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_exact_knife_intersection import exact_hand_knife_intersection,convex_intersection_radius
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record
p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v973');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.load(open(a.geometry));cal=json.load(open(a.calibration));assert geo['source']==cal['source'];src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();g=f.g
for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
actual=z['robot_q'].astype(float);issued=z['issued_target'].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);invO=np.linalg.inv(O);L0=invO@f.kin.forward(actual[:7]);kp=np.array(json.load(open('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json'))['direct_pickup']['hand_kp']);armkp=np.array([j['stiffness']for j in json.load(open('assets/robots/g2_wuji/audit.json'))['active_arm']]);M=np.array(cal['material_points_link_m']);F=np.array(cal['allocated_total_force_proxies_N']);keys=cal['keys'];path=geo['rows'];skinE=[ConvexHull(g.meshes[n][0][0]).equations for n,k in keys[:2]];faces=[int(np.argmax(E[:,:3]@m+E[:,3]))for E,m in zip(skinE,M[:2])];levels=[float((E[:,:3]@m+E[:,3])[j])for E,m,j in zip(skinE,M[:2],faces)];cert=[];failure=None
record('actual_loaded_palm_capacity_precheck_started_'+a.version,[str(a.geometry),str(a.calibration)],dict(scope=__doc__,geometry_fixed_point_pass=geo['passed'],fixed_point_error_m=path[-1]['palm_position_error_m'],old_Thumb_Middle_issued_targets='exact unchanged',old_original_normal_budget_N=cal['measured_normal_budget_N']),next_step='Originaldense real bodypatch/skin/H ->one actualPALM normal capacity, no geometrygoal relaxation success')
for seg,(A,B)in enumerate(zip(path[:-1],path[1:])):
 qa=np.r_[A['arm_q'],A['hand_q']];qb=np.r_[B['arm_q'],B['hand_q']];ta=np.array(A.get('object_world_translation_goal_m',[0,0,0]));tb=np.array(B.get('object_world_translation_goal_m',[0,0,0]));ma=np.array(A.get('Index_contact_materials_link_m',M[:2]));mb=np.array(B.get('Index_contact_materials_link_m',M[:2]));count=max(2,int(np.ceil(abs(qb-qa).max()/.008))+1)
 for u in np.linspace(0,1,count):
  q=qa*(1-u)+qb*u;h=q[7:];plannedO=O.copy();plannedO[:3,3]+=ta*(1-u)+tb*u;L=np.linalg.inv(plannedO)@f.kin.forward(q[:7]);frames=g.w.forward(h);H=f.H.inspect(h);bad=[];m=ma*(1-u)+mb*u;points=[];skin=[]
  for j,(n,k)in enumerate(keys[:2]):
   T=L@frames[n];points.append(T[:3,:3]@m[j]+T[:3,3]);v=skinE[j][:,:3]@m[j]+skinE[j][:,3];skin.append(dict(max_original_halfplane_m=float(v.max()),source_skin_face_error_m=float(abs(v[faces[j]]-levels[j]))))
  for c in g.gaps(h,L,float(z['slider_q']),'thumb',frames=frames,certify_clearance_m=.0002):
   allowed=c['knife_link']=='link_1'and c['knife_component']==0 and c['hand_link']in['hand_r_thumb_link4','hand_r_thumb_pad_link'];limit=-.00029 if allowed else -.00001
   if c['gap_lower_bound_m']<limit:
    exact=exact_hand_knife_intersection(g,h,L,float(z['slider_q']),c)
    if not exact['no_intersection']:bad.append(dict(collision=c,exact=exact))
  T=L@frames['hand_r_base_link'];radii=[convex_intersection_radius(v@T[:3,:3].T+T[:3,3],p['vertices'])for v,n in g.meshes['hand_r_base_link']for p in g.knife_geometry.collision_parts(float(z['slider_q']))if p['link']=='link_0'];entry=dict(segment=seg,fraction=float(u),self=H,Thumb_knife_violations=bad,Index_body_points_m=np.array(points).tolist(),Index_original_skin=skin,old_single_face_error_scope='Diagnostic only: contact may migrate to another original facet. Native normals/carry must certify loaded contact.',palm_body_max_intersection_radius_m=max(radii));cert.append(entry)
  # Original contact patches are finite. They may roll, but cannot leave body.
  validpatch=-.00405<=points[0][1]<=.00405 and -.00955<=points[1][0]<=.00955 and all(abs(p[2])<.0719 for p in points)
  if H or bad or not validpatch or any(r['max_original_halfplane_m']>.000004 for r in skin) or max(radii)>.00001:failure='Original dense loaded Palm/oldbodypatch/skin/H constraint';break
 if failure:break

def jac(L,h,name,m,ids):
 J=np.empty((3,len(ids)))
 for j,c in enumerate(ids):
  up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@g.w.forward(up)[name];B=L@g.w.forward(down)[name];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
 return J
residual=kp[:4]*(issued[7:11]-actual[7:11])-sum((jac(L0,actual[7:],keys[j][0],M[j],np.arange(4)).T@F[j]for j in range(2)),np.zeros(4));rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,.3]];clock=.3;previous=issued.copy();motor_audit=[]
if not failure:
 for index,row in enumerate(path):
  h=np.array(row['hand_q']);L=np.array(row['wrist_in_knife']);m=np.array(row.get('Index_contact_materials_link_m',M[:2]));motor=issued[7:].copy();motor[:4]=h[:4]+(sum((jac(L,h,keys[j][0],m[j],np.arange(4)).T@F[j]for j in range(2)),np.zeros(4))+residual)/kp[:4];arm=np.array(row['arm_q'])+issued[:7]-actual[:7];q=np.r_[arm,motor];margin=float(np.minimum(q-np.r_[f.kin.lower,g.w.lower],np.r_[f.kin.upper,g.w.upper]-q).min());motor_audit.append(dict(index=index,minimum_original_command_margin_rad=margin));
  if margin<=0:failure='Original motor target limit';break
  assert np.array_equal(motor[4:],issued[11:]);clock+=max(1,int(np.ceil(max(abs(q[:7]-previous[:7]).max()/.004,abs(q[7:]-previous[7:]).max()/.012))))/30.;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist()));previous=q
passed=failure is None;out=dict(precheck_passed=passed,failure=failure,source=str(src),fixed_Palm_point_reference_passed=geo['passed'],fixed_point_error_m=path[-1]['palm_position_error_m'],actual_Palm_bearing_validated=False,seconds=clock+2.,geometry_certificates=cert,motor_audit=motor_audit,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
if passed:
 rows.append(dict(rows[-1],time_s=clock+2.));(a.output/'motor.json').write_text(json.dumps(dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.015,scope=__doc__),indent=2))
record('actual_loaded_palm_capacity_precheck_terminal_'+a.version,[str(a.output/'precheck.json')],dict(precheck_passed=passed,failure=failure,dense_samples=len(cert),seconds=clock+2.,fixed_point_reference_still_passed=geo['passed'],actual_Palm_bearing_validated=False),next_step='One native Palm/body normal beforeMiddle selfload withdrawal, actualH/carry, thenPAD/fullB30/fresh afterrealbearing');print(json.dumps({k:v for k,v in out.items()if k not in['geometry_certificates','motor_audit']}))
