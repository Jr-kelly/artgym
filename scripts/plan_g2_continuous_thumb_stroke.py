"""Offline continuous rolling-pad IK, preserving original collision/limit checks.

Uses an initial calibrated grasp and endpoint hypothesis. No physics or force
claim. Hard per-knot joint-change bounds prevent a point-valid IK branch jump.
"""
import argparse,json,hashlib
from types import SimpleNamespace
from functools import lru_cache
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--knife-spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--joint-step',type=float,default=.04);p.add_argument('--motor-anchor-plan',type=Path,help='Certified acquisition motor plan; constrain actualinitial+reference-offset targets to originallimits andthumb selfclearance');p.add_argument('--support-motor-corridor',type=Path,help='Knownoffline supportmotorbounds; constrainthumb trajectory atbothmiddlejoint endpoints, no livecontact/object input');p.add_argument('--facing-mode',choices=['nominal-x','supporting-hull'],default='nominal-x',help='Supporting-hull checks outward normals ofactualpadfacets within0.4mm ofthecontactsupportplane; no physical geometry changes');p.add_argument('--facing-floor',type=float,default=.25,help='Geometric padnormal cosine floor; may use independently observed successful contactorientation, never change physicalcollisions');p.add_argument('--refine-initial-contact',action='store_true',help='Refine loaded measured q to a geometry-only zero-force slider-top touch before path fitting; no physical state or runtime target jump');p.add_argument('--contact-patch',action='store_true',help='Use authored slider top lateral interval with0.5mm inset,0.15mm normal and0.5mm axial centroid tolerance; preserve all collision/limits/40mm command');p.add_argument('--joint-margin',type=float,default=.08,help='Offline thumb engineering reserve within unchanged URDF limits; minimum .005rad, original default .08');p.add_argument('--thumb-base-margin',type=float,default=.08,help='Geometric reserve for original thumb base-joint limit; no motor-limit change');a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise FileExistsError(a.output)
 assert .005<=a.joint_margin<=.20 and .005<=a.thumb_base_margin<=.30
 j=json.loads(a.plan.read_text());g=DigitGeometry(knife_spec=a.knife_spec);h=g.w;w=np.array(j['wrist_in_knife']);q0=np.array(j['touch_q']);n=np.array(j['contact_normals'][0]);end=np.array(j['stroke_endpoint']['thumb_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);rows=[];previous=q0[16:].copy()
 assert a.facing_mode!='supporting-hull' or len(g.meshes['hand_r_thumb_pad_link'])==1
 pad_hull=ConvexHull(v);pad_facet_centers=v[pad_hull.simplices].mean(1);pad_facet_normals=pad_hull.equations[:,:3]
 fixed=h.forward(q0);others=[]
 for link,meshes in g.meshes.items():
  if any('_'+f+'_' in link for f in ['index','middle','ring','pinky']):
   t=fixed[link]
   for vertices,axes in meshes:
    vertices=vertices@t[:3,:3].T+t[:3,3];center=vertices.mean(0);others.append((vertices,axes@t[:3,:3].T,center,float(np.linalg.norm(vertices-center,axis=1).max())))
 parts={float(shift):g.knife_geometry.collision_parts(j['planning_slider_m']+float(shift)) for shift in np.linspace(0,.04,41)}
 @lru_cache(maxsize=2048)
 def sample(values,shift):
  q=q0.copy();q[16:]=values;frames=h.forward(q);t=w@frames['hand_r_thumb_pad_link'];points=v@t[:3,:3].T+t[:3,3];proj=points@n;weight=np.exp(-(proj-proj.min())/.0002);weight/=weight.sum();point=weight@points;facing=float(t[:3,0]@(-n));knife=np.inf;selfgap=np.inf
  if a.facing_mode=='supporting-hull':
   facet_projection=(pad_facet_centers@t[:3,:3].T+t[:3,3])@n;supporting=facet_projection<=proj.min()+.0004
   facing=float((pad_facet_normals@t[:3,:3].T@(-n))[supporting].max()) if supporting.any() else -1.
  for link,meshes in g.meshes.items():
   if '_thumb_' not in link:continue
   for vertices,axes in meshes:
    fk=frames[link];vh=vertices@fk[:3,:3].T+fk[:3,3];nh=axes@fk[:3,:3].T;center=vh.mean(0);radius=float(np.linalg.norm(vh-center,axis=1).max());vo=vh@w[:3,:3].T+w[:3,3];no=nh@w[:3,:3].T
    for part in parts[shift]:
     ax=np.r_[no,part['normals']];pa=vo@ax.T;pb=part['vertices']@ax.T;knife=min(knife,float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()))
    for vb,nb,cb,rb in others:
     gap=float(np.linalg.norm(center-cb)-radius-rb)
     if gap<=.000015:
      ax=np.r_[nh,nb];pa=vh@ax.T;pb=vb@ax.T;gap=float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
     selfgap=min(selfgap,gap)
  return point,facing,knife,selfgap
 def evaluate(x,shift):return sample(tuple(x),float(shift))
 start=evaluate(previous,0.)[0].copy()
 patch_x_center=float(g.knife_geometry.joint_xyz[0])
 assert not a.contact_patch or np.allclose(abs(n),[0,1,0]),'Patch mode currently uses authored y-normal slider top'
 base_lower=h.lower[16:]+a.joint_margin;base_upper=h.upper[16:]-a.joint_margin
 base_lower[0]=h.lower[16]+a.thumb_base_margin;base_upper[0]=h.upper[16]-a.thumb_base_margin
 if a.thumb_base_margin>.08 or a.refine_initial_contact or j.get('operating_contact_point_knife_m'):
  old=previous.copy()
  if j.get('operating_contact_point_knife_m'):start=np.array(j['operating_contact_point_knife_m'])
  if a.refine_initial_contact:
   assert a.contact_patch,'Surface refinement uses declared finite contactpatch'
   slider_parts=[part for part in parts[0.] if part['link']=='link_1']
   pad_frame=w@h.forward(q0)['hand_r_thumb_pad_link']
   pad_vertices=v@pad_frame[:3,:3].T+pad_frame[:3,3]
   # Lift the lowest collision vertex above the slider top. The soft
   # contact centroid can already be above it while the hull intersects.
   start[1]+=max(0.,max(float(part['vertices'][:,1].max()) for part in slider_parts)+.00005-float(pad_vertices[:,1].min()))
   start[0]=np.clip(start[0],patch_x_center-.0045,patch_x_center+.0045)
  def initial_constraints(x):
   point,facing,knife,selfgap=evaluate(x,0.)
   contact=np.array([.0001-np.linalg.norm(point-start)])
   if a.contact_patch:contact=np.array([.0045-abs(point[0]-patch_x_center),.00015-abs(point[1]-start[1]),.0005-abs(point[2]-start[2])])
   return np.r_[contact*1000,facing-a.facing_floor,(knife-.000005)*1000,(selfgap-.000015)*1000]
  initial=minimize(lambda x:float(np.sum(((evaluate(x,0.)[0]-start)*250)**2)+.05*np.sum((x-old)**2)),np.clip(old,base_lower,base_upper),method='SLSQP',bounds=list(zip(base_lower,base_upper)),constraints=[dict(type='ineq',fun=initial_constraints)],options=dict(maxiter=160,ftol=1e-11))
  initial_audit=dict(old_thumb_q=old.tolist(),candidate_thumb_q=initial.x.tolist(),requested_base_margin_rad=a.thumb_base_margin,optimizer_success=bool(initial.success),minimum_constraint=float(initial_constraints(initial.x).min()),initial_constraint_values=initial_constraints(old).tolist(),final_constraint_values=initial_constraints(initial.x).tolist(),constraint_order=['patch_lateral_mm','patch_normal_mm','patch_axial_mm','facing_cosine_margin','knife_separation_mm','self_separation_mm'] if a.contact_patch else ['point_error_mm','facing_cosine_margin','knife_separation_mm','self_separation_mm'],message=initial.message,scope='Geometry-only pressure-headroom hypothesis; no force or physics evidence')
  a.output.with_suffix('.initial-audit.json').write_text(json.dumps(initial_audit,indent=2));print(json.dumps(initial_audit),flush=True)
  assert initial_constraints(initial.x).min()>=-1e-4,'Rejected initial posture; do not execute'
  previous=initial.x;q0[16:]=previous;j['touch_q']=q0.tolist()
  a.output.with_suffix('.plan.json').write_text(json.dumps(j,indent=2))
  start=evaluate(previous,0.)[0].copy()
 motor_anchor=json.loads(a.motor_anchor_plan.read_text()) if a.motor_anchor_plan else None
 motor_geometry=DigitGeometry(max_face_axes=10000,knife_spec=a.knife_spec) if motor_anchor else None
 anchor_offset=np.array(motor_anchor['close_q'])[16:]-q0[16:] if motor_anchor else None
 support_corridor=json.loads(a.support_motor_corridor.read_text()) if a.support_motor_corridor else None
 if support_corridor:assert motor_anchor and support_corridor['hand_index']==7
 def motor_self_constraints(x):
  full=np.array(motor_anchor['close_q']);full[16:]=x+anchor_offset;values=[]
  support_positions=support_corridor['motor_bounds_rad'] if support_corridor else [full[7]]
  for support_position in support_positions:
   full[7]=support_position
   values.extend(r['gap_lower_bound_m']-.000015 for r in motor_geometry.self_gaps(full,'thumb',certify_clearance_m=.000015)+motor_geometry.pair_gaps(full,[('hand_r_thumb_pad_link','hand_r_base_link'),('hand_r_thumb_link4','hand_r_base_link')]))
  return np.array(values)*1000
 for shift in np.linspace(0,.04,41):
  desired=start+np.array([0.,0.,shift]);reference=q0[16:]*(1-shift/.04)+end*(shift/.04);prior=previous.copy();lo=np.maximum(base_lower,prior-a.joint_step);hi=np.minimum(base_upper,prior+a.joint_step)
  if motor_anchor:
   lo=np.maximum(lo,h.lower[16:]+.005-anchor_offset);hi=np.minimum(hi,h.upper[16:]-.005-anchor_offset)
  assert np.all(lo<=hi),'No originalmotor/geometry bounds overlap'
  def objective(x):
   point,*_=evaluate(x,shift);return float(((point-desired)*250)**2@np.ones(3)+.05*np.sum((x-reference)**2))
  def constraints(x):
   point,facing,knife,selfgap=evaluate(x,shift)
   contact=(.0001-np.linalg.norm(point-desired))*np.ones(1)
   if a.contact_patch:contact=np.array([.0045-abs(point[0]-patch_x_center),.00015-abs(point[1]-desired[1]),.0005-abs(point[2]-desired[2])])
   return np.r_[contact*1000,facing-a.facing_floor,(knife-.000005)*1000,(selfgap-.000015)*1000,motor_self_constraints(x) if motor_anchor else []]
  fit=SimpleNamespace(x=q0[16:].copy(),success=True,message='Fixed initialknownmotor anchor, geometry checked') if motor_anchor and shift==0 else minimize(objective,np.clip(reference,lo,hi),method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=160,ftol=1e-11));point,facing,knife,selfgap=evaluate(fit.x,shift);ok=bool(constraints(fit.x).min()>=-1e-4);rows.append(dict(shift_m=float(shift),q_thumb=fit.x.tolist(),point_error_m=float(np.linalg.norm(point-desired)),pad_facing_cosine=facing,minimum_knife_gap_m=knife,minimum_self_gap_m=selfgap,maximum_joint_step_rad=float(abs(fit.x-prior).max()),constraint_values=constraints(fit.x).tolist(),contact_point_knife_m=point.tolist(),feasible=ok,optimizer_success=bool(fit.success),message=fit.message));previous=fit.x
  with a.output.with_suffix('.knots.jsonl').open('a') as stream:stream.write(json.dumps(rows[-1])+'\n')
  if len(rows)%5==0:print(json.dumps(dict(knots=len(rows),shift_m=float(shift),feasible=ok)),flush=True)
  if not ok:break
 result=dict(source=str(a.plan),support_motor_corridor=support_corridor,support_motor_corridor_sha256=hashlib.sha256(a.support_motor_corridor.read_bytes()).hexdigest() if a.support_motor_corridor else None,scope='Offline continuous rolling-pad IK hypothesis; measured pressure, servo tracking and physics remain unverified',rows=rows,joint_step_rad=a.joint_step,motor_anchor_plan=str(a.motor_anchor_plan) if a.motor_anchor_plan else None,final_motor_limits_and_self_constrained=bool(motor_anchor),pad_facing_floor=a.facing_floor,facing_mode=a.facing_mode,facing_scope='Actualsupportingcollisionhullfacetnormal within0.4mmcontactplane' if a.facing_mode=='supporting-hull' else 'Nominalpadlocal+xaxisheuristic',known_motor_anchor=bool(j.get('offline_measured_operation_only')),initial_surface_refined=a.refine_initial_contact,contact_patch_mode=a.contact_patch,contact_patch_scope='Authored nominal10mm slider top,0.5mm lateral inset; centroid normal tolerance0.15mm,axial0.5mm. Still original40mm command and allcollisions/limits; not real contact calibration' if a.contact_patch else 'Original100um fixed centroid',engineering_joint_margin_rad=a.joint_margin,engineering_thumb_base_margin_rad=a.thumb_base_margin,all_feasible=bool(len(rows)==41 and all(r['feasible'] for r in rows)),target_travel_m=.04,travel_seconds=4.,hold_seconds=1.);a.output.write_text(json.dumps(result,indent=2));print(json.dumps(dict(all_feasible=result['all_feasible'],knots=len(rows),last=rows[-1])));assert result['all_feasible'],'Do not execute an incomplete/rejected trajectory'
if __name__=='__main__':main()
