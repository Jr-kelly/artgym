"""Coupled gravity-wrench motor reference from actual normal-contact observations.

Tangential forces are allocated proxies, not measured forces. Original measured
normal budget, conservative mu.8 and original PD/effort/joint limits are retained.
Only the unloaded new finger's old non-knife preload is retired. Old primary
contacts remain active. Native normal contacts and every-frame H certify load.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.g2_kinematics import transform,minimal_alignment
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',default='v911');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.loads(a.geometry.read_text());assert geo['geometry_pass'];cal=json.loads(a.calibration.read_text());assert cal['feasible']and geo['source']==cal['source'];src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();h0=z['robot_q'][7:].astype(float);issued=z['issued_target'].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);L0=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);names=list(geo['rows'][0]['contact_material_points']);assert names==['hand_r_index_pad_link','hand_r_middle_pad_link','hand_r_thumb_pad_link'];digit=geo.get('new_bearing_digit','ring');new='hand_r_'+digit+'_pad_link';names.append(new);ids=[np.array([f.g.w.names.index('hand_r_'+n.split('_')[2]+'_joint'+str(j))for j in range(1,5)])for n in names];kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);com=np.array([0,.000113841678,-.012053567434+.2*float(z['slider_q'])]);hulls=[ConvexHull(np.concatenate([v for v,normals in f.g.meshes[n]]))for n in names];material0=dict(geo['rows'][0]['contact_material_points']);firstfoot=np.array(geo['rows'][0].get('bearing_foot_knife_m',geo['rows'][0].get('ring_foot_knife_m')));T=L0@f.g.w.forward(h0)[new];material0[new]=(T[:3,:3].T@(firstfoot-T[:3,3])).tolist();force0=np.r_[np.array(cal['allocated_F_proxy_knife_N']),np.zeros((1,3))];residual=[];corrections=[]
 def jac(L,h,n,m,index):
  J=np.empty((3,4))
  for j,c in enumerate(index):
   up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@f.g.w.forward(up)[n];B=L@f.g.w.forward(down)[n];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
  return J
 for j,(n,index,H)in enumerate(zip(names,ids,hulls)):
  m=np.array(material0[n]);T=L0@f.g.w.forward(h0)[n];J=jac(L0,h0,n,m,index);tau=kp[index]*(issued[7:][index]-h0[index]);residual.append(tau-J.T@force0[j]);e=H.equations[:,:3]@m+H.equations[:,3];ng=H.equations[e.argmax(),:3];na=T[:3,:3].T@np.array(cal['normals_knife'][j])if j<3 else ng;corrections.append(minimal_alignment(ng,na))
 rows=[dict(time_s=t,arm_q=issued[:7].tolist(),hand_q=issued[7:].tolist(),wrist_in_knife=L0.tolist(),normal_outward_knife=[-1.,0.,0.])for t in (0.,1.)];clock=1.;previous=issued.copy();Fprev=force0.copy();audit=[];failure=None;scale=np.array([1,1,1,100,100,100]);wrench=np.array(cal['desired_gravity_wrench']);budget=cal['original_normal_budget_N'];record('actual_normal_calibrated_gravity_wrench_path_started_'+a.version,[str(a.geometry),str(a.calibration)],dict(scope=__doc__,budget_N=budget,new_bearing_digit=digit),next_step='Check allgrip gravitywrench/friction/motor feasibility before one native load verification')
 for r in geo['rows']:
  L=np.array(r['wrist_in_knife']);h=np.array(r['hand_q']);material=dict(r['contact_material_points']);foot=np.array(r.get('bearing_foot_knife_m',r.get('ring_foot_knife_m')));bounds=r.get('bearing_pad_bounds_knife_m',r.get('ring_pad_bounds_knife_m'));T=L@f.g.w.forward(h)[new];material[new]=(T[:3,:3].T@(foot-T[:3,3])).tolist();P=[];N=[];J=[]
  for j,(n,index,H)in enumerate(zip(names,ids,hulls)):
   m=np.array(material[n]);T=L@f.g.w.forward(h)[n];P.append(T[:3,:3]@m+T[:3,3]);e=H.equations[:,:3]@m+H.equations[:,3];N.append(T[:3,:3]@corrections[j]@H.equations[e.argmax(),:3]if j<3 else np.array([0.,1.,0.]));J.append(jac(L,h,n,m,index))
  P=np.array(P);N=np.array(N);active=r['phase']=='acquire-back-face'and foot[0]<.0092 and bounds[1][1]>-.0055;B=np.empty((6,12))
  for i,point in enumerate(P):
   for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
  def cones(x):
   F=x.reshape(4,3);fn=np.sum(F*N,1);ft=F-fn[:,None]*N;sel=4 if active else 3;return np.r_[.8**2*fn[:sel]**2-np.sum(ft[:sel]**2,1),fn[:3]-.015,fn[3]-.15 if active else 0.,budget-fn.sum()]
  seed=np.array(r.get('gravity_wrench_proxy',{}).get('forces_knife_N',Fprev)).ravel();fit=minimize(lambda x:float(((x-Fprev.ravel())**2).sum()),seed,method='SLSQP',constraints=[dict(type='eq',fun=lambda x:np.r_[(B@x-wrench)*scale,np.zeros(0)if active else x.reshape(4,3)[3]]),dict(type='ineq',fun=cones)],options=dict(maxiter=250,ftol=1e-12));F=fit.x.reshape(4,3);error=float(np.linalg.norm((B@fit.x-wrench)*scale));slack=float(cones(fit.x).min());fn=np.sum(F*N,1);entry=dict(index=r['index'],active_new_bearing=bool(active),force_proxy_knife_N=F.tolist(),normals_knife=N.tolist(),normal_proxy_N=fn.tolist(),wrench_error=error,cone_slack=slack,solver=fit.message);audit.append(entry)
  if error>1e-5 or slack< -1e-7:failure='Contact-wrench feasibility failed';break
  motor=h.copy()
  for j,(index,jacobian,force,rest)in enumerate(zip(ids,J,F,residual)):
   if j==3:rest=rest*(1-min(r['index']/4.,1.))
   motor[index]+=(jacobian.T@force+rest)/kp[index]
  arm=np.array(r['arm_q'])+issued[:7]-z['robot_q'][:7];q=np.r_[arm,motor];margin=float(np.minimum(q-np.r_[f.kin.lower,f.g.w.lower],np.r_[f.kin.upper,f.g.w.upper]-q).min());entry['motor_margin_rad']=margin
  if margin<=0:failure='Original motor limit';break
  frames=max(1,int(np.ceil(max(abs(q[:7]-previous[:7]).max()/.004,abs(q[7:]-previous[7:]).max()/.012))));clock+=frames/30.;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist(),wrist_in_knife=L.tolist(),normal_outward_knife=[-1.,0.,0.]));previous=q;Fprev=F
 passed=failure is None and len(audit)==len(geo['rows']);(a.output/'wrench-path-audit.json').write_text(json.dumps(dict(passed=passed,failure=failure,source=str(src),normal_budget_N=budget,rows=audit,scope=__doc__),indent=2))
 if passed:
  rows.append(dict(rows[-1],time_s=clock+1.5));reference=a.output/'whole-wrist-reference.json';reference.write_text(json.dumps(dict(rows=rows),indent=2));out=dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.04,scope=__doc__,contact_contour_course=dict(reference=str(reference),start_s=0.,end_s=1e9,side_to_front_seconds=1.,whole_wrist_pose_feedback=True,preparation_pressure_feedback=False,preload_release_basis='normal-turn',knife_pose_coordinates='live-sim-oracle',object_pose_feedback_components='world-stabilized',pose_error_phase_governor=True));(a.output/'motor.json').write_text(json.dumps(out,indent=2))
 record('actual_normal_calibrated_gravity_wrench_path_terminal_'+a.version,[str(a.output/'wrench-path-audit.json')],dict(passed=passed,failure=failure,poses=len(audit),seconds=clock+1.5,scope=__doc__),next_step='Feasiblecoupled wrench ->one native sameactualsource; otherwise reject incompatible contactnormal route, no force/gain scan');print(json.dumps(dict(passed=passed,failure=failure,poses=len(audit),seconds=clock+1.5,last=audit[-1])))
if __name__=='__main__':main()
