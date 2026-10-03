"""Small known-stroke geometric supportcountertilt in original actionspan."""
import copy,numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry

def plan(motor,support,reference,degrees=-4.):
 assert -4<=degrees<=4 and degrees!=0
 g=DigitGeometry();h=g.w;wrist=np.asarray(motor['wrist_in_knife']);normals=np.asarray(motor['contact_normals']);start=np.asarray(support['post_lift_target_q']);q=start.copy()
 fingers=['index','middle','pinky'];order=['thumb','index','middle','ring','pinky'];audit=[]
 def surface(q,f):
  m=wrist@h.forward(q)['hand_r_'+f+'_pad_link'];v=np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']])@m[:3,:3].T+m[:3,3]
  p=v@normals[order.index(f)];weights=np.exp(-(p-p.min())/.0002);weights/=weights.sum();return weights@v,m[:3,0]
 anchors={f:surface(start,f) for f in fingers};ref=copy.deepcopy(reference)
 for row in ref['rows']:
  fraction=row['shift_m']/.04;rot=Rotation.from_rotvec([0,0,np.deg2rad(degrees)*fraction]).as_matrix();errors=[]
  for f in fingers:
   ids=[h.names.index('hand_r_'+f+'_joint'+str(i)) for i in range(1,5)];point,axis=anchors[f];desired=rot@point;targetaxis=rot@axis;seed=q.copy()
   low=np.maximum(h.lower[ids]+1e-4,start[ids]-.0399);high=np.minimum(h.upper[ids]-1e-4,start[ids]+.0399)
   def residual(value):
    candidate=seed.copy();candidate[ids]=value;p,a=surface(candidate,f)
    return np.r_[(p-desired)*100,(a-targetaxis)*.12,(value-start[ids])*.002]
   fit=least_squares(residual,np.clip(seed[ids],low+1e-7,high-1e-7),bounds=(low,high),max_nfev=100);q[ids]=fit.x;p,_=surface(q,f);error=float(np.linalg.norm(p-desired));errors.append(error)
   assert error<.00025,(row['shift_m'],f,error)
  row['support_offset_rad']=(q-start)[:16].tolist();audit.append(dict(shift_m=row['shift_m'],requested_support_tilt_deg=degrees*fraction,max_surface_error_m=max(errors),max_motor_offset_rad=float(abs(q-start).max())))
 ref['support_countertilt']=dict(degrees=degrees,scope='Known40mm scheduledreference only, same3support motorgeometry fromonceinitialestimates. Original +/-0.04support actionspan/jointlimits; no liveobject/force input, not force/pose regulation. Actual contact/normal/stability outcomes required.',rows=audit)
 return ref
