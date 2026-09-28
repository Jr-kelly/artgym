"""Generate open/touch/motor-preload targets, audit approach and G2 flip.

CPU geometry only. Closing targets may compress a free body in physics; they
are not assigned measured finger positions and never imply a force estimate.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation

from scripts.audit_g2_side_pickup_candidate import radius
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.g2_table_collision import ArmTableCollision
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.g2_air_flip import plan_flip
from scripts.wuji_kinematics import FINGERS


def main():
    p=argparse.ArgumentParser()
    for key in ['plan','localization','output']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--opening',type=float,default=.005)
    p.add_argument('--squeeze',type=float,default=.001)
    p.add_argument('--squeeze-per-finger',type=float,nargs=5,help='Explicit thumb/index/middle/ring/pinky motor compression, all in metres; nominal geometry only')
    p.add_argument('--lift',type=float,default=.30)
    p.add_argument('--open-pad-lift',type=float,default=0.,help='Open pads move up in the knife frame by this amount; real motor path, not an object state edit')
    p.add_argument('--flip-degrees',type=float,choices=[-180.,180.],default=180.)
    p.add_argument('--flip-axis',choices=['wrist-forward','knife-length'],default='wrist-forward')
    p.add_argument('--close-via-touch',action='store_true',help='Specify two motor segments instead of direct open-to-close interpolation')
    p.add_argument('--arm-wrist-posture',type=float,help='Use G2 redundant joint7 to select an initial IK posture; original robot limits remain')
    p.add_argument('--hard-close-clearance',action='store_true',help='One constrained closing-path refinement, unchanged requested motor compression')
    p.add_argument('--knife-spec',type=Path)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    original=json.loads(a.plan.read_text());loc=json.loads(a.localization.read_text())
    g=DigitGeometry(max_face_axes=24);h=g.w
    wrist=np.asarray(original['wrist_in_knife']);q0=np.asarray(original['touch_q'])
    object_world=transform(loc['object'][:3],loc['object'][3:])
    from scripts.g2_knife_geometry import KnifeGeometry
    knife=KnifeGeometry(a.knife_spec)
    if a.knife_spec:object_world=knife.table_pose(object_world)
    knife_parts=knife.collision_parts()
    normals=np.asarray(original['contact_normals'])
    vertices={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()}
    normals_local={n:np.concatenate([v for _,v in m]) for n,m in g.meshes.items()}
    boxes=[(np.zeros(3),np.array([.0095,.004,.0735])),
        (np.array([0,.0055,.010624586881962734-.03267458826303482]),np.array([.005,.0015,.015]))]
    graph={}
    for parent,child,_,_,_ in h.joints:
        graph.setdefault(parent,set()).add(child);graph.setdefault(child,set()).add(parent)
    pairs=[]
    for i,n in enumerate(sorted(vertices)):
        near={n}|graph.get(n,set());near|=set().union(*(graph.get(v,set()) for v in list(near)))
        pairs.extend((n,m) for m in sorted(vertices)[i+1:] if m not in near)

    def sample(q):
        frames={n:wrist@f for n,f in h.forward(q).items()}
        vs={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in vertices.items()}
        axes={n:v@frames[n][:3,:3].T for n,v in normals_local.items()}
        points=[];facing=[];gap=[];height=[]
        for finger,normal in zip(FINGERS,normals):
            n='hand_r_%s_pad_link'%finger;v=vs[n];project=v@normal
            weights=np.exp(-(project-project.min())/.0002);weights/=weights.sum()
            points.append(weights@v);facing.append(frames[n][:3,0]@(-normal))
        for n,v in vs.items():
            ax=np.r_[np.eye(3),axes[n]];proj=v@ax.T
            if a.knife_spec:
                for part in knife_parts:
                    ka=np.r_[ax,part['normals']];pa=v@ka.T;pb=part['vertices']@ka.T
                    gap.append(np.maximum(pa.min(0)-pb.max(0),pb.min(0)-pa.max(0)).max())
            else:
                for center,half in boxes:
                    lo=center@ax.T-abs(ax)@half;hi=center@ax.T+abs(ax)@half
                    gap.append(np.maximum(proj.min(0)-hi,lo-proj.max(0)).max())
            height.append((v@object_world[2,:3]+object_world[2,3]-.75).min())
        selfgaps=[]
        constrained_pairs=list(original.get('self_collision_pairs_constrained',[]))+[['hand_r_base_link','hand_r_thumb_link3']]
        for n,m in constrained_pairs:
            ax=np.r_[axes[n],axes[m]];va,vb=vs[n]@ax.T,vs[m]@ax.T
            selfgaps.append(np.maximum(va.min(0)-vb.max(0),vb.min(0)-va.max(0)).max())
        selfgap=min(selfgaps)
        return np.asarray(points),np.asarray(facing),np.asarray(gap),np.asarray(height),selfgap,vs

    def fit_offset(offset):
        values=np.broadcast_to(np.asarray(offset),5)
        opening=bool(np.all(values>0))
        desired=sample(q0)[0]+normals*values[:,None]
        if opening:desired[:,1]-=a.open_pad_lift
        def residual(q):
            points,facing,gap,height,selfgap,_=sample(q)
            parts=[(points-desired).ravel()*500,np.minimum(facing-.32,0),
                np.minimum(height-.0006,0)*600,np.array([min(selfgap-.000015,0)*600]),(q-q0)*.02]
            if opening:parts.append(np.minimum(gap-.000015,0)*500)
            # Endpoint clearance does not guarantee joint-space interpolation
            # clearance. Preserve the same threshold along this actual motion.
            for u in [.25,.5,.75]:
                _,_,_,middle_height,middle_selfgap,_=sample(q0*(1-u)+q*u)
                parts.extend([np.minimum(middle_height-.0006,0)*800,
                    np.array([min(middle_selfgap-.000015,0)*800])])
            return np.concatenate(parts)
        fit=least_squares(residual,q0,bounds=(h.lower+.005,h.upper-.005),max_nfev=160,diff_step=1e-5)
        x=fit.x;info=dict(success=bool(fit.success),nfev=fit.nfev,message=fit.message)
        if a.hard_close_clearance and not opening:
            def constraints(q):
                out=[]
                for u in [.25,.5,.75,1.]:
                    _,_,_,height,selfgap,_=sample(q0*(1-u)+q*u)
                    out.extend([(height.min()-.00055)*1000,(selfgap-.000015)*1000])
                return np.asarray(out)
            hard=minimize(lambda q:float(np.sum(residual(q)**2)),x,method='SLSQP',
                bounds=list(zip(h.lower+.005,h.upper-.005)),constraints=[dict(type='ineq',fun=constraints)],
                options=dict(maxiter=160,ftol=1e-10))
            x=hard.x;info['hard_refinement']=dict(success=bool(hard.success),iterations=hard.nit,message=hard.message)
        info['contact_error_m']=np.linalg.norm(sample(x)[0]-desired,axis=1).tolist()
        return x,info

    squeeze=np.array(a.squeeze_per_finger) if a.squeeze_per_finger else np.full(5,a.squeeze)
    assert (squeeze>0).all() and (squeeze<=.008).all()
    opened,open_fit=fit_offset(a.opening);closed,close_fit=fit_offset(-squeeze)
    result=dict(original,kind='five_finger_side_pinch_motor_plan',source_touch_plan=str(a.plan),
        open_q=opened.tolist(),close_q=closed.tolist(),grasp=0,opening_m=a.opening,squeeze_m=a.squeeze,
        allow_close_overtravel=False,open_fit=open_fit,close_fit=close_fit,
        preload_definition='Geometric compression requested via legal joint motor targets only, not measured positions or forces')
    result['squeeze_per_finger_m']=squeeze.tolist()
    if a.knife_spec:result['knife_spec']=str(a.knife_spec)
    if a.close_via_touch:
        result['close_waypoints']=[dict(fraction=0.,q=opened.tolist()),dict(fraction=2/3,q=q0.tolist()),dict(fraction=1.,q=closed.tolist())]
    result.update(open_pad_lift_m=a.open_pad_lift,planned_flip_degrees=a.flip_degrees,planned_flip_axis=a.flip_axis)
    (a.output/'motor-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    # All nonadjacent convex pairs audited at 21 sampled hand configurations.
    # Closing-command object overlap is separately reported, not executed as a
    # configuration setter. Table and self collision remain disallowed.
    rows=[]
    segments=[('open_to_touch',opened,q0),('touch_to_preload',q0,closed)]
    if not a.close_via_touch:segments.append(('actual_open_to_close_command',opened,closed))
    for phase,qa,qb in segments:
        for u in np.linspace(0,1,61 if phase=='actual_open_to_close_command' else 21):
            q=qa*(1-u)+qb*u;points,facing,gap,height,selfgap,vs=sample(q)
            bad=[]
            for n,m in pairs:
                r=radius(vs[n],vs[m])
                if r is None or r>1e-5:bad.append(dict(pair=[n,m],inscribed_intersection_radius_m=r))
            rows.append(dict(phase=phase,fraction=float(u),table_min_m=float(height.min()),
                knife_gap_min_m=float(gap.min()),self_intersections=bad,
                facing_min=float(facing.min())))
    # Vertical approach with the OPEN hand must remain separated from the
    # resting knife, not merely clear at its final pose.
    _,_,_,_,_,vs=sample(opened)
    corners=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])
    approach_overlaps=[]
    for dz in np.linspace(.16,0,65):
        local_shift=object_world[:3,:3].T@np.array([0,0,dz])
        for n,v in vs.items():
            collision_vertices=[part['vertices'] for part in knife_parts] if a.knife_spec else [center+corners*half for center,half in boxes]
            for bi,kv in enumerate(collision_vertices):
                r=radius(v+local_shift,kv)
                if r is None or r>1e-5:approach_overlaps.append(dict(dz_m=float(dz),hand_link=n,knife_link=bi,radius_m=r))
    arm=G2Kinematics();table=ArmTableCollision(.75)
    target=object_world@wrist;above=target.copy();above[2,3]+=.16
    lift=target.copy();lift[2,3]+=a.lift
    arm_result={};arm_pass=False
    try:
        grasp_q,err=arm.solve(target,np.asarray(loc['grasp_q']))
        if a.arm_wrist_posture is not None:
            grasp_q,err=arm.solve_wrist_posture(target,grasp_q,a.arm_wrist_posture)
        high_q,high_err=arm.solve(above,grasp_q,attempts=1)
        if high_err['position_m']>.001 or high_err['rotation_rad']>.005:raise ValueError('Above-table IK '+str(high_err))
        (a.output/'arm-seed.json').write_text(json.dumps(high_q.tolist(),indent=2)+'\n')
        approach,ad=plan_translation(arm,high_q,target,4,1/30,table)
        lifted,ld=plan_translation(arm,approach[-1],lift,4,1/30,table)
        lifted_object=object_world.copy();lifted_object[2,3]+=a.lift
        flip,fd=plan_flip(arm,arm.forward(lifted[-1]),lifted_object,lifted[-1],a.flip_degrees,10,1/30,table,axis_mode=a.flip_axis)
        arm_result=dict(grasp_ik=err,high_ik=high_err,approach=ad,lift=ld,flip=fd)
        arm_pass=fd['feasible']
    except ValueError as exc:arm_result['failure']=str(exc)
    max_motor_velocity=float(abs(closed-opened).max()*1.875/3.)
    if a.close_via_touch:max_motor_velocity=float(max(abs(q0-opened).max()*1.875/2,abs(closed-q0).max()*1.875))
    hand_pass=bool(all(r['table_min_m']>=.0005 and not r['self_intersections'] and
        (r['phase']!='open_to_touch' or r['knife_gap_min_m']>=-1e-7) for r in rows)
        and not approach_overlaps and max(open_fit['contact_error_m'])<.001)
    audit=dict(hand_path_rows=rows,approach_intersections=approach_overlaps,arm=arm_result,
        hand_path_pass=hand_pass,arm_path_pass=bool(arm_pass),geometric_ready_for_one_physics_trial=bool(hand_pass and arm_pass),
        max_quintic_close_motor_speed_rad_s=max_motor_velocity,
        scope='Sampled CPU motor geometry precheck; actual servo tracking, contact, holding, flip, and flattening remain untested',
        no_state_injection=True,physics_trials=0)
    (a.output/'motion-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(hand_path_pass=hand_pass,arm_path_pass=arm_pass,
        hand_failures=[r for r in rows if r['table_min_m']<.0005 or r['self_intersections'] or (r['phase']=='open_to_touch' and r['knife_gap_min_m']< -1e-7)],
        approach_intersections=approach_overlaps,open_fit=open_fit,close_fit=close_fit,
        arm_failure=arm_result.get('failure',arm_result.get('flip',{}).get('failure')))),flush=True)


if __name__=='__main__':main()
