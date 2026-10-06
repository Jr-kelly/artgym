"""Joint wrist path retaining newly measured index/middle materials, table supported."""
import json,time,argparse
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics,transform
from scripts.g2_contact_geometry import DigitGeometry
from scripts.record_wuji_flat_table_event import record

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--actual-correction',action='store_true');ap.add_argument('--rail-clear',action='store_true');ap.add_argument('--stroke',action='store_true');a=ap.parse_args()
 if a.stroke:a.rail_clear=True
 if a.rail_clear:a.actual_correction=True
 p=Path('runs/flat-table-20261006/preparation/'+('actual-slider-stroke-20261006' if a.stroke else 'actual-thumb-rail-clear-r1-20261006' if a.rail_clear else 'actual-loaded-thumb-correction-20261006' if a.actual_correction else 'actual-dual-support-thumb-20261006'));p.mkdir(exist_ok=False)
 sp=p/'asset-spec.json';sp.write_text(json.dumps(dict(asset_urdf='assets/objects/knife_wuji_newknife_20261005/nominal-v5/mobility.urdf',file_sha256={})))
 g=DigitGeometry(max_face_axes=6,knife_spec=sp);k=G2Kinematics();source=Path('runs/flat-table-20261006/'+('recorded-actual-slider-contact-8p9s' if a.stroke else 'recorded-loaded-correction-8p9s' if a.rail_clear else 'recorded-dual-thumb-9s' if a.actual_correction else 'recorded-new-dual-support-1s'));s=np.load(source/'takeover.npz')
 O=transform(s['object_state'][:3],s['object_state'][3:7]);q0=s['robot_q'].astype(float);offset=s['issued_target']-q0
 ids=np.r_[np.arange(7),np.arange(7,15),np.arange(23,27)];x0=q0[ids];lo=np.r_[k.lower,g.w.lower][ids]+.001;hi=np.r_[k.upper,g.w.upper][ids]-.001
 names=['hand_r_index_link4','hand_r_middle_link4','hand_r_thumb_pad_link']
 materials=[np.array([.006882446745518775,-.004752936075092943,.009188747811550014]),np.array([-.006137721754216662,-.006854934432174916,-.005539267097527919]),np.array([.008139873738,-.002185502453,-.005107771605])]
 targets=[np.array([-.008123513311147681,.003988069482147673,.07199820131063465]),np.array([-.006993900984525701,.003993611782789258,-.004768774844706046]),np.array([0,.006,-.026+float(s['slider_q'])])]
 if a.actual_correction:
  c=next(c for c in json.load(open(source/'native-contacts.json'))['contacts'] if c['hand_link']=='hand_r_index_link4')
  names.pop(1);materials.pop(1);targets.pop(1);materials[0]=np.array(c['position_hand_link_m']);targets[0]=np.array(c['position_knife_m'])
 if a.rail_clear:targets[-1][0]=-.0015
 if a.stroke:
  c=next(c for c in json.load(open(source/'native-contacts.json'))['contacts'] if c['hand_link']=='hand_r_thumb_pad_link' and c['knife_link']=='link_1');materials[-1]=np.array(c['position_hand_link_m']);targets[-1]=np.array(c['position_knife_m'])+[0,0,.030]
 V={n:np.concatenate([v for v,_ in meshes]) for n,meshes in g.meshes.items()};inv=np.linalg.inv(O)
 def state(x):
  q=q0.copy();q[ids]=x;W=k.forward(q[:7]);F=g.w.forward(q[7:]);L=inv@W
  pts=[(L@F[n])[:3,:3]@m+(L@F[n])[:3,3] for n,m in zip(names,materials)]
  return q,W,F,L,pts
 _,_,_,_,start=state(x0);rows=[];diagnostics=[];x=np.clip(x0,lo+1e-7,hi-1e-7);b=time.time()
 for u in np.linspace(0,1,9 if a.stroke else 7 if a.actual_correction else 13):
  thumb=(1-u)*start[-1]+u*(targets[-1]+[0,-.0003 if a.actual_correction else .0002,0])
  def residual(z):
   q,W,F,L,pts=state(z);r=[]
   for point,t in zip(pts,targets[:-1]+[thumb]):r.extend((point-t)*400)
   for n,v in V.items():
    T=W@F[n];P=v@T[:3,:3].T+T[:3,3];inside=(P[:,0]>=.3)&(P[:,0]<=.9)&(P[:,1]>=-.63)&(P[:,1]<=.17)
    r.append(max(0,.7501-P[inside,2].min())*200 if inside.any() else 0.)
   r.extend(min(0,a['gap_lower_bound_m']-.0002)*120 for a in g.self_gaps(q[7:],'thumb',.0002))
   for f in ['index','middle','thumb']:
    r.extend(min(0,a['gap_lower_bound_m']+.0003)*100 for a in g.gaps(q[7:],L,float(s['slider_q']),f) if a['hand_link'] not in names)
   if a.rail_clear:
    r.extend(min(0,c['gap_lower_bound_m']-.0002)*250 for c in g.gaps(q[7:],L,float(s['slider_q']),'thumb') if c['knife_link']=='link_0')
   r.extend((z-x0)*.02);return r
  fit=least_squares(residual,x,bounds=(lo,hi),max_nfev=40 if a.actual_correction else 65,diff_step=1e-5);x=fit.x;q,W,F,L,pts=state(x)
  errs=[float(np.linalg.norm(a-t)) for a,t in zip(pts,targets[:-1]+[thumb])];gap=min(a['gap_lower_bound_m'] for a in g.self_gaps(q[7:],'thumb',.0002));d=dict(fraction=float(u),errors_m=errs,thumb_self_gap_m=gap);diagnostics.append(d);print(json.dumps(d),flush=True)
  command=q+offset
  if not a.actual_correction:command[23:27]=q[23:27]
  command=np.clip(command,np.r_[k.lower,g.w.lower],np.r_[k.upper,g.w.upper]);rows.append(dict(time_s=float(1+u*6),arm_q=command[:7].tolist(),hand_q=command[7:].tolist()))
 rows.insert(0,dict(time_s=0.,arm_q=s['issued_target'][:7].tolist(),hand_q=s['issued_target'][7:].tolist()));rows.append(dict(rows[-1],time_s=9.))
 result=dict(rows=rows,diagnostics=diagnostics,actual_material_points=[m.tolist() for m in materials],targets=[t.tolist() for t in targets],elapsed_s=time.time()-b,loaded_motor_offset_retained=True,no_lift=True)
 (p/'path.json').write_text(json.dumps(result,indent=2));record('actual_dual_support_thumb_path_finished',[str(p/'path.json')],dict(final=diagnostics[-1],worst_point_error_m=max(max(d['errors_m']) for d in diagnostics)),updates=dict(active_jobs=[]),next_step='Inspect actual joint path; one native segment if contact errors support a test, never geometry-only success.')
if __name__=='__main__':main()
