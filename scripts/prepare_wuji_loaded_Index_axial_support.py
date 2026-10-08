"""Axially migrate an actual Index bearing while the other three bearings remain.

The current contact span lies below the knife COM. Move Index toward z=-5mm
before converting it into proximal back support for Pinky. Original meshes,
physical properties, H and actuator limits stay. Exact original surface rolling
guides a single bounded path. Measured normal Jacobian transport plus captured
residual torque is a proxy; native load and migration are required evidence.
"""
import argparse,json,time,math
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import transform
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.wuji_original_contact_surface import OriginalContactSurface
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v993');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'takeover.npz');meta=json.loads((a.source/'manifest.json').read_text());trace=np.load(meta['source']);clock=float(trace['time'][meta['takeover_index']]);C=[json.loads(x)for x in(Path(meta['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()];cc=min(C,key=lambda r:abs(r['time_s']-clock))['contacts'];f=FunctionalEntryAffordance();g=f.g
 for n,meshes in g.meshes.items():g.meshes[n]=[(v,np.unique(N,axis=0))for v,N in meshes]
 names=sorted({c['hand_link']for c in cc if '_index_'in c['hand_link']and c['knife_link']=='link_0'});assert names;name=max(names,key=lambda n:sum(c['normal_magnitude_N']for c in cc if c['hand_link']==n));h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);L=np.linalg.inv(transform(z['object_state'][:3],z['object_state'][3:7]))@f.kin.forward(z['robot_q'][:7]);M=[];FN=[]
 for n in names:
  sel=[c for c in cc if c['hand_link']==n and c['knife_link']=='link_0'];w=np.array([c['normal_magnitude_N']for c in sel]);w/=w.sum();M.append(w@np.array([c['position_hand_link_m']for c in sel]));FN.append(sum((np.array(c['force_normal_contribution_knife_N'])for c in sel),np.zeros(3)))
 surface=OriginalContactSurface(np.concatenate([v for v,norm in g.meshes[name]]));initial=surface.project(M[names.index(name)]);T=L@g.w.forward(h0)[name];P0=T[:3,:3]@initial+T[:3,3];low=np.r_[g.w.lower[:4]+.015,[-.006]*3];high=np.r_[g.w.upper[:4]-.015,[.006]*3];prior=np.r_[h0[:4],np.zeros(3)];rows=[];failure=None;beg=time.monotonic();depth={}
 for c in g.gaps(h0,L,float(z['slider_q']),'index'):depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))]=min(-.0002,c['gap_lower_bound_m']-.000005)
 record('loaded_Index_axial_original_path_started_'+a.version,[str(a.source)],dict(scope=__doc__,source_Index_contact_link=name,source_surface_point_knife_m=P0.tolist(),target_axial_m=-.005,other_three_targets='exact originalissued unchanged',reason='Proximal backbearing balancesknifeCOM−12mm withdistalPinky beforeThumbfront conversion'),next_step='Bounded fixedwrist Indexoriginalsurface path; nativeactual load atproximalbody before newbackface conversion')
 def point(x):
  h=h0.copy();h[:4]=x[:4];m=surface.project(initial+x[4:]);T=L@g.w.forward(h)[name];return h,m,T[:3,:3]@m+T[:3,3]
 for i,u in enumerate(np.linspace(0,1,9)):
  wanted=P0.copy();wanted[2]=P0[2]*(1-u)-.005*u;previous=prior.copy()
  def residual(x):
   if time.monotonic()-beg>75:raise TimeoutError('Bounded single Indexaxial check')
   h,m,P=point(x);r=list((P-wanted)*1000);r.extend(min(0.,c['gap_lower_bound_m']-depth[(c['hand_link'],c['knife_link'],c.get('knife_component',0))])*1400 for c in g.gaps(h,L,float(z['slider_q']),'index',certify_clearance_m=.0002));r.extend(min(0.,c['gap_lower_bound_m']-.0002)*1400 for c in g.pair_gaps(h,f.H.pairs,certify_clearance_m=.0002));r.extend((x-previous)*.025);return np.array(r)
  try:prior=previous if i==0 else least_squares(residual,previous,bounds=(low,high),max_nfev=60,diff_step=1e-5).x
  except TimeoutError as exc:failure=str(exc);break
  h,m,P=point(prior);H=f.H.inspect(h);err=float(np.linalg.norm(P-wanted));rows.append(dict(hand_q=h.tolist(),Index_material_link_m=m.tolist(),target_knife_m=wanted.tolist(),actual_knife_m=P.tolist(),error_m=err,self=H));print(json.dumps(dict(index=i,fraction=float(u),point_knife_m=P.tolist(),error_m=err,self=H)),flush=True)
  if err>.0003 or H:failure='Original fixedwrist Index axial reach/H';break
 kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp'])
 def jac(h,n,m):
  J=np.empty((3,4))
  for j in range(4):
   up=h.copy();down=h.copy();up[j]+=1e-5;down[j]-=1e-5;A=L@g.w.forward(up)[n];B=L@g.w.forward(down)[n];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
  return J
 cert=[];motors=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist())for t in[0.,.5]];t=.5;prev=issued[7:].copy();residual_tau=kp[:4]*(issued[7:11]-h0[:4])-sum((jac(h0,n,m).T@F for n,m,F in zip(names,M,FN)),np.zeros(4))
 if failure is None:
  for seg,(A,B)in enumerate(zip(rows[:-1],rows[1:])):
   qa=np.array(A['hand_q']);qb=np.array(B['hand_q'])
   for u in np.linspace(0,1,max(2,int(np.ceil(abs(qb-qa).max()/.012))+1)):
    h=qa*(1-u)+qb*u;H=f.H.inspect(h);cert.append(dict(segment=seg,fraction=float(u),self=H))
    if H:failure='Original dense H';break
   if failure:break
 if failure is None:
  for r in rows:
   h=np.array(r['hand_q']);chosen=[np.array(r['Index_material_link_m'])if n==name else m for n,m in zip(names,M)];motor=issued[7:].copy();motor[:4]=h[:4]+(sum((jac(h,n,m).T@F for n,m,F in zip(names,chosen,FN)),np.zeros(4))+residual_tau)/kp[:4]
   if np.minimum(motor-g.w.lower,g.w.upper-motor).min()<=0:failure='Original motor limit';break
   t+=max(1,int(np.ceil(abs(motor-prev).max()/.012)))/30.;motors.append(dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=motor.tolist()));prev=motor
 passed=bool(failure is None and len(rows)==9);out=dict(passed=passed,failure=failure,source=str(a.source),rows=rows,dense_certificates=cert,source_Index_normal_vectors_N=np.array(FN).tolist(),seconds=t+1.5,scope=__doc__);(a.output/'precheck.json').write_text(json.dumps(out,indent=2));(a.output/'preparer.py').write_bytes(Path(__file__).read_bytes())
 if passed:motors.append(dict(motors[-1],time_s=t+1.5));(a.output/'motor.json').write_text(json.dumps(dict(rows=motors,required_actual_source=str(a.source),development_abort_on_translation_m=.015,scope=__doc__),indent=2))
 record('loaded_Index_axial_original_path_terminal_'+a.version,[str(a.output/'precheck.json')],dict(passed=passed,failure=failure,poses=len(rows),seconds=t+1.5),next_step='Native actualIndex axial/load/H/carry ifvalid; unreachable ->coupledwrist withretainedM/Thumb/Pinky, not commonpressure orNNrounds');print(json.dumps(dict(passed=passed,failure=failure,poses=len(rows),seconds=t+1.5)))
if __name__=='__main__':main()
