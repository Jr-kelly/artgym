"""Offline park a non-contact digit clear of the entire known lift sweep.

Does not alter active contact targets, actuator limits, object state or clocks.
Positive face-axis separation is a geometry certificate only.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_kinematics import FINGERS


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--acquisition-path',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--digit',choices=FINGERS,default='ring');a=p.parse_args();assert not a.output.exists()
    plan=json.loads(a.plan.read_text());assert a.digit not in plan['active_fingers'];g=DigitGeometry(max_face_axes=24,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;k=G2Kinematics();idx=[h.names.index('hand_r_'+a.digit+'_joint'+str(i)) for i in range(1,5)];path=np.array(json.loads(a.acquisition_path.read_text())['lift_q']);wrists=[k.forward(q) for q in path[::4]];parts=g.knife_geometry.collision_parts(plan['planning_slider_m']);w=np.array(plan['wrist_in_knife']);base=np.array(plan['touch_q']);names=[n for n in g.meshes if '_'+a.digit+'_' in n];others=[n for n in g.meshes if not '_'+a.digit+'_' in n and not (n=='hand_r_base_link')];own=[('hand_r_'+a.digit+'_pad_link','hand_r_base_link'),('hand_r_'+a.digit+'_link4','hand_r_base_link')]
    def gaps(x):
        q=base.copy();q[idx]=x;frames=h.forward(q);meshes={n:[(v@frames[n][:3,:3].T+frames[n][:3,3],norm@frames[n][:3,:3].T) for v,norm in mm] for n,mm in g.meshes.items()};out=[]
        for n in names:
            for v,normal in meshes[n]:
                vo=v@w[:3,:3].T+w[:3,3];no=normal@w[:3,:3].T
                for part in parts:
                    axes=np.r_[no,part['normals']];aa=vo@axes.T;bb=part['vertices']@axes.T;out.append(float(np.maximum(aa.min(0)-bb.max(0),bb.min(0)-aa.max(0)).max())-.0001)
                for other in others:
                    for ov,on in meshes[other]:
                        axes=np.r_[normal,on];aa=v@axes.T;bb=ov@axes.T;out.append(float(np.maximum(aa.min(0)-bb.max(0),bb.min(0)-aa.max(0)).max())-.0001)
                for world in wrists:
                    vw=v@world[:3,:3].T+world[:3,3];nw=normal@world[:3,:3].T;axes=np.r_[np.eye(3),nw];pv=(vw-np.array([.6,-.25,.725]))@axes.T;r=abs(axes)@np.array([.3,.4,.025]);out.append(float(np.maximum(pv.min(0)-r,-r-pv.max(0)).max())-.0005)
        out.extend(r['gap_lower_bound_m']-.0001 for r in g.pair_gaps(q,own));return np.array(out)
    lo=h.lower[idx]+.015;hi=h.upper[idx]-.015;seeds=[base[idx],np.array([.6,0,1.2,1.]),np.array([1.,0,1.3,1.3])];rows=[];best=None
    for seed in seeds:
        x=np.clip(seed,lo,hi);fit=minimize(lambda x:float(np.sum((x-np.array([.6,0,1.2,1.]))**2))*.001,x,method='SLSQP',bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=gaps)],options=dict(maxiter=100,ftol=1e-10));gap=float(gaps(fit.x).min());rows.append(dict(success=bool(fit.success),message=fit.message,minimum_constraint_m=gap,q=fit.x.tolist()))
        if gap>=-1e-7:best=fit.x;break
    out=dict(args=vars(a),rows=rows,passed=best is not None,scope='Offline inactive-digit geometry only,31 lift knots; independent full-mesh selected-path audit and physics required. Active contacts unchanged.')
    a.output.mkdir(parents=True)
    if best is not None:
        for key in ['open_q','touch_q','close_q','post_lift_close_q']:
            if key in plan:
                q=np.array(plan[key]);q[idx]=best;plan[key]=q.tolist()
        for row in plan.get('close_waypoints',[]):
            q=np.array(row['q']);q[idx]=best;row['q']=q.tolist()
        plan['inactive_digit_parking']=dict(digit=a.digit,indices=idx,q=best.tolist(),geometry_only=True)
        (a.output/'motor-plan.json').write_text(json.dumps(plan,indent=2))
    (a.output/'audit.json').write_text(json.dumps(out,default=str,indent=2));print(json.dumps(out,default=str),flush=True);assert best is not None


if __name__=='__main__':main()
