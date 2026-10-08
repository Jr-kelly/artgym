"""Coordinated new back bearing with retained old opposition and free wrist pose.

No prescribed roll angle, fixed material locations or additional pressure.
Old contacts can roll and slide axially; the ring pad must reach the actual back
face before the old clamp can retire. Geometry alone is not physical load proof.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--whole-patch-clearance',action='store_true');p.add_argument('--resume-geometry',type=Path);p.add_argument('--max-wall-seconds',type=float,default=240.);p.add_argument('--around-corner',action='store_true');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');f=FunctionalEntryAffordance();g=f.g;normal_counts_before=sum(len(n)for meshes in g.meshes.values()for _,n in meshes)
 for name,meshes in g.meshes.items():g.meshes[name]=[(v,np.unique(n,axis=0))for v,n in meshes]
 normal_counts_after=sum(len(n)for meshes in g.meshes.values()for _,n in meshes);h0=z['robot_q'][7:].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);L0=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);manifest=json.loads((a.source/'manifest.json').read_text());cc=json.loads((Path(manifest['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()[-1])['contacts'];names=['hand_r_index_link4','hand_r_middle_link4','hand_r_thumb_pad_link'];materials=[];P0=[];hulls=[]
 for name in names:
  selected=[c for c in cc if c['hand_link']==name];w=np.array([c['normal_magnitude_N']for c in selected]);w/=w.sum();m=w@np.array([c['position_hand_link_m']for c in selected]);materials.append(m);T=L0@g.w.forward(h0)[name];P0.append(T[:3,:3]@m+T[:3,3]);hulls.append(ConvexHull(np.concatenate([v for v,_ in g.meshes[name]])))
 ring='hand_r_ring_pad_link';V=np.concatenate([v for v,_ in g.meshes[ring]])
 def ring_vertices(L,h):
  T=L@g.w.forward(h)[ring];return V@T[:3,:3].T+T[:3,3]
 def ring_foot(L,h):
  P=ring_vertices(L,h);w=np.exp((P[:,1]-P[:,1].max())/.0002);return w@P/w.sum()
 first=ring_foot(L0,h0);first_vertices=ring_vertices(L0,h0);goal=np.clip(first,[-.006,-.004,-.065],[.006,-.004,-.025]);
 if a.around_corner:goal[1]=-.0042
 if a.whole_patch_clearance:goal[1]=-.0044
 retreat=first.copy();retreat[0]+=.0145-first_vertices[:,0].min();back_corner=retreat.copy();back_corner[1]=-.0094;back_inside=goal.copy();back_inside[1]=-.0094
 corner=np.array([max(first[0]+.0005,.0102),-.0044,first[2]]);ids=np.r_[np.arange(8),np.arange(12,20)];x0=np.r_[np.zeros(6),h0[ids],np.array(materials).ravel()];low=np.r_[[-.035]*3,[-.60]*3,g.w.lower[ids]+.025,np.concatenate([H.points.min(0)-.0002 for H in hulls])];high=np.r_[[.035]*3,[.60]*3,g.w.upper[ids]-.025,np.concatenate([H.points.max(0)+.0002 for H in hulls])];depth={};P0=np.array(P0)
 for digit in ['index','middle','thumb','ring']:
  for c in g.gaps(h0,L0,float(z['slider_q']),digit):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 def decode(x):
  L=L0.copy();L[:3,3]+=x[:3];L[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@L0[:3,:3];h=h0.copy();h[ids]=x[6:22];return L,h,x[22:].reshape(3,3)
 prior=x0.copy();rows=[];arm=z['robot_q'][:7].astype(float)
 if a.resume_geometry:
  old=json.loads(a.resume_geometry.read_text());assert old['source']==str(a.source);rows=old['rows'];last=rows[-1];L=np.array(last['wrist_in_knife']);h=np.array(last['hand_q']);M=np.array([last['contact_material_points'][n]for n in names]);prior=np.r_[L[:3,3]-L0[:3,3],Rotation.from_matrix(L[:3,:3]@L0[:3,:3].T).as_rotvec(),h[ids],M.ravel()];arm=np.array(last['arm_q'])
 start=time.monotonic();failure=None;version='v899' if a.whole_patch_clearance else 'v896' if a.around_corner else 'v895';record('coordinated_new_back_bearing_geometry_started_'+version,[str(a.source)],dict(scope=__doc__,initial_ring_foot=first.tolist(),resume_geometry=str(a.resume_geometry)if a.resume_geometry else None,reused_poses=len(rows),exact_normal_deduplication=dict(before=normal_counts_before,after=normal_counts_after),goal_ring_region=[[-.006,-.004,-.065],[.006,-.004,-.025]],wrist_freedom='3translation/3rotation, originalarmreachability',old_bearing='oppositionX retained, Ywithinbody andaxialmigration±12mm, contactpoint rolls onsameoriginalhull'),next_step='Truebackbearing first withwholegripmotion; nativechecksload beforeanyoldThumbrelease, no fixedturnangle')
 count=17 if a.around_corner or a.whole_patch_clearance else 13
 for index,u in enumerate(np.linspace(0,1,count)):
  if index<len(rows):continue
  if a.whole_patch_clearance:
   anchors=[first,retreat,back_corner,back_inside,goal];stage=min(3,index//4);local=(index-stage*4)/4;wanted=anchors[stage]*(1-local)+anchors[stage+1]*local;phase=['withdraw-whole-pad','clear-whole-back-corner','enter-back-face','acquire-back-face'][stage]
  elif a.around_corner:
   local=index/8 if index<=8 else (index-8)/8;wanted=first*(1-local)+corner*local if index<=8 else corner*(1-local)+goal*local
   assert wanted[0]>=.0095 or wanted[1]<=-.004,'Ringapproach crossesknifevolume'
  else:wanted=first*(1-u)+goal*u
  def residual(x):
   if time.monotonic()-start>a.max_wall_seconds:raise TimeoutError('Boundedwholegripbearingpath walltime reached')
   L,h,M=decode(x);F=g.w.forward(h);r=[]
   for j,(name,m,H)in enumerate(zip(names,M,hulls)):
    T=L@F[name];P=T[:3,:3]@m+T[:3,3];lo=np.array([(.0095 if j<2 else-.0095),-.004,P0[j,2]-.012]);hi=np.array([lo[0],.004,P0[j,2]+.012]);r.extend((P-np.clip(P,lo,hi))*800);eq=H.equations[:,:3]@m+H.equations[:,3];r.append(float(eq.max())*1000);r.extend(np.maximum(eq,0)*1000)
   P=ring_foot(L,h);r.extend((P-wanted)*800)
   if a.whole_patch_clearance:
    vertices=ring_vertices(L,h)
    if phase=='withdraw-whole-pad':r.append(min(0.,vertices[:,0].min()-(first_vertices[:,0].min()+min(index/4,1)*(.0145-first_vertices[:,0].min())))*1400)
    elif phase=='clear-whole-back-corner':r.append(min(0.,vertices[:,0].min()-.0145)*1400)
    elif phase=='enter-back-face':r.append(max(0.,vertices[:,1].max()+.009)*1400)
    else:r.append(max(0.,vertices[:,1].max()+.0042)*1400)
   for digit in ['index','middle','thumb','ring']:
    for c in g.gaps(h,L,float(z['slider_q']),digit,frames=F,certify_clearance_m=.0002):r.append(min(0.,c['gap_lower_bound_m']-depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))])*1400)
   r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend(x[:3]*3);r.extend(x[3:6]*.1);r.extend((x-prior)*.02);return np.array(r)
  try:
   x=prior.copy() if index==0 else least_squares(residual,np.clip(prior,low+1e-7,high-1e-7),bounds=(low,high),max_nfev=40,diff_step=1e-5).x
  except TimeoutError as exc:failure=str(exc);break
  L,h,M=decode(x);actual=ring_foot(L,h);error=float(np.linalg.norm(actual-wanted));arm,ik=f.kin.solve_near(O@L,arm,max_step=.15,minimum_margin=.06);bad=f.H.inspect(h);row=dict(phase=phase if a.whole_patch_clearance else 'clear-side-to-back-corner' if a.around_corner and index<=8 else 'enter-back-face' if a.around_corner else 'straight-approach',index=index,fraction=float(u),wrist_in_knife=L.tolist(),arm_q=arm.tolist(),hand_q=h.tolist(),ring_foot_knife_m=actual.tolist(),ring_target_knife_m=wanted.tolist(),ring_error_m=error,ring_pad_bounds_knife_m=[ring_vertices(L,h).min(0).tolist(),ring_vertices(L,h).max(0).tolist()],contact_material_points=dict(zip(names,[m.tolist()for m in M])),arm_IK=ik,self=bad);rows.append(row);prior=x;(a.output/'partial.json').write_text(json.dumps(dict(rows=rows,geometry_pass=False),indent=2));print(json.dumps(row),flush=True)
  if error>.0007 or bad or ik['position_m']>.0003 or ik['rotation_rad']>.003:break
 passed=len(rows)==count and rows[-1]['fraction']==1 and rows[-1]['ring_error_m']<.0007 and not rows[-1]['self']and rows[-1]['arm_IK']['position_m']<.0003 and rows[-1]['arm_IK']['rotation_rad']<.003;out=dict(rows=rows,geometry_pass=bool(passed),source=str(a.source),initial_issued=z['issued_target'].tolist(),failure=failure,elapsed_s=time.monotonic()-start,scope=__doc__);(a.output/'result.json').write_text(json.dumps(out,indent=2));record('coordinated_new_back_bearing_geometry_terminal_'+version,[str(a.output/'result.json')],dict(passed=bool(passed),poses=len(rows),failure=failure,last=rows[-1]if rows else None),next_step='Sourceconsistenttrueback-bearing guide ->nativewholegripshort load proof; blockedchangecontactmode, no pressure/timinggrid')
if __name__=='__main__':main()
