"""Offline scheduled thumb travel with cooperative, nominal impedance targets.

No current object/slider/contact values enter execution. Planned force is a
nominal motor preload, not measured force or constant-force regulation. All
motors retain the authored stiffness and joint/effort limits. The script follows
the same legal support target span and recursive thumb action memory as R800.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from omegaconf import OmegaConf
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--screen',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--axial-force',type=float,default=.12);p.add_argument('--friction',type=float,default=1.1);p.add_argument('--support-span',type=float,default=.04);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 plan=json.loads(a.plan.read_text());screen=json.loads(a.screen.read_text());g=DigitGeometry();hand=g.w;w=np.array(plan['wrist_in_knife']);world=np.array(plan['object_world_matrix']);q0=np.array(plan['touch_q']);closed=np.array(plan['close_q']);kp=np.array(OmegaConf.load('isaacgymenvs/cfg/hand/wuji_paper_official_actuator.yaml').dof_props.stiffness);active=[FINGERS.index(f) for f in plan['active_fingers']];normal=np.array(plan['contact_normals'])[active];count=len(active);original_force=np.array(plan['equilibrium_audit']['planned_force_on_knife_N']);gravity=world[:3,:3].T@np.array([0,0,-.035*9.81]);t1=np.array([np.eye(3)[np.argmin(abs(n))] for n in normal]);t2=np.cross(normal,t1)
 def points(q):
  frames=hand.forward(q);out=[]
  for idx,n in zip(active,normal):
   link='hand_r_'+FINGERS[idx]+'_pad_link';mat=w@frames[link];v=np.concatenate([v for v,_ in g.meshes[link]]);v=v@mat[:3,:3].T+mat[:3,3];proj=v@n;weights=np.exp(-(proj-proj.min())/.0002);weights/=weights.sum();out.append(weights@v)
  return np.array(out)
 def forces(flat):
  x=flat.reshape(count,3);return -normal*x[:,0:1]+t1*x[:,1:2]+t2*x[:,2:3]
 seed=np.c_[-(original_force*normal).sum(-1),(original_force*t1).sum(-1),(original_force*t2).sum(-1)].ravel();branches={};allpass=True
 for branch,axial in [('extend',a.axial_force),('hold',0.),('retract',-a.axial_force)]:
  rows=[];previous=seed.copy()
  for item in screen['rows']:
   shift=item['shift_m'];q=q0.copy();q[16:]=item['q_thumb'];contact=points(q);jac=np.empty((count,3,20))
   for j in range(20):
    delta=np.zeros(20);delta[j]=1e-5;jac[:,:,j]=(points(q+delta)-points(q-delta))/2e-5
   com=np.array([0,.0075,-.02205+shift])*(.006/.035)
   lo=np.maximum(-.20,hand.lower+.005-q);hi=np.minimum(.20,hand.upper-.005-q)
   lo[:16]=np.maximum(lo[:16],closed[:16]-a.support_span-q[:16]);hi[:16]=np.minimum(hi[:16],closed[:16]+a.support_span-q[:16])
   def offsets(x):return np.einsum('fij,fi->j',jac,forces(x))/kp
   def equality(x):
    f=forces(x);return np.r_[f.sum(0)+gravity,np.cross(contact-com,f).sum(0)*100,f[active.index(0),2]-axial]
   def inequality(x):
    v=x.reshape(count,3);d=offsets(x);return np.r_[a.friction*v[:,0]-np.linalg.norm(v[:,1:],axis=-1),d-lo,hi-d]
   desired=original_force.copy();desired[active.index(0),2]=axial
   result=minimize(lambda x:float(((forces(x)-desired)**2).sum()+.05*((x-previous)**2).sum()),previous,method='SLSQP',bounds=[b for _ in active for b in [(0.08,2.),(-2.,2.),(-2.,2.)]],constraints=[dict(type='eq',fun=equality),dict(type='ineq',fun=inequality)],options=dict(maxiter=250,ftol=1e-11))
   ok=bool(np.max(abs(equality(result.x)))<1e-5 and np.min(inequality(result.x))>=-1e-6);allpass&=ok
   target=q+offsets(result.x);target[12:16]=closed[12:16]
   rows.append(dict(shift_m=shift,q_target=target.tolist(),nominal_force_on_knife_N=forces(result.x).tolist(),wrench_residual=equality(result.x).tolist(),minimum_constraint_margin=float(np.min(inequality(result.x))),feasible=ok,optimizer_success=bool(result.success),message=result.message,support_target_delta_from_closed_rad=(target[:16]-closed[:16]).tolist()));previous=result.x
  branches[branch]=rows;print(json.dumps(dict(branch=branch,feasible=sum(r['feasible'] for r in rows),total=len(rows))),flush=True)
 report=dict(args=vars(a),branches=branches,all_feasible=bool(allpass),scope='Offline modeled contact wrench and original-gain motor targets; does not prove actual pressure, collision-free measured states, or operation success',control='Known scheduled40mm task; three-second travel and two-second hold; same bounded support span and recursive thumb issued target memory')
 (a.output/'scheduled-wrench.json').write_text(json.dumps(report,default=str,indent=2));assert allpass,'Recorded infeasible targets must not be executed'
if __name__=='__main__':main()
