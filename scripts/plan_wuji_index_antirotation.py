"""Index contact insertion with fixed actual settled nominal grasp geometry.
Keep middle/pinky support and thumb contact-reference sites; real authored
index meshes/limits/self-collision, no auxiliary body restraint or force.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,minimize
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 j=json.loads(a.plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;w=np.array(j['wrist_in_knife']);q0=np.array(j['touch_q']);v=np.concatenate([v for v,_ in g.meshes['hand_r_index_pad_link']]);hull=ConvexHull(v);centers=v[hull.simplices].mean(1);normals=hull.equations[:,:3];rng=np.random.default_rng(2026100451);results=[]
 for name,n,target in [('left-corner',np.array([-1.,-1.,0])/np.sqrt(2),np.array([-.0082,-.0062,.035])),('left-side',np.array([-1.,0.,0]),np.array([-.0082,-.001,.035]))]:
  def sample(x):
   q=q0.copy();q[:4]=x;mat=w@h.forward(q)['hand_r_index_pad_link'];vertices=v@mat[:3,:3].T+mat[:3,3];pr=vertices@n;weight=np.exp(-(pr-pr.min())/.0002);point=weight@vertices/weight.sum();fc=centers@mat[:3,:3].T+mat[:3,3];support=fc@n<=pr.min()+.0004;facing=float((normals@mat[:3,:3].T@(-n))[support].max()) if support.any() else -1.;knife=g.minimum_gap(q,w,j['planning_slider_m'],'index');selfgap=min(r['gap_lower_bound_m'] for r in g.self_gaps(q,'index',certify_clearance_m=.000015));return point,facing,knife,selfgap
  def errors(x):
   point,facing,knife,selfgap=sample(x);desired=target.copy();desired[2]=np.clip(point[2],.005,.065)
   return np.r_[(point-desired)*500,min(facing-.25,0)*2,min(knife-.000005,0)*1000,min(selfgap-.000015,0)*1000,.01*(x-q0[:4])]
  def constraints(x):
   point,facing,knife,selfgap=sample(x);return np.r_[(.0005-abs(point[:2]-target[:2]))*1000,(point[2]-.005)*1000,(.065-point[2])*1000,facing-.25,(knife-.000005)*1000,(selfgap-.000015)*1000]
  best=None;start=time.monotonic()
  for seed in [q0[:4]]+[np.clip(q0[:4]+rng.normal(0,.3,4),h.lower[:4]+.015,h.upper[:4]-.015) for _ in range(3)]:
   lo=h.lower[:4]+.015;hi=h.upper[:4]-.015;fit=least_squares(errors,np.clip(seed,lo,hi),bounds=(lo,hi),max_nfev=100);hard=minimize(lambda x:float(np.sum(errors(x)**2)),fit.x,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=100,ftol=1e-10));value=float(constraints(hard.x).min())
   if best is None or value>best[0]:best=(value,hard.x.copy(),hard.message)
   if value>=-1e-4:break
  value,x,message=best;point,facing,knife,selfgap=sample(x);out=dict(j);out['touch_q'][:4]=x.tolist();out['active_fingers']=['thumb','index','middle','pinky'];out['contact_normals'][1]=n.tolist();out['contact_points'][1]=point.tolist();out['index_antirotation_audit']=dict(passed=value>=-1e-4,normal=n.tolist(),point=point.tolist(),minimum_knife_gap_m=float(knife),minimum_self_gap_m=float(selfgap),facing=facing,message=message,minimum_constraint=value,seconds=time.monotonic()-start,scope=__doc__);(a.output/(name+'.json')).write_text(json.dumps(out,indent=2));results.append(out['index_antirotation_audit']);print(json.dumps(out['index_antirotation_audit']),flush=True)
 (a.output/'summary.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
