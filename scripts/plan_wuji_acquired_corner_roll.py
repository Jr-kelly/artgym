"""Short coupled intrinsic corner roll from the actual v877 bearing state.

Only geometric motor guidance: current three material contacts retained while
thumb slides on -X toward the front edge and I/M approach the back edge. This
is a short transition diagnostic, not a complete operating entry or B success.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--retain-source-contact-depth',action='store_true');p.add_argument('--extra-back-bearing',action='store_true');p.add_argument('--rolling-surfaces',action='store_true');p.add_argument('--angle-deg',type=float,default=15.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;O=transform(z['object_state'][:3],z['object_state'][3:7]);L0=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);names=['hand_r_index_link4','hand_r_middle_link4','hand_r_thumb_pad_link'];
 if a.extra_back_bearing:names.append('hand_r_ring_pad_link')
 manifest=json.loads((a.source/'manifest.json').read_text());history=Path(manifest['source']).parent/'wrap-contact-physical-steps.jsonl';contacts=json.loads(history.read_text().splitlines()[-1])['contacts'];materials=[];P0=[]
 for name in names:
  cc=[c for c in contacts if c['hand_link']==name];w=np.array([c['normal_magnitude_N']for c in cc]);w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in cc]);materials.append(m);T=L0@g.w.forward(h0)[name];P0.append(T[:3,:3]@m+T[:3,3])
 from scipy.spatial import ConvexHull
 hulls=[ConvexHull(np.concatenate([v for v,_ in g.meshes[n]]))for n in names]
 if a.rolling_surfaces and not a.retain_source_contact_depth:
  from scripts.g2_contact_geometry import DigitGeometry
  g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json',max_face_axes=8)
 ids=np.r_[np.arange(8),np.arange(12,20)] if a.extra_back_bearing else np.r_[np.arange(8),np.arange(16,20)];contact_start=6+len(ids);x0=np.r_[np.zeros(6),h0[ids]];lo=np.r_[[-.025]*3,[-.40]*3,g.w.lower[ids]+.03];hi=np.r_[[.025]*3,[.40]*3,g.w.upper[ids]-.03];
 if a.rolling_surfaces:
  x0=np.r_[x0,np.array(materials).ravel()];lo=np.r_[lo,np.concatenate([h.points.min(0)-.0002 for h in hulls])];hi=np.r_[hi,np.concatenate([h.points.max(0)+.0002 for h in hulls])]
 prior=x0.copy();arm=z['robot_q'][:7].astype(float);rows=[];began=time.monotonic();event_version='v894r1' if a.retain_source_contact_depth else 'v894' if a.extra_back_bearing else 'v883' if a.rolling_surfaces else 'v882';record('acquired_corner_roll_geometry_started_'+event_version,[str(a.source)],dict(scope=__doc__,angle_deg=a.angle_deg,material_points=[m.tolist()for m in materials]),next_step='Onecoupledshort15deg path, preservesall3bearing andmotorbounds; nofullA rerun')
 depth_baseline={}
 if a.retain_source_contact_depth:
  for digit in ['index','middle','thumb','ring']:
   for c in g.gaps(h0,L0,float(z['slider_q']),digit):depth_baseline[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 def lower_depth(c):return depth_baseline.get((c['hand_link'],c['knife_link'],c.get('knife_component',0)),-.00065)
 def decode(x):
  L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];h=h0.copy();h[ids]=x[6:contact_start];return L,h
 for i,u in enumerate(np.linspace(0,1,16)):
  target=np.array(P0);target[:,0]=[.0095,.0095,-.0095,.0095*(1-u)] if a.extra_back_bearing else [.0095,.0095,-.0095];target[:2,1]=(1-u)*target[:2,1]+u*(-.004);target[2,1]=(1-u)*target[2,1]+u*.004;target[:,2]=np.array(P0)[:,2]
  if a.extra_back_bearing:target[3,1]=-.004;rotation=Rotation.from_euler('z',-a.angle_deg*u,degrees=True).as_matrix();desiredR=rotation@L0[:3,:3]
  def residual(x):
   L,h=decode(x);F=g.w.forward(h);P=[]
   chosen=x[contact_start:].reshape(len(names),3) if a.rolling_surfaces else materials
   for name,m in zip(names,chosen):T=L@F[name];P.append(T[:3,:3]@m+T[:3,3])
   r=list((np.array(P)-target).ravel()*700);
   if a.rolling_surfaces:
    for hull,m in zip(hulls,chosen):
     eq=hull.equations[:,:3]@m+hull.equations[:,3];r.append(float(eq.max())*1500);r.extend(np.maximum(eq,0)*1500)
   r.extend(Rotation.from_matrix(desiredR.T@L[:3,:3]).as_rotvec()*15)
   for digit in (['index','middle','thumb','ring'] if a.extra_back_bearing else ['index','middle','thumb']):
    r.extend(min(0.,c['gap_lower_bound_m']-lower_depth(c))*1500 for c in g.gaps(h,L,float(z['slider_q']),digit,frames=F,certify_clearance_m=.0002))
   r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1500 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend(x[:3]*5);r.extend((x-prior)*.04);return np.array(r)

  if i==0 and a.retain_source_contact_depth:
   class Fit:pass
   fit=Fit();fit.x=prior.copy()
  else:fit=least_squares(residual,np.clip(prior,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=35,diff_step=1e-5)
  L,h=decode(fit.x);F=g.w.forward(h);chosen=fit.x[contact_start:].reshape(len(names),3) if a.rolling_surfaces else materials;P=np.array([(L@F[n])[:3,:3]@m+(L@F[n])[:3,3]for n,m in zip(names,chosen)]);err=float(np.linalg.norm(P-target,axis=1).max());rot=float(np.linalg.norm(Rotation.from_matrix(desiredR.T@L[:3,:3]).as_rotvec()));arm,ik=f.kin.solve_near(O@L,arm,max_step=.15,minimum_margin=.06);bad=f.H.inspect(h);gaps=[c['gap_lower_bound_m']for digit in (['index','middle','thumb','ring'] if a.extra_back_bearing else ['index','middle','thumb'])for c in g.gaps(h,L,float(z['slider_q']),digit)];row=dict(contact_material_points=dict(zip(names,[m.tolist() for m in chosen])),index=i,fraction=float(u),wrist_in_knife=L.tolist(),hand_q=h.tolist(),arm_q=arm.tolist(),contact_target_knife_m=target.tolist(),contact_error_m=err,orientation_error_rad=rot,arm_IK=ik,self=bad,min_knife_gap_m=min(gaps));rows.append(row);print(json.dumps(row),flush=True);prior=fit.x;(a.output/'partial.json').write_text(json.dumps(dict(rows=rows,geometry_pass=False),indent=2))
  if err>.0007 or rot>.015 or bad or ik['position_m']>.0003 or ik['rotation_rad']>.003:break
 passed=len(rows)==16 and rows[-1]['fraction']==1 and not rows[-1]['self']and rows[-1]['contact_error_m']<.0007 and rows[-1]['orientation_error_rad']<.015 and rows[-1]['arm_IK']['position_m']<.0003 and rows[-1]['arm_IK']['rotation_rad']<.003;result=dict(rows=rows,geometry_pass=bool(passed),scope=__doc__,source=str(a.source),material_points=dict(zip(names,[m.tolist()for m in materials])),initial_issued=issued.tolist(),elapsed_s=time.monotonic()-began);(a.output/'result.json').write_text(json.dumps(result,indent=2));record('acquired_corner_roll_geometry_terminal_'+event_version,[str(a.output/'result.json')],dict(passed=bool(passed),poses=len(rows),last=rows[-1],elapsed_s=result['elapsed_s']),next_step='Ifshortpathclear actualshortrestore; ifgeometricbearingblocked changewholegriptransition once, nofollower/gainscan')
if __name__=='__main__':main()
