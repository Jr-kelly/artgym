"""Side-corner roll then front-face slide, retaining actual bearing sites.
Geometry-only motor prior. Actual original physics must verify carrying and B.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,default=Path('runs/flat-table-20261006/direct/recorded/regrasp-v746-actual-3p5-v748'));p.add_argument('--axial-first',action='store_true');p.add_argument('--coupled-wrist',action='store_true');p.add_argument('--sliding-bearing',action='store_true');p.add_argument('--functional-thumb-seed',action='store_true');p.add_argument('--reserve-acquired-preload',action='store_true');p.add_argument('--diagonal-approach',action='store_true');p.add_argument('--resume-geometry',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);began=time.monotonic()
 src=a.source;z=np.load(src/'takeover.npz');g=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json',max_face_axes=32);full=DigitGeometry(knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');q=z['robot_q'][7:].astype(float);k=G2Kinematics();O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@k.forward(z['robot_q'][:7]);slider=float(z['slider_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']]);H=HandIntersection()
 def foot(cur,n):
  f=L@g.w.forward(cur)['hand_r_thumb_pad_link'];points=v@f[:3,:3].T+f[:3,3];projections=points@n;w=np.exp(-(projections-projections.min())/.0002);return w@points/w.sum()
 n0=np.array([-.964,.264,0.]);n0/=np.linalg.norm(n0);initial=foot(q,n0);corner=np.array([-.00952,.00402,initial[2]]);points=[]
 # Rotate the contact normal while retaining the corner, then move the
 # contact across the top body face before approaching the raised slider.
 for u in np.linspace(0,1,26):
  theta=np.arctan2(n0[1],-n0[0])+(np.pi/2-np.arctan2(n0[1],-n0[0]))*u;n=np.array([-np.cos(theta),np.sin(theta),0]);points.append((initial*(1-u)+corner*u,n,'corner-roll'))
 if not a.diagonal_approach:
  for u in np.linspace(0,1,21)[1:]:points.append((corner+np.array([.00952*u,0,0]),np.array([0.,1.,0.]),'top-centre'))
 top=np.array([0,.00402,initial[2]])
 for u in np.linspace(0,1,51)[1:]:
  zpos=top[2]+(-.039+slider-top[2])*u
  # Cap front edge at -10mm: round the 2mm elevation before crossing it.
  xpos=corner[0]*(1-u) if a.diagonal_approach else 0.
  lift=min(np.clip((-zpos-.008)/.005,0,1),np.clip((xpos+.0055)/.002,0,1));points.append((np.array([xpos,.00402+.0021*lift,zpos]),np.array([0.,1.,0.]),'face-to-cap'))
 if a.axial_first:
  points=[];tail=corner.copy();tail[2]=-.039+slider
  for u in np.linspace(0,1,16):points.append((initial*(1-u)+tail*u,n0,'side-axial-slide'))
  for u in np.linspace(0,1,18)[1:]:
   theta=np.arctan2(n0[1],-n0[0])+(np.pi/2-np.arctan2(n0[1],-n0[0]))*u;points.append((tail,np.array([-np.cos(theta),np.sin(theta),0.]),'tail-corner-roll'))
  for u in np.linspace(0,1,18)[1:]:
   x=tail[0]*(1-u);lift=np.clip((x+.0055)/.002,0,1);points.append((np.array([x,.00402+.0021*lift,tail[2]]),np.array([0,1.,0]),'tail-to-cap'))
 rows=[];previous=q.copy()
 bearing=json.loads(Path('runs/flat-table-20261006/direct/development/functional-tail-transfer-fullB-v774/simulation/wrap-contact-physical-steps.jsonl').read_text().splitlines()[0])['contacts'];bearing=[c for c in bearing if 'thumb' not in c['hand_link']];active=np.r_[np.arange(8),np.arange(12,20)];x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q[active]];prior_x=x0.copy();lo=np.r_[x0[:3]-.035,x0[3:6]-.45,g.w.lower[active]+.015];hi=np.r_[x0[:3]+.035,x0[3:6]+.45,g.w.upper[active]-.015];armseed=z['robot_q'][:7].astype(float)
 def decode(x):
  X=np.eye(4);X[:3,3]=x[:3];X[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();cur=q.copy();cur[active]=x[6:];return X,cur
 def coupled_residual(x,wanted,n):
  X,cur=decode(x);F=g.w.forward(cur);T=X@F['hand_r_thumb_pad_link'];points=v@T[:3,:3].T+T[:3,3];projections=points@n;w=np.exp(-(projections-projections.min())/.0002);pt=w@points/w.sum();r=list((pt-wanted)*500)
  for c in bearing:
   T=X@F[c['hand_link']];actual=T[:3,:3]@np.array(c['position_hand_link_m'])+T[:3,3];prior=np.array(c['position_knife_m'])
   if a.sliding_bearing:
    # Bearing may migrate on the body backside. Preserve the normal
    # constraint, allow axial sliding and inside-face lateral adjustment.
    r.append((actual[1]+.004)*500);r.append(max(abs(actual[0])-.0096,0)*500);r.append(max(abs(actual[2]-prior[2])-.025,0)*400)
   else:r.extend((actual-prior)*400)
  for f in ['thumb','index','middle','ring']:
   r.extend(min(c['gap_lower_bound_m']+.00055,0)*1000 for c in g.gaps(cur,X,slider,f,frames=F,certify_clearance_m=.0001))
  r.extend(min(c['gap_lower_bound_m']-.0001,0)*1000 for c in g.self_gaps(cur,'thumb',frames=F,certify_clearance_m=.0001));r.extend((x[:3]-prior_x[:3])*20);r.extend((x[3:]-prior_x[3:])*.01);return np.array(r)
 if a.resume_geometry:
  rows=json.loads(a.resume_geometry.read_text())['rows'];last=rows[-1];previous=np.array(last['hand_q']);X=np.array(last['wrist_in_knife']);prior_x=np.r_[X[:3,3],Rotation.from_matrix(X[:3,:3]).as_rotvec(),previous[active]];armseed=np.array(last['arm_q'])
 for i,(wanted,n,phase) in enumerate(points):
  if i<len(rows):continue
  if a.reserve_acquired_preload:
   acquired=z['issued_target'][7:].astype(float)-q
   blend=np.clip((n[1]-n0[1])/(1-n0[1]),0,1);blend=blend**3*(10-15*blend+6*blend*blend)
   acquired[16:]*=1-blend
   lo[6:]=np.maximum(g.w.lower[active]+.015,g.w.lower[active]-acquired[active])
   hi[6:]=np.minimum(g.w.upper[active]-.015,g.w.upper[active]-acquired[active])
  def residual(x):
   cur=previous.copy();cur[16:]=x;point=foot(cur,n);knife=full.gaps(cur,L,slider,'thumb',certify_clearance_m=.0001);selfgap=g.self_gaps(cur,'thumb',certify_clearance_m=.0001);gaps=np.array([c['gap_lower_bound_m'] for c in knife]);own=np.array([c['gap_lower_bound_m'] for c in selfgap]);return np.r_[(point-wanted)*500,np.minimum(gaps+.00055,0)*1000,np.minimum(own-.00015,0)*1000,(x-previous[16:])*.005]
  if a.coupled_wrist:
   fit=least_squares(lambda x:coupled_residual(x,wanted,n),np.clip(prior_x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=35,diff_step=1e-4,ftol=1e-6,xtol=5e-5,gtol=5e-5)
   if a.functional_thumb_seed and phase!='side-axial-slide':
    seed=prior_x.copy();seed[-4:]=[1.17408677,-.00826255,.71838869,.61965301]
    alternative=least_squares(lambda x:coupled_residual(x,wanted,n),np.clip(seed,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=50,diff_step=1e-4,ftol=1e-6,xtol=5e-5,gtol=5e-5)
    if alternative.cost<fit.cost:fit=alternative
   X,cur=decode(fit.x);prior_x=fit.x;armseed,ik=k.solve_near(O@X,armseed,max_step=.12);L_saved=L.copy();L=X;err=float(np.linalg.norm(foot(cur,n)-wanted));L=L_saved
  else:
   fit=least_squares(residual,np.clip(previous[16:],g.w.lower[16:]+.015,g.w.upper[16:]-.015),bounds=(g.w.lower[16:]+.015,g.w.upper[16:]-.015),max_nfev=100,diff_step=1e-5);cur=previous.copy();cur[16:]=fit.x;X=L;err=float(np.linalg.norm(foot(cur,n)-wanted));ik=None
  bad=H.inspect(cur);gap=min(c['gap_lower_bound_m'] for c in full.gaps(cur,X,slider,'thumb',certify_clearance_m=.0001));r={'i':i,'phase':phase,'thumb_q':cur[16:].tolist(),'hand_q':cur.tolist(),'arm_q':armseed.tolist(),'wrist_in_knife':X.tolist(),'arm_ik':ik,'contact_target_knife_m':wanted.tolist(),'normal_outward_knife':n.tolist(),'contact_error_m':err,'self':bad,'min_knife_gap_m':gap};rows.append(r);(a.output/'partial-geometry.json').write_text(json.dumps({'rows':rows,'geometry_pass':False,'scope':'Ongoinggeometryonly; no physical result'},indent=2));print(json.dumps(r),flush=True);previous=cur
  if err>.001 or bad or gap<-.0007:break
 passed=len(rows)==len(points);out={'rows':rows,'geometry_pass':passed,'source':str(src),'wrist_in_knife':L.tolist(),'scope':__doc__,'wall_seconds':time.monotonic()-began};(a.output/'geometry.json').write_text(json.dumps(out,indent=2));record('contact_contour_transfer_geometry_terminal',[str(a.output/'geometry.json')],{'passed':passed,'last':rows[-1],'rows':len(rows),'scope':'Staticwholepadcontactcontour only, notactualbearing'},next_step='Clearcontactcontour -> nativecoupledpressure/motorcourse; blocked->allowwrist/wholehand motion while retainingbearingpoints')
if __name__=='__main__':main()
