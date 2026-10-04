"""One distinct contact-topology hypothesis: opposite lower-edge ring brace.

Pickup targets remain the successful planned closure. Ring adds an opposed
lateral lever after lift; nominal finite-PD preload is not a force command.
Original robot/object meshes, limits and dense self gates are mandatory.
"""
import argparse,copy,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares,minimize
from scipy.spatial import ConvexHull
from scripts.g2_contact_geometry import DigitGeometry

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--motor-plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);motor=json.loads(a.motor_plan.read_text());g=DigitGeometry(max_face_axes=10000,knife_spec='research/robust-knife-family-20261003/real-knife-asset-spec.json');h=g.w;w=np.asarray(motor['wrist_in_knife']);q0=np.asarray(motor['post_lift_close_q']);ids=np.array([h.names.index('hand_r_ring_joint%d'%j) for j in range(1,5)]);vertices=np.concatenate([v for v,_ in g.meshes['hand_r_ring_pad_link']]);hull=ConvexHull(vertices);centers=vertices[hull.simplices].mean(1);normals=hull.equations[:,:3];normal=np.array([0.,-1.,0.]);size=np.asarray(motor['initial_geometry_estimate']['handle_size_WTL_m']);target=np.array([size[0]/2-.002,-size[1]/2-.0002,0.]);low=h.lower[ids]+.015;high=h.upper[ids]-.015;start=time.monotonic()
    def full(x):q=q0.copy();q[ids]=x;return q
    def point(q):
        frame=w@h.forward(q)['hand_r_ring_pad_link'];v=vertices@frame[:3,:3].T+frame[:3,3];pr=v@normal;weights=np.exp(-(pr-pr.min())/.0002);weights/=weights.sum();pc=weights@v;fc=centers@frame[:3,:3].T+frame[:3,3];support=fc@normal<=pr.min()+.0004;facing=float((normals@frame[:3,:3].T@(-normal))[support].max()) if support.any() else -1.
        return pc,facing
    def evaluate(x):
        q=full(x);pc,facing=point(q);gap=g.minimum_gap(q,w,motor['planning_slider_m'],'ring');selfgap=min(r['gap_lower_bound_m'] for r in g.self_gaps(q,'ring',certify_clearance_m=.0001));return pc,facing,gap,selfgap
    def residual(x):
        pc,facing,gap,selfgap=evaluate(x);desired=target.copy();desired[2]=np.clip(pc[2],-.020,.020)
        return np.r_[(pc-desired)*500,min(facing-.25,0)*2,min(gap-.000005,0)*1000,min(selfgap-.0001,0)*1000,.01*(x-q0[ids])]
    def constraints(x):
        pc,facing,gap,selfgap=evaluate(x)
        return np.r_[(.0005-abs(pc[:2]-target[:2]))*1000,(pc[2]+.020)*1000,(.020-pc[2])*1000,facing-.25,(gap-.000005)*1000,(selfgap-.0001)*1000]
    fit=least_squares(residual,np.clip(q0[ids],low,high),bounds=(low,high),max_nfev=100);hard=minimize(lambda x:float(np.sum(residual(x)**2)),fit.x,method='SLSQP',bounds=list(zip(low,high)),constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=120,ftol=1e-10));pc,facing,gap,selfgap=evaluate(hard.x);passed=bool(constraints(hard.x).min()>=-1e-4);audit=dict(passed=passed,minimum_constraint=float(constraints(hard.x).min()),target_knife_m=target.tolist(),touch_point_knife_m=pc.tolist(),facing=facing,minimum_knife_gap_m=float(gap),minimum_self_gap_m=float(selfgap),touch_ring_q=hard.x.tolist(),optimizer_message=str(hard.message),seconds=time.monotonic()-start,scope=__doc__)
    if passed:
        touch=full(hard.x);desired=pc+np.array([0.,.0005,0.])
        def preload_error(x):q=full(x);p,_=point(q);return np.r_[(p-desired)*500,.01*(x-hard.x)]
        preload=least_squares(preload_error,hard.x,bounds=(np.maximum(low,hard.x-.08),np.minimum(high,hard.x+.08)),max_nfev=100);closed=full(preload.x);position_error=float(np.linalg.norm(point(closed)[0]-desired));minimum_self=min(r['gap_lower_bound_m'] for r in g.self_gaps(closed,'ring',certify_clearance_m=.0001));audit.update(preload_position_error_m=position_error,preload_self_gap_m=float(minimum_self),preload_offset_m=.0005,preload_scope='Known position compression hypothesis under unchanged finitePD/torque; not measured orconstantforce');passed=passed and position_error<.00005 and minimum_self>=.0001-1e-7;audit['passed']=bool(passed)
        if passed:
            out=copy.deepcopy(motor);out['post_lift_close_q']=closed.tolist();out['post_lift_preload_seconds']=[12.,14.];out['post_lift_ring_brace']=audit;out['active_fingers']=['thumb','index','middle','ring','pinky'];out['excluded_fingers']=[];(a.output/'motor-plan.json').write_text(json.dumps(out,indent=2))
    (a.output/'geometry-audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit),flush=True)
    if not passed:raise SystemExit(2)
if __name__=='__main__':main()
