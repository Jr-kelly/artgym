"""Source-matched open preform with original real-knife/table/hand collision meshes.

Retains the selected functional wrist/contact layout. Only open finger posture
is optimized; desired closure contacts may load the knife through finite PD.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--localization',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 plan=json.loads(a.plan.read_text());world=np.asarray(json.loads(a.localization.read_text())['object_world_matrix']);w=np.asarray(plan['wrist_in_knife']);g=DigitGeometry(knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;normal=np.asarray(plan['contact_normals']);touch=np.asarray(plan['touch_q']);prior=np.asarray(plan['open_q']);parts=g.knife_geometry.collision_parts(-.03267458688196273)
 def geometry(q):
  frames=h.forward(q);knife=[];table=[];contacts=[]
  for name,meshes in g.meshes.items():
   m=w@frames[name]
   for v,n in meshes:
    vv=v@m[:3,:3].T+m[:3,3];nn=n@m[:3,:3].T
    for part in parts:
     ax=np.r_[nn,part['normals']];pa=vv@ax.T;pb=part['vertices']@ax.T;knife.append(float(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max()))
    vw=vv@world[:3,:3].T+world[:3,3];ax=np.r_[np.eye(3),nn@world[:3,:3].T];proj=(vw-np.array([.60,-.25,.725]))@ax.T;radius=abs(ax)@np.array([.30,.40,.025]);table.append(float(np.maximum(proj.min(0)-radius,-radius-proj.max(0)).max()))
  for f,n in zip(FINGERS,normal):
   name='hand_r_'+f+'_pad_link';m=w@frames[name];v=np.concatenate([x for x,_ in g.meshes[name]]);vv=v@m[:3,:3].T+m[:3,3];pr=vv@n;weights=np.exp(-(pr-pr.min())/.0002);contacts.append(weights@vv/weights.sum())
  return np.array(knife),np.array(table),np.array(contacts)
 _,_,start=geometry(touch);desired=start+normal*.012
 def cons(q):
  kg,tg,_=geometry(q);return np.r_[(kg-.001)*1000,(tg-.0003)*1000]
 def objective(q):
  _,_,c=geometry(q);return float(np.sum(((c-desired)*150)**2)+.02*np.sum((q-prior)**2))
 fit=minimize(objective,np.clip(prior,h.lower+.005,h.upper-.005),method='SLSQP',bounds=list(zip(h.lower+.005,h.upper-.005)),constraints=[dict(type='ineq',fun=cons)],options=dict(maxiter=120,ftol=1e-9))
 kg,tg,c=geometry(fit.x);passed=bool(cons(fit.x).min()>-1e-4)
 plan['open_q']=fit.x.tolist();plan['close_waypoints']=[dict(fraction=0.,q=fit.x.tolist()),dict(fraction=2/3,q=plan['touch_q']),dict(fraction=1.,q=plan['close_q'])]
 audit=dict(scope=__doc__,minimum_open_knife_gap_m=float(kg.min()),minimum_open_table_gap_m=float(tg.min()),optimizer_success=bool(fit.success),message=fit.message,geometry_passed=passed,closure_table_gaps_m=[float(geometry(fit.x*(1-f)+np.asarray(plan['touch_q'])*f)[1].min()) for f in np.linspace(0,1,21)],next='Actual acquisition path and finite-PD closure/lift physics required; open geometry alone is not successful pickup')
 plan['open_preform_audit']=audit;(a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(a.output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit));assert passed,'Rejected open preform'

if __name__=='__main__':main()
