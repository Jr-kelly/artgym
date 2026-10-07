"""Small structural direct side-opposition plan, slider facing down; motors only."""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--longitudinal-m',type=float,default=0.);p.add_argument('--contact-y-m',type=float,default=-.002);p.add_argument('--diagonal-opposition',action='store_true');p.add_argument('--functional-front',action='store_true');p.add_argument('--reserved-true-pad-grip',action='store_true');p.add_argument('--balanced-true-pad-grip',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json');g=DigitGeometry(max_face_axes=12,knife_spec=spec);k=G2Kinematics();V={n:np.concatenate([v for v,_ in mesh]) for n,mesh in g.meshes.items()};O=np.eye(4);O[:3,:3]=(Rotation.from_euler('z',45,degrees=True)*Rotation.from_euler('x',-90,degrees=True)).as_matrix();O[:2,3]=[.50,-.40];O=g.knife_geometry.table_pose(O)
 # Local palm inside +X faces down, fingers curl across width; four digits run along knife axis.
 L=np.eye(4);L[:3,:3]=np.array([[0,0,1],[1,0,0],[0,1,0]]);L[:3,3]=[-.10,-.08,a.longitudinal_m-.008]
 q=np.array([.65,0,.55,.4]*4+[.8,.3,.7,.1]);ids=np.r_[0:8,8:12,16:20];names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_pinky_pad_link','hand_r_thumb_pad_link'];directions=[[-1,0,0]]*3+[[1,0,0]];targets=np.array([[.0095,a.contact_y_m,.03],[.0095,a.contact_y_m,0],[.0095,a.contact_y_m,-.05],[-.0095,a.contact_y_m,-.02]]);targets[:,2]+=a.longitudinal_m
 if a.diagonal_opposition:
  L[:3,:3]=np.array([[0,-2**-.5,2**-.5],[1,0,0],[0,2**-.5,2**-.5]]);L[:3,3]=[-.07,-.09,-.105]
  q=np.array([.6,0,.6,.6]*2+[.6,0,.9,.4]*2+[.9,.3,.7,.1]);ids=np.r_[0:8,16:20];names=['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_pad_link'];directions=[[-1,0,0]]*2+[[1,0,0]];targets=np.array([[.0095,a.contact_y_m,.03],[.0095,a.contact_y_m,0],[-.0095,a.contact_y_m,-.02]])
 if a.functional_front:
  q[16:]=[.8,.3,-.1,.3];targets[:,2]=[.025,-.005,.015]
  q[8:16]=[.2,0,.2,.3]*2
 if a.reserved_true_pad_grip:
  O[:3,:3]=Rotation.from_euler('x',-90,degrees=True).as_matrix();O[:2,3]=[.45,-.4];O=g.knife_geometry.table_pose(O)
  q[16:]=[1.,.3,.4,.3]
 if a.balanced_true_pad_grip:
  targets[:,2]=[.015,-.030,0.]
 materials={n:(np.exp((V[n][:,0]-V[n][:,0].max())/.0005)@V[n]/np.exp((V[n][:,0]-V[n][:,0].max())/.0005).sum()) for n in names}
 x0=np.r_[L[:3,3],Rotation.from_matrix(L[:3,:3]).as_rotvec(),q[ids]];lo=np.r_[L[:3,3]-.07,x0[3:6]-(1.2 if a.functional_front else .6),g.w.lower[ids]+.012];hi=np.r_[L[:3,3]+.07,x0[3:6]+(1.2 if a.functional_front else .6),g.w.upper[ids]-.012];N=np.asarray(directions)
 if a.reserved_true_pad_grip:
  lo[6:]=g.w.lower[ids]+.06;hi[6:]=g.w.upper[ids]-.06
  lo[6+list(ids).index(18)]=.05;lo[6+list(ids).index(19)]=.05
 def decode(x):
  l=np.eye(4);l[:3,3]=x[:3];l[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix();h=q.copy();h[ids]=x[6:];return l,h
 def contacts(l,h):
  F=g.w.forward(h);points=[];normals=[]
  for n,d in zip(names,N):
   T=l@F[n];v=V[n]@T[:3,:3].T+T[:3,3];proj=v@d;w=np.exp((proj-proj.max())/.0004);points.append(T[:3,:3]@materials[n]+T[:3,3] if a.functional_front else w@v/w.sum());normals.append(T[:3,0])
  return np.array(points),np.array(normals)
 def res(x):
  l,h=decode(x);P,n=contacts(l,h);F=g.w.forward(h);W=O@l;r=list(((P-targets)*([250,250,220] if a.balanced_true_pad_grip else [250,250,35] if a.functional_front else 220)).ravel());r.extend(((n-N)*(1.5 if a.functional_front else .9 if a.diagonal_opposition else .3)).ravel());r.extend((l[:3,0]-[0,1,0])*(1. if a.reserved_true_pad_grip else .15))
  for name,v in V.items():
   T=W@F[name];z=(v@T[:3,:3].T+T[:3,3])[:,2];r.append(max(0,(.752 if a.reserved_true_pad_grip else .751)-z.min())*350)
  for f in ['index','middle','pinky','thumb','ring']:
   for gap in g.gaps(h,l,0,f):
    if gap['hand_link'] not in names:r.append(min(0,gap['gap_lower_bound_m']-.0002)*80)
  r.extend((x-x0)*.008);return np.array(r)
 record('direct_side_geometry_start',[str(a.output)],config={'uncertainty':'Fourfunctional sidepads reachablewithpalm-down andallhandabove realtable?','decision':'Contacterror<1mm/no tablevertices/deepinterdigitcollision permits shortnative close/lift; failurechangescontactheight or topology','targets':targets.tolist(),'initial_slider_face':'down'})
 t=time.time();fit=least_squares(res,np.clip(x0,lo+1e-6,hi-1e-6),bounds=(lo,hi),max_nfev=100,diff_step=1e-5);l,h=decode(fit.x);P,n=contacts(l,h);W=O@l;F=g.w.forward(h);zmin=min((v@(W@F[name])[:3,:3].T+(W@F[name])[:3,3])[:,2].min() for name,v in V.items());arm,e=k.solve(W,np.array([-.8,-.8,1.4,1.,0,-.3,1.]));inter=HandIntersection().inspect(h)
 out=dict(wrist_in_knife=l.tolist(),hand_q=h.tolist(),object_world=O.tolist(),arm_q=arm.tolist(),arm_ik=e,active_links=names,contact_targets=targets.tolist(),contact_points=P.tolist(),contact_errors_m=np.linalg.norm(P-targets,axis=1).tolist(),normal_errors=np.linalg.norm(n-N,axis=1).tolist(),lowest_hand_z_m=float(zmin),palm_inside_world=(W[:3,0]).tolist(),intersections=inter,seconds=time.time()-t,source='Direct sideopposition from functionalgrip, planonly notphysics')
 if a.functional_front:out.update(functional_front=True,material_points={n:m.tolist() for n,m in materials.items()},longitudinal_targets_free=True)
 (a.output/'candidate.json').write_text(json.dumps(out,indent=2));print(json.dumps({v:out[v] for v in ['contact_errors_m','normal_errors','lowest_hand_z_m','arm_ik','intersections','seconds']}),flush=True)
 record('direct_side_geometry_finished',[str(a.output/'candidate.json')],config={v:out[v] for v in ['contact_errors_m','lowest_hand_z_m','arm_ik','intersections']},next_step='Inspectgeometry thennativefeasiblecontact; no fulloldprefixreplay')
if __name__=='__main__':main()
