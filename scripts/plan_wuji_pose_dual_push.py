"""Pose-conditioned two-pad side push with finite travel in both digits.
New mechanism: start bent, leaving extension travel for contact-preserving correction.
"""
import json,numpy as np
from pathlib import Path
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform,G2Kinematics
p=Path('runs/flat-table-20261006/preparation/pose-dual-push-v67');p.mkdir(parents=True,exist_ok=False)
g=DigitGeometry();z=np.load('runs/flat-table-20261006/development/fixed-support-middle-v66/simulation/trace.npz');i=np.argmin(abs(z['time']+20.05));O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7]);L=np.linalg.inv(O)@W;q=np.zeros(20);q[4]=.09;q[16]=.0475;names=['hand_r_index_pad_link','hand_r_middle_pad_link'];points=[np.array([-.00770174,-.00235265,-.00788409]),np.array([-.00779631,-.00051811,-.00687698])];targets=np.array([[.0095,.0038,.0194],[.0095,.004,-.0151]])
def decode(x):
 l=L.copy();l[:3,3]=x[:3];qq=q.copy();qq[:8]=x[3:];return l,qq
def res(x):
 l,qq=decode(x);f=g.w.forward(qq);ps=np.array([(l@f[n])[:3,:3]@v+(l@f[n])[:3,3] for n,v in zip(names,points)])
 return np.r_[(ps-targets).ravel()*200,(qq[[0,2,3,4,6,7]]-.25)*.1]
x=np.r_[L[:3,3],np.array([.25,0,.25,.25,.25,0,.25,.25])];lo=np.r_[L[:3,3]-.08,g.w.lower[:8]+.001];hi=np.r_[L[:3,3]+.08,g.w.upper[:8]-.001];fit=least_squares(res,np.clip(x,lo+1e-7,hi-1e-7),bounds=(lo,hi),max_nfev=150);l,qq=decode(fit.x);f=g.w.forward(qq);ps=np.array([(l@f[n])[:3,:3]@v+(l@f[n])[:3,3] for n,v in zip(names,points)]);print('errors',np.linalg.norm(ps-targets,axis=1),'q',qq[:8],flush=True)
s=dict(wrist_in_knife=l.tolist(),hand_q=qq.tolist(),material_points=[v.tolist() for v in points],material_links=names,contact_targets=targets.tolist(),contact_errors_m=np.linalg.norm(ps-targets,axis=1).tolist(),source_trace='fixed-support-middle-v66',source_time_s=float(z['time'][i]),pose_source='sim_oracle',scope=__doc__);(p/'spec.json').write_text(json.dumps(s,indent=2))
# Preserve original whole-supported initial placement, table and safe withdrawal.
old=json.load(open('runs/flat-table-20261006/preparation/push-corner-v10/prefix.json'));k=G2Kinematics();center=np.array([.37,-.5695,.7541]);first=O@l;first[:3,3]+=center-O[:3,3];above=first.copy();above[2,3]+=.075;push=first.copy();push[:2,3]-=.06;release=push.copy();release[:3,3]+=O[:3,0]*.05;retreat=release.copy();retreat[2,3]+=.18;outside=retreat.copy();outside[:2,3]=[.17,-.70];keys=[(0,above),(1,above),(3,first),(7,push),(8,release),(10,retreat),(12,outside)];qa=np.array(old['rows'][0]['arm_q']);rows=[]
for (ta,aa),(tb,bb) in zip(keys[:-1],keys[1:]):
 for t in np.arange(ta,tb,1/30):
  u=(t-ta)/(tb-ta);u=u**3*(10-15*u+6*u*u);mat=aa.copy();mat[:3,3]=(1-u)*aa[:3,3]+u*bb[:3,3];qa,e=k.solve_near(mat,qa);rows.append(dict(time_s=float(t),arm_q=qa.tolist(),hand_q=qq.tolist(),ik=e))
# High branch transition regenerated from actual new withdrawal endpoint.
endqa=np.array(old['rows'][540]['arm_q'])
for t in np.arange(12,18,1/30):
 u=(t-12)/6;u=u**3*(10-15*u+6*u*u);rows.append(dict(time_s=float(t),arm_q=((1-u)*qa+u*endqa).tolist(),hand_q=((1-u)*qq+u*np.array(old['rows'][540]['hand_q'])).tolist()))
rows+=old['rows'][540:];old['rows']=rows;old['scope']=__doc__;old['pose_dual_push_spec']=str(p/'spec.json');(p/'prefix.json').write_text(json.dumps(old,indent=2))
