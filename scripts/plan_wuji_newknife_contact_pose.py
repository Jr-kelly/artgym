"""Joint wrist/contact IK for narrow cap, three stroke sites, retained support.
Estimate-only planning; no physical asset, live force or state. Not a demo.
"""
import argparse,json,copy
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument("--stroke-m",type=float,default=.035);p.add_argument('--fixed-wrist-from-initialize',action='store_true',help='Retain certified nominal wrist while adapting finger/contact geometry');p.add_argument('--pinky-support-crosswidth-fraction',type=float);p.add_argument('--middle-support-crosswidth-fraction',type=float);p.add_argument('--minimum-front-cosine',type=float);p.add_argument('--small-wrist',action='store_true');p.add_argument('--smooth',action='store_true');p.add_argument('--two-support',action='store_true');p.add_argument('--initialize',type=Path);p.add_argument('--sites',type=int,default=7);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);plan=json.loads((a.base/'motor-plan.json').read_text());g=DigitGeometry();h=g.w;w0=np.array(plan['wrist_in_knife']);q0=np.array(plan['touch_q']);normals=np.array(plan['contact_normals']);fingers=['thumb','middle','pinky'] if a.two_support else ['thumb','index','middle','pinky'];
 if a.two_support:
  index_ids=[h.names.index('hand_r_index_joint'+str(i)) for i in range(1,5)];q0[index_ids]=np.clip(np.zeros(4),h.lower[index_ids]+.01,h.upper[index_ids]-.01)
 ids={f:[h.names.index('hand_r_'+f+'_joint'+str(i)) for i in range(1,5)] for f in fingers};vertices={f:np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]) for f in fingers}
 def surface(w,q,f):
  m=w@h.forward(q)['hand_r_'+f+'_pad_link'];v=vertices[f]@m[:3,:3].T+m[:3,3];n=normals[['thumb','index','middle','ring','pinky'].index(f)];z=v@n;weight=np.exp(-(z-z.min())/.0002);return weight@v/weight.sum(),m[:3,0]
 supports={f:surface(w0,q0,f)[0] for f in fingers[1:]};estimate=plan['initial_geometry_estimate'];size=estimate['handle_size_WTL_m'];cap=estimate['slider_size_WTL_m'];centerz=-.02205+estimate['slider_contact_shift_m'][2];thumbtarget=np.array([0,size[1]/2+cap[1]+.00015,centerz]);shifts=np.linspace(0,a.stroke_m,a.sites).tolist();support_start=6+4*len(shifts)
 if a.middle_support_crosswidth_fraction is not None:
  assert 0<a.middle_support_crosswidth_fraction<.4
  supports['middle'][0]=a.middle_support_crosswidth_fraction*size[0]
 if a.pinky_support_crosswidth_fraction is not None:
  assert -.4<a.pinky_support_crosswidth_fraction<.4
  supports['pinky'][0]=a.pinky_support_crosswidth_fraction*size[0]
 # Wrist translation and intrinsic rotation relative to baseline, then three
 # independent thumb sites and one shared supporting hand.
 start=np.concatenate([np.zeros(6),np.tile(q0[ids['thumb']],len(shifts))]+[q0[ids[f]] for f in fingers[1:]])
 low=np.concatenate([[-.05]*3,[-1.]*3,np.tile(h.lower[ids['thumb']]+.01,len(shifts))]+[h.lower[ids[f]]+.01 for f in fingers[1:]]);high=np.concatenate([[.05]*3,[1.]*3,np.tile(h.upper[ids['thumb']]-.01,len(shifts))]+[h.upper[ids[f]]-.01 for f in fingers[1:]])
 if a.small_wrist:low[:3]=-.02;high[:3]=.02;low[3:6]=-.4;high[3:6]=.4
 if a.initialize:
  seed=json.loads((a.initialize/'motor-plan.json').read_text());sr=json.loads((a.initialize/'contact-pose.json').read_text())['rows'];sw=np.array(seed['wrist_in_knife']);start[:3]=sw[:3,3]-w0[:3,3];start[3:6]=Rotation.from_matrix(sw[:3,:3]@w0[:3,:3].T).as_rotvec()
  for i,shift in enumerate(shifts):start[6+4*i:10+4*i]=[np.interp(shift,[r['shift_m'] for r in sr],[r['thumb_q'][j] for r in sr]) for j in range(4)]
  for i,f in enumerate(fingers[1:]):start[support_start+4*i:support_start+4*i+4]=np.array(seed['touch_q'])[ids[f]]
 if a.fixed_wrist_from_initialize:
  assert a.initialize
  low[:6]=start[:6]-1e-9;high[:6]=start[:6]+1e-9
 def unpack(x):
  w=w0.copy();w[:3,3]+=x[:3];w[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@w0[:3,:3];q=q0.copy()
  for k,f in enumerate(fingers[1:]):q[ids[f]]=x[support_start+4*k:support_start+4*k+4]
  return w,q
 def residual(x):
  w,q=unpack(x);parts=[]
  for i,shift in enumerate(shifts):
   q[ids['thumb']]=x[6+4*i:10+4*i];point,normal=surface(w,q,'thumb');target=thumbtarget+[0,0,shift];parts.append((point-target)*500)
   parts.append(np.array([max(0.,a.minimum_front_cosine+normal[1])])*.7 if a.minimum_front_cosine is not None else (normal-[0,-1,0])*.7)
  for f in fingers[1:]:
   point,n=surface(w,q,f);parts.append((point-supports[f])*180)
  if a.smooth:
   trajectory=x[6:support_start].reshape(-1,4);parts.extend([np.diff(trajectory,axis=0).ravel()*.12,np.diff(trajectory,n=2,axis=0).ravel()*.3])
  parts.extend([x[:3]*(2 if a.small_wrist else .5),x[3:6]*(.08 if a.small_wrist else .015),(x[6:]-start[6:])*.003])
  return np.concatenate(parts)
 fit=least_squares(residual,np.maximum(np.minimum(start,high-1e-12),low+1e-12),bounds=(low,high),max_nfev=350,ftol=1e-7,xtol=1e-7,gtol=1e-7)
 w,q=unpack(fit.x);rows=[]
 for i,shift in enumerate(shifts):
  q[ids['thumb']]=fit.x[6+4*i:10+4*i];point,n=surface(w,q,'thumb');rows.append(dict(shift_m=shift,thumb_q=q[ids['thumb']].tolist(),point_m=point.tolist(),point_error_m=float(np.linalg.norm(point-thumbtarget-[0,0,shift])),authored_front_cosine=float(-n[1])))
 q[ids['thumb']]=fit.x[6:10];out=copy.deepcopy(plan);preload=np.array(plan['close_q'])-q0;out['wrist_in_knife']=w.tolist();out['touch_q']=q.tolist();out['close_q']=np.clip(q+preload,h.lower+.005,h.upper-.005).tolist();out['open_q']=np.clip(q+(np.array(plan['open_q'])-q0),h.lower+.005,h.upper-.005).tolist();out['close_waypoints']=[dict(fraction=0,q=out['open_q']),dict(fraction=2/3,q=out['touch_q']),dict(fraction=1,q=out['close_q'])]
 if a.two_support:
  for key in ('touch_q','close_q','open_q'):
   for i in index_ids:out[key][i]=float(q0[i])
  out['close_waypoints']=[dict(fraction=0,q=out['open_q']),dict(fraction=2/3,q=out['touch_q']),dict(fraction=1,q=out['close_q'])]
 audit=dict(wrist_shift_m=fit.x[:3].tolist(),wrist_rotation_delta_rad=fit.x[3:6].tolist(),rows=rows,support_error_m={f:float(np.linalg.norm(surface(w,q,f)[0]-supports[f])) for f in fingers[1:]},optimizer_nfev=fit.nfev,optimizer_success=bool(fit.success),scope=__doc__,geometry_preflight_pending=True)
 (a.output/'contact-pose.json').write_text(json.dumps(audit,indent=2));(a.output/'motor-plan.json').write_text(json.dumps(out,indent=2));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
