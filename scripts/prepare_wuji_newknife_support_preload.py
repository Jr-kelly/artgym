"""Estimate-only support contact IK and inverse-static normal motor preload.
The requested normal forces are model targets, not measured contact forces.
No physics state, load identity, or contact truth enters this preparation.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--actuator-spec',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True)
 for name in ['motor-plan.json','reference.json','localization.json','calibration.json','adaptation-audit.json']:
  shutil.copy2(a.base/name,a.output/name)
 shutil.copytree(a.base/'estimated-collision',a.output/'estimated-collision')
 plan=json.loads((a.base/'motor-plan.json').read_text());act=json.loads(a.actuator_spec.read_text());kp=np.array(act['kp'])[act['hand_indices']];g=DigitGeometry();h=g.w;w=np.array(plan['wrist_in_knife']);q=np.array(plan['touch_q']);closed=np.array(plan['close_q']);width,thickness,length=plan['initial_geometry_estimate']['handle_size_WTL_m'];points=[];rows=[];fingers=['index','middle','pinky']
 for f in fingers:
  ids=[h.names.index('hand_r_'+f+'_joint'+str(i)) for i in range(1,5)];link='hand_r_'+f+'_pad_link';vertices=np.concatenate([v for v,_ in g.meshes[link]])
  def point(x):
   candidate=q.copy();candidate[ids]=x;m=w@h.forward(candidate)[link];v=vertices@m[:3,:3].T+m[:3,3];weights=np.exp((v[:,1]-v[:,1].max())/.0002);return weights@v/weights.sum()
  prior=q[ids].copy();target=point(prior);target[1]=-thickness/2
  fit=least_squares(lambda x:np.r_[(point(x)-target)*1000,(x-prior)*.02],prior,bounds=(h.lower[ids]+.005,h.upper[ids]-.005),max_nfev=200)
  assert np.linalg.norm(point(fit.x)-target)<.00005
  q[ids]=fit.x;points.append(point(fit.x));m=w@h.forward(q)[link];local=(points[-1]-m[:3,3])@m[:3,:3]
  jac=np.zeros((3,4))
  for k,index in enumerate(ids):
   dq=q.copy();dq[index]+=1e-5;dm=w@h.forward(dq)[link];jac[:,k]=(dm[:3,:3]@local+dm[:3,3]-points[-1])/1e-5
  rows.append(dict(finger=f,ids=ids,contact_m=points[-1].tolist(),jacobian_m_rad=jac.tolist(),touch_q=fit.x.tolist()))
 # Nominal measured mass; unknown COM approximated at body origin for this
 # preload model. World gravity orientation comes from the initial estimate.
 world=np.array(plan['object_world_matrix']);normal_weight=.055*9.80665*world[2,1];thumb_N=1.2;thumb_z=-.02205+plan['initial_geometry_estimate']['slider_contact_shift_m'][2];points=np.array(points)
 forces=np.linalg.solve(np.array([np.ones(3),points[:,0],points[:,2]]),[thumb_N+normal_weight,0.,thumb_N*thumb_z]);assert np.all(forces>0)
 for row,force in zip(rows,forces):
  ids=row['ids'];jac=np.array(row['jacobian_m_rad']);delta=jac.T@np.array([0,force,0])/kp[ids];closed[ids]=q[ids]+delta;row.update(requested_normal_proxy_N=float(force),motor_preload_rad=delta.tolist())
 margin=float(np.minimum(closed-h.lower,h.upper-closed).min())
 if margin<.005-1e-7:
  (a.output/'support-preload-rejected.json').write_text(json.dumps(dict(minimum_margin_rad=margin,closed_q=closed.tolist(),violating_joints=[h.names[i] for i in np.where(np.minimum(closed-h.lower,h.upper-closed)<.005-1e-7)[0]],rows=rows),indent=2))
 assert margin>=.005-1e-7, 'Original joint reserve violated: %.9f rad'%margin
 plan.update(touch_q=q.tolist(),close_q=closed.tolist(),support_inverse_static_preload=dict(scope=__doc__,mass_estimate_kg=.055,COM_assumption_m=[0,0,0],thumb_normal_proxy_N=thumb_N,normal_weight_N=float(normal_weight),rows=rows,actuator_spec=str(a.actuator_spec)))
 plan['close_waypoints']=[dict(fraction=0.,q=plan['open_q']),dict(fraction=2/3,q=plan['touch_q']),dict(fraction=1.,q=plan['close_q'])]
 (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2));(a.output/'support-preload-audit.json').write_text(json.dumps(plan['support_inverse_static_preload'],indent=2));print(json.dumps(plan['support_inverse_static_preload']))
if __name__=='__main__':main()
