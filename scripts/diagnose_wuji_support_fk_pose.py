"""Test whether three measured support FK points explain held-object drift.
Kabsch estimate uses hand joints and fixed pad material points only. Object
truth appears solely in this offline error audit, never in estimated pose.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry

def fit_points(source,target):
 a=source.mean(0);b=target.mean(0);u,s,v=np.linalg.svd((source-a).T@(target-b));rot=v.T@np.diag([1,1,np.linalg.det(v.T@u.T)])@u.T;return rot,b-rot@a,float(np.sqrt(np.mean(np.sum((source@rot.T+b-rot@a-target)**2,axis=1))))
def main():
 p=argparse.ArgumentParser();p.add_argument('--axial-roll-only',action='store_true');p.add_argument('--trial',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();x=np.load(a.trial/'trace.npz');plan=json.loads(a.plan.read_text());g=DigitGeometry();h=g.w;w=np.array(plan['wrist_in_knife']);anchor=int(np.argmin(abs(x['time']-16)));q=x['q'][anchor];frames=h.forward(q);local={};names=['index','middle','pinky'];normalrows={'index':1,'middle':2,'pinky':4}
 for f in names:
  name='hand_r_'+f+'_pad_link';v=np.concatenate([v for v,_ in g.meshes[name]]);m=w@frames[name];n=np.array(plan['contact_normals'][normalrows[f]]);proj=(v@m[:3,:3].T+m[:3,3])@n;weight=np.exp(-(proj-proj.min())/.0002);local[f]=weight@v/weight.sum()
 def points(q):
  frames=h.forward(q);return np.array([frames['hand_r_'+f+'_pad_link'][:3,:3]@local[f]+frames['hand_r_'+f+'_pad_link'][:3,3] for f in names])
 def actual(i):
  obj=x['object'][i];wr=x['wrist'][i];r=Rotation.from_quat(wr[3:7]).as_matrix().T;return r@Rotation.from_quat(obj[3:7]).as_matrix(),r@(obj[:3]-wr[:3])
 original=points(q);r0,p0=actual(anchor);rows=[]
 for i in range(anchor,len(x['time']),3):
  current=points(x['q'][i]);r,t,res=fit_points(original,current)
  if a.axial_roll_only:
   aa=(original-original.mean(0))@w[:3,:3].T;bb=(current-current.mean(0))@w[:3,:3].T;angle=np.arctan2(np.sum(aa[:,0]*bb[:,1]-aa[:,1]*bb[:,0]),np.sum(aa[:,:2]*bb[:,:2]));r=w[:3,:3].T@Rotation.from_rotvec([0,0,angle]).as_matrix()@w[:3,:3];t=current.mean(0)-r@original.mean(0);res=float(np.sqrt(np.mean(np.sum((original@r.T+t-current)**2,axis=1))))
  ra,pa=actual(i);rotation_error=Rotation.from_matrix((r@r0).T@ra).magnitude();position_error=np.linalg.norm(r@p0+t-pa);static_error=Rotation.from_matrix(r0.T@ra).magnitude();rows.append(dict(time_s=float(x['time'][i]),fit_residual_m=res,rotation_error_rad=float(rotation_error),position_error_m=float(position_error),static_rotation_error_rad=float(static_error)))
 result=dict(scope=__doc__,axial_roll_only=a.axial_roll_only,trial=str(a.trial),anchor_s=float(x['time'][anchor]),local_material_points={k:v.tolist() for k,v in local.items()},rows=rows,median_rotation_error_rad=float(np.median([r['rotation_error_rad'] for r in rows])),maximum_rotation_error_rad=max(r['rotation_error_rad'] for r in rows),median_position_error_m=float(np.median([r['position_error_m'] for r in rows])),maximum_fit_residual_m=max(r['fit_residual_m'] for r in rows));a.output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['rows','local_material_points']}))
if __name__=='__main__':main()
