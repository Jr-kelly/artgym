"""Force/moment ablation of saved actual contacts; optional hypothetical support."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import linprog


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--omit',nargs='+',default=['thumb']);p.add_argument('--extra-point',type=float,nargs=3);p.add_argument('--extra-normal',type=float,nargs=3,default=[0,-1,0]);a=p.parse_args()
    if a.output.exists():raise ValueError('Preserve old diagnostic')
    d=json.loads(a.source.read_text());points=[v for v in d['points'] if v['finger'] not in a.omit]
    if a.extra_point:points.append(dict(finger='hypothetical',point=a.extra_point,normal=a.extra_normal))
    gravity=np.array(d['gravity_in_object_N']);external=np.r_[gravity,np.cross(d['com_in_object_m'],gravity)];rows=[]
    for mu in [.5,1.,2.,3.]:
        columns=[]
        for v in points:
            normal=np.array(v['normal'],dtype=float);normal/=np.linalg.norm(normal);axis=np.eye(3)[np.argmin(abs(normal))];u=np.cross(normal,axis);u/=np.linalg.norm(u);z=np.cross(normal,u)
            for theta in np.arange(8)*np.pi/4:
                force=-normal+mu*(np.cos(theta)*u+np.sin(theta)*z);columns.append(np.r_[force,np.cross(v['point'],force)])
        W=np.array(columns).T
        for label,n in [('force_only',3),('force_and_moment',6)]:
            result=linprog(np.ones(len(columns)),A_eq=W[:n],b_eq=-external[:n],bounds=(0,None),method='highs')
            rows.append(dict(mu=mu,constraint=label,feasible=bool(result.success),predicted_total_normal_N=float(result.fun) if result.success else None))
    out=dict(source=str(a.source),omit=a.omit,hypothetical_point=a.extra_point,hypothetical_normal=a.extra_normal if a.extra_point else None,results=rows,
        limitation='Static eight-ray friction cones from actual contact normals. Force vs full wrench ablation WITHOUT motor limits. Extra point is a geometric proposal, not a realized contact. Not force measurement or stable-control evidence.')
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))


if __name__=='__main__':main()
