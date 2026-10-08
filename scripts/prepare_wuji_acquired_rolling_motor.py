"""All-hand motor guidance transporting the captured whole-grip wrench proxy.

Original PD, effort, gravity and contact remain active. Force inferred from
measured joint deflection is a proxy, not measured contact force. Only geometric
rolling contact coordinates guide motors; no live material-point followers.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--geometry',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);geo=json.loads(a.geometry.read_text());assert geo['geometry_pass'];src=Path(geo['source']);z=np.load(src/'takeover.npz');f=FunctionalEntryAffordance();h=z['robot_q'][7:].astype(float);initial=z['issued_target'].astype(float);O=transform(z['object_state'][:3],z['object_state'][3:7]);L=np.linalg.inv(O)@f.kin.forward(z['robot_q'][:7]);kp=np.array(json.loads(Path('runs/flat-table-20261006/direct/development/balanced-pad-fresh-free-wrist-widthflip-v877/prefix.json').read_text())['direct_pickup']['hand_kp']);
 manifest=json.loads((src/'manifest.json').read_text());contacts=json.loads((Path(manifest['source']).parent/'wrap-contact-physical-steps.jsonl').read_text().splitlines()[-1])['contacts'];names=list(geo.get('material_points',geo['rows'][0]['contact_material_points']));
 if 'ring_foot_knife_m'in geo['rows'][0]and 'hand_r_ring_pad_link'not in names:names.append('hand_r_ring_pad_link')
 initial_materials={}
 for name in names:
  cc=[c for c in contacts if c['hand_link']==name];weights=np.array([c['normal_magnitude_N']for c in cc]);weights/=weights.sum();initial_materials[name]=weights@np.array([c['position_hand_link_m']for c in cc])
 ids=[np.array([f.g.w.names.index('hand_r_'+name.split('_')[2]+'_joint'+str(j))for j in range(1,5)])for name in names];com=np.array([0,.000113841678,-.012053567434]);forces=[];residuals=[];points=[]
 def jac(L,h,name,m,idx):
  J=np.empty((3,4))
  for j,c in enumerate(idx):
   up=h.copy();down=h.copy();up[c]+=1e-5;down[c]-=1e-5;A=L@f.g.w.forward(up)[name];B=L@f.g.w.forward(down)[name];J[:,j]=(A[:3,:3]@m+A[:3,3]-B[:3,:3]@m-B[:3,3])/2e-5
  return J
 for name,idx in zip(names,ids):
  m=np.array(initial_materials[name]);T=L@f.g.w.forward(h)[name];points.append(T[:3,:3]@m+T[:3,3]);J=jac(L,h,name,m,idx);tau=kp[idx]*(initial[7:][idx]-h[idx]);F=np.linalg.lstsq(J.T,tau,rcond=1e-3)[0];forces.append(F);residuals.append(tau-J.T@F)
 forces=np.array(forces);points=np.array(points);hulls=[ConvexHull(np.concatenate([v for v,_ in f.g.meshes[n]]))for n in names]
 def contact_normals(L,h,materials):
  F=f.g.w.forward(h);out=[]
  for n,H in zip(names,hulls):
   m=np.array(materials[n]);eq=H.equations[:,:3]@m+H.equations[:,3];T=L@F[n];out.append(T[:3,:3]@H.equations[eq.argmax(),:3])
  return np.array(out)
 n0=contact_normals(L,h,initial_materials);normal_budget=float(np.sum(forces*n0));previous_forces=forces.copy();wrench=np.r_[forces.sum(0),np.cross(points-com,forces).sum(0)];rows=[dict(time_s=0.,arm_q=initial[:7].tolist(),hand_q=initial[7:].tolist())];checks=[];clock=1.;prev=initial.copy();scale=np.array([1,1,1,100,100,100])
 for row in geo['rows']:
  row=dict(row);row['contact_material_points']=dict(row['contact_material_points'])
  if 'ring_foot_knife_m'in row:
   T=np.array(row['wrist_in_knife'])@f.g.w.forward(row['hand_q'])['hand_r_ring_pad_link'];m=T[:3,:3].T@(np.array(row['ring_foot_knife_m'])-T[:3,3]);u=row['fraction'];row['contact_material_points']['hand_r_ring_pad_link']=(initial_materials['hand_r_ring_pad_link']*(1-u)+m*u).tolist()
  L=np.array(row['wrist_in_knife']);h=np.array(row['hand_q']);Fh=f.g.w.forward(h);P=[];J=[]
  for name,idx in zip(names,ids):
   m=np.array(row['contact_material_points'][name]);T=L@Fh[name];P.append(T[:3,:3]@m+T[:3,3]);J.append(jac(L,h,name,m,idx))
  P=np.array(P);current=np.r_[forces.sum(0),np.cross(P-com,forces).sum(0)];A=np.empty((6,2*len(names)))
  for i,point in enumerate(P):
   for j in range(2):v=np.eye(3)[j+1];A[:,2*i+j]=np.r_[v,np.cross(point-com,v)]
  normals=contact_normals(L,h,row['contact_material_points']);active=np.ones(len(names),dtype=bool);
  if 'ring_foot_knife_m'in row and (row['phase']=='clear-side-to-back-corner' or row['ring_foot_knife_m'][0]>.0092):active[names.index('hand_r_ring_pad_link')]=False
  B=np.empty((6,3*len(names)))
  for i,point in enumerate(P):
   for j in range(3):v=np.eye(3)[j];B[:,3*i+j]=np.r_[v,np.cross(point-com,v)]
  def friction(x):
   F=x.reshape(len(names),3);N=np.sum(F*normals,axis=1);tangent=F-N[:,None]*normals
   minimum=np.ones(len(names))*.015
   if 'ring_foot_knife_m'in row and active[names.index('hand_r_ring_pad_link')]:minimum[names.index('hand_r_ring_pad_link')]=.15
   return np.r_[.8**2*N[active]**2-np.sum(tangent[active]**2,axis=1),N[active]-minimum[active],normal_budget-N.sum()]
  fit=minimize(lambda x:float(np.sum((x-previous_forces.ravel())**2)),previous_forces.ravel(),method='SLSQP',constraints=[dict(type='eq',fun=lambda x:np.r_[(B@x-wrench)*scale,x.reshape(len(names),3)[~active].ravel()]),dict(type='ineq',fun=friction)],options=dict(maxiter=150,ftol=1e-12))
  newF=fit.x.reshape(len(names),3);normal_load=np.sum(newF*normals,axis=1);ratio=np.linalg.norm(newF-normal_load[:,None]*normals,axis=1)/np.maximum(normal_load,1e-12);ratio[~active]=0;allocation_error=float(np.linalg.norm((B@fit.x-wrench)*scale));assert allocation_error<1e-5 and friction(fit.x).min()>-1e-7,(row['index'],fit.message,allocation_error,friction(fit.x).tolist());previous_forces=newF.copy()
  motor=h.copy()
  for idx,jacobian,F,res in zip(ids,J,newF,residuals):motor[idx]+=(jacobian.T@F+res)/kp[idx]
  arm=np.array(row['arm_q'])+initial[:7]-z['robot_q'][:7];allq=np.r_[arm,motor];margin=float(np.minimum(allq-np.r_[f.kin.lower,f.g.w.lower],np.r_[f.kin.upper,f.g.w.upper]-allq).min());error=float(np.linalg.norm((np.r_[newF.sum(0),np.cross(P-com,newF).sum(0)]-wrench)*scale));assert margin>0 and ratio.max()<=.800001 and error<1e-5,(row['index'],margin,ratio,error,wrench.tolist(),newF.tolist(),P.tolist())
  frames=max(1,int(np.ceil(max(abs(allq[:7]-prev[:7]).max()/.004,abs(allq[7:]-prev[7:]).max()/.012))));clock+=frames/30;rows.append(dict(time_s=clock,arm_q=arm.tolist(),hand_q=motor.tolist()));checks.append(dict(active_contacts=active.tolist(),total_normal_proxy_N=float(normal_load.sum()),normal_knife=normals.tolist(),index=row['index'],contact_force_proxy_knife_N=newF.tolist(),friction_ratio=ratio.tolist(),wrench_error_scaled=error,minimum_motor_margin_rad=margin));prev=allq
 rows.append(dict(rows[-1],time_s=clock+1.5));out=dict(required_actual_source=str(src),rows=rows,development_abort_on_translation_m=.04,scope=__doc__);(a.output/'motor.json').write_text(json.dumps(out,indent=2));(a.output/'wrench-proxy-audit.json').write_text(json.dumps(dict(captured_force_proxy_N=forces.tolist(),captured_wrench_proxy=wrench.tolist(),checks=checks,seconds=rows[-1]['time_s'],scope=__doc__),indent=2));record('acquired_surface_rolling_motor_prepared_v884',[str(a.output/'motor.json'),str(a.output/'wrench-proxy-audit.json')],dict(seconds=rows[-1]['time_s'],maximum_friction_ratio=max(max(r['friction_ratio'])for r in checks),scope=__doc__),next_step='Oneactualshortrollingnative, samecapturednormal andcoupledwrenchproxy; evaluateactualrelativeyaw/carry/H thencontinuegoal');print(json.dumps(dict(seconds=rows[-1]['time_s'],captured_force_proxy_N=forces.tolist())))
if __name__=='__main__':main()
