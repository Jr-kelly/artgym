"""Coupled transfer using actual Pinky PAD backing before old Thumb retirement.

All seven arm joints and four bearing fingers cooperate. Old Index/Middle side
and new Pinky back contacts stay on finite original body patches; Thumb rolls
along its side toward the front corner. No imposed wrist angle or gain/pressure
grid. Original geometry/H/actuator limits remain. A path is only guidance and
needs native bearing/carry verification before advancing to roof and full B.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record
from scripts.wuji_original_contact_surface import OriginalContactSurface
from scipy.spatial.transform import Rotation

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v978');p.add_argument('--rolling-original-skin',action='store_true');p.add_argument('--cooperative-corner-roll',action='store_true');p.add_argument('--max-seconds',type=float,default=150.);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.loads((a.source/'manifest.json').read_text());trace=np.load(meta['source']);clock=float(trace['time'][meta['takeover_index']]);C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];cc=min(C,key=lambda r:abs(r['time_s']-clock))['contacts'];f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 q0=z['robot_q'].astype(float);h0=q0[7:];O=transform(z['object_state'][:3],z['object_state'][3:7]);L0=np.linalg.inv(O)@f.kin.forward(q0[:7]);names=['hand_r_index_link4','hand_r_middle_link4','hand_r_pinky_pad_link','hand_r_thumb_pad_link'];digits=['index','middle','pinky','thumb'];ids=np.r_[np.arange(12),np.arange(16,20)];M=[];P0=[];N=[];FN=[];mag=[]
 for n in names:
  sel=[c for c in cc if c['hand_link']==n and c['knife_link']=='link_0'];assert sel,n;w=np.array([c['normal_magnitude_N']for c in sel]);mag.append(float(w.sum()));w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in sel]);T=L0@g.w.forward(h0)[n];M.append(m);P0.append(T[:3,:3]@m+T[:3,3]);F=sum((np.array(c['force_normal_contribution_knife_N'])for c in sel),np.zeros(3));FN.append(F);N.append(F/np.linalg.norm(F))
 M=np.array(M);P0=np.array(P0);depth={}
 for d in digits:
  for c in g.gaps(h0,L0,float(z['slider_q']),d):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 lo=np.r_[f.kin.lower+.025,g.w.lower[ids]+.015];hi=np.r_[f.kin.upper-.025,g.w.upper[ids]-.015];prior=np.r_[q0[:7],h0[ids]];surfaces=[OriginalContactSurface(np.concatenate([v for v,norm in g.meshes[n]]))for n in names];material_start=len(prior)
 if a.rolling_original_skin:prior=np.r_[prior,np.zeros(12)];lo=np.r_[lo,[-.006]*12];hi=np.r_[hi,[.006]*12]
 # A centroid of several native contacts can lie inside a curved convex hull.
 # Surface guidance starts at the actual original surface, keeping its captured
 # penetration into the original knife rather than inventing zero penetration.
 native_centroid_materials=M.copy();native_centroid_points=P0.copy()
 if a.rolling_original_skin:
  M=np.array([s.project(m)for s,m in zip(surfaces,M)]);F0=g.w.forward(h0);P0=np.array([(L0@F0[n])[:3,:3]@m+(L0@F0[n])[:3,3]for n,m in zip(names,M)])
 rows=[];beg=time.monotonic();failure=None
 record('actual_four_bearing_side_front_geometry_started_'+a.version,[str(a.source)],dict(scope=__doc__,native_contact_names=names,source_material_points=M.tolist(),source_points_knife=P0.tolist(),original_measured_normal_budget_N=sum(mag)),next_step='One coupled finite-body contact path; originaldensecheck and inferredwrench then native actual rolling; no oldThumb release yet')
 def decode(x):
  h=h0.copy();h[ids]=x[7:material_start];return np.linalg.inv(O)@f.kin.forward(x[:7]),h
 def materials(x):
  return np.array([s.project(m+d)for s,m,d in zip(surfaces,M,x[material_start:].reshape(4,3))])if a.rolling_original_skin else M
 for i,u in enumerate(np.linspace(0,1,9)):
  previous=prior.copy();target=P0[3].copy();target[1]=P0[3,1]*(1-u)+.0039*u
  def residual(x):
   if time.monotonic()-beg>a.max_seconds:raise TimeoutError('Bounded four-bearing conversion')
   L,h=decode(x);F=g.w.forward(h);chosen=materials(x);P=np.array([(L@F[n])[:3,:3]@m+(L@F[n])[:3,3]for n,m in zip(names,chosen)]);r=[]
   for j in range(3):
    low=P0[j].copy();high=P0[j].copy();low[2]-=.005;high[2]+=.005
    if j<2:
     if a.cooperative_corner_roll:low[0]=high[0]=P0[j,0]-.004*u;low[1]=high[1]=P0[j,1]
     else:low[0]=high[0]=P0[j,0];low[1]=-.0039;high[1]=.0039
    else:low[1]=high[1]=P0[j,1];low[0]=-.0093;high[0]=.0093
    r.extend((P[j]-np.clip(P[j],low,high))*1000)
   r.extend((P[3]-target)*1000)
   if a.cooperative_corner_roll:
    desiredR=Rotation.from_euler('z',-15*u,degrees=True).as_matrix()@L0[:3,:3];r.extend(Rotation.from_matrix(desiredR.T@L[:3,:3]).as_rotvec()*8)
   for d in digits:
    r.extend(min(0.,c['gap_lower_bound_m']-depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))])*1400 for c in g.gaps(h,L,float(z['slider_q']),d,frames=F,certify_clearance_m=.0002))
   r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend((L[:3,3]-L0[:3,3])*2);r.extend((x-previous)*.025);return np.array(r)
  try:prior=previous if i==0 else least_squares(residual,previous,bounds=(lo,hi),max_nfev=50,diff_step=1e-5).x
  except TimeoutError as exc:failure=str(exc);break
  L,h=decode(prior);F=g.w.forward(h);chosen=materials(prior);P=np.array([(L@F[n])[:3,:3]@m+(L@F[n])[:3,3]for n,m in zip(names,chosen)]);bad=f.H.inspect(h);error=float(np.linalg.norm(P[3]-target));normal_error=float(max(abs(P[0,0]-P0[0,0]),abs(P[1,0]-P0[1,0]),abs(P[2,1]-P0[2,1])))
  if a.cooperative_corner_roll:normal_error=float(max(abs(P[0,1]-P0[0,1]),abs(P[1,1]-P0[1,1]),abs(P[2,1]-P0[2,1]),abs(P[0,0]-P0[0,0]+.004*u),abs(P[1,0]-P0[1,0]+.004*u)))
  finite=bool(np.all(abs(P[:2,1])<.00405)and abs(P[2,0])<.00955 and np.all(abs(P[:,2])<.0719));row=dict(index=i,fraction=float(u),arm_q=prior[:7].tolist(),hand_q=h.tolist(),wrist_in_knife=L.tolist(),contact_material_points=dict(zip(names,chosen.tolist())),contact_points_knife_m=P.tolist(),Thumb_side_target_m=target.tolist(),Thumb_target_error_m=error,retained_contact_normal_error_m=normal_error,finite_original_body_patches=finite,self=bad);rows.append(row);(a.output/'partial.json').write_text(json.dumps(dict(rows=rows,passed=False),indent=2));print(json.dumps({k:v for k,v in row.items()if k not in['contact_material_points','arm_q','hand_q','wrist_in_knife']}),flush=True)
  if error>.0003 or normal_error>.00025 or not finite or bad:failure='Original finite bearing/H/Thumb-side conversion';break
 passed=bool(failure is None and len(rows)==9);out=dict(passed=passed,failure=failure,source=str(a.source),rows=rows,names=names,material_points_link_m=M.tolist(),native_centroid_materials_link_m=native_centroid_materials.tolist(),native_centroid_points_knife_m=native_centroid_points.tolist(),source_points_knife_m=P0.tolist(),measured_normal_vectors_N=np.array(FN).tolist(),measured_normals_knife=np.array(N).tolist(),measured_normal_budget_N=sum(mag),elapsed_s=time.monotonic()-beg,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));(a.output/'planner.py').write_bytes(Path(__file__).read_bytes());record('actual_four_bearing_side_front_geometry_terminal_'+a.version,[str(a.output/'result.json')],dict(passed=passed,failure=failure,poses=len(rows),elapsed_s=out['elapsed_s'],last=rows[-1]),next_step='Originaldensemesh/H and conservednormalbudget gravitywrench then oneactualThumbside shift; no fixedangle or gain/pressure grid')
if __name__=='__main__':main()
