"""Bounded, CPU-only thumb-versus-four-finger side contact screening.

Plans from an earlier real settled table pose; never writes simulation state.
Candidate contact geometry is neither a force estimate nor a pickup success.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation

from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import transform
from scripts.wuji_kinematics import FINGERS


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-plan', type=Path, required=True)
    p.add_argument('--localization', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--table-height', type=float, default=.75)
    p.add_argument('--constrained-refine', type=Path, help='One bounded hard-constraint refinement of an already recorded candidate; does not change screening thresholds')
    p.add_argument('--convex-free-length', action='store_true', help='Require full-hull separating planes and allow each contact to move along the knife length by up to20mm')
    a = p.parse_args()
    assert not a.convex_free_length or a.constrained_refine
    assert not (a.output/'summary.json').exists()
    a.output.mkdir(parents=True, exist_ok=True)
    geometry = DigitGeometry(max_face_axes=16)
    hand = geometry.w
    base = json.loads(a.source_plan.read_text())
    loc = json.loads(a.localization.read_text())
    knife_world = transform(loc['object'][:3], loc['object'][3:])
    wrist0 = np.asarray(base['wrist_in_knife'])
    q0 = np.asarray(base['touch_q'], dtype=float)
    targets = np.asarray(base['contact_targets'], dtype=float)
    assert np.all(targets[1:, 0] > 0) and targets[0, 0] < 0
    outward = np.array([[-1.,0,0]] + [[1.,0,0]]*4)
    meshes = {name:np.concatenate([mesh[0] for mesh in values]) for name,values in geometry.meshes.items()}
    # Meshes are already convex hull vertices transformed by their URDF origins.
    # All vertices are retained in both optimization and final table audit.
    slider = -.03267458826303482
    boxes = [(np.zeros(3),np.array([.019,.008,.147])/2),
             (np.array([0,.0055,.010624586881962734+slider]),np.array([.01,.003,.03])/2)]

    def unpack(x, movable):
        wrist = wrist0.copy()
        if movable:
            wrist[:3,3] += x[:3]
            wrist[:3,:3] = Rotation.from_rotvec(x[3:6]).as_matrix() @ wrist0[:3,:3]
            q = x[6:26]
        else:
            q = x
        return wrist, q

    def desired(x):
        out=targets.copy()
        if a.convex_free_length:
            out[:,2]+=x[26:31]
        return out

    def convex_gaps(wrist,q,vertices):
        frames=hand.forward(q);gaps=[]
        for name,values in geometry.meshes.items():
            frame=wrist@frames[name]
            axes=np.r_[np.eye(3),np.concatenate([n for _,n in values])@frame[:3,:3].T]
            axes/=np.linalg.norm(axes,axis=1)[:,None]
            projection=vertices[name]@axes.T
            for center,half in boxes:
                lo=center@axes.T-abs(axes)@half;hi=center@axes.T+abs(axes)@half
                gaps.append(float(np.maximum(projection.min(0)-hi,lo-projection.max(0)).max()))
        return np.asarray(gaps)

    def sample(x, movable):
        wrist, q = unpack(x, movable)
        local_frames = hand.forward(q)
        frames = {name:wrist@frame for name,frame in local_frames.items()}
        vertices = {name:v@frames[name][:3,:3].T+frames[name][:3,3] for name,v in meshes.items()}
        points, directions = [], []
        for finger,n in zip(FINGERS,outward):
            name = 'hand_r_%s_pad_link' % finger
            v = vertices[name]
            proj = v@n
            weights = np.exp(-(proj-proj.min())/.0003)
            weights /= weights.sum()
            points.append(weights@v)
            directions.append(frames[name][:3,0])
        return wrist, q, vertices, np.asarray(points), np.asarray(directions)

    def residual(x, movable, seed):
        wrist,q,vertices,points,directions = sample(x,movable)
        errors = [(points-desired(x)).ravel()*200, (directions+outward).ravel()*.18]
        for v in vertices.values():
            world_height = v@knife_world[2,:3] + knife_world[2,3]
            errors.append(np.minimum(world_height-a.table_height-.0005,0)*250)
            for center,half in boxes:
                signed = np.max(abs(v-center)-half,axis=1)
                errors.append(np.minimum(signed+.0002,0)*150)
        errors.append((q-seed)*.02)
        palm_world_up = (knife_world[:3,:3]@wrist[:3,:3])[2,0]
        errors.append(np.array([max(palm_world_up+.5,0)*3]))
        if movable:
            errors.append(x[:3]*1.5)
            errors.append(x[3:6]*.05)
        if a.convex_free_length:
            errors.append(x[26:31]*.2)
        return np.concatenate(errors)

    candidates = [
            ('fixed-old-wrist-all-five-pads',False,False),
            ('bounded-wrist-all-five-pads',True,False),
            ('bounded-wrist-less-flexed-seed',True,True)]
    if a.constrained_refine:
        candidates = [('hard-constraint-refinement',True,False)]
    rows = []
    for i,(name,movable,flatter_seed) in enumerate(candidates):
        seed = q0.copy()
        if flatter_seed:
            for finger in FINGERS[1:]:
                for number in [3,4]:
                    k = hand.names.index('hand_r_%s_joint%d' % (finger,number))
                    seed[k] = min(seed[k],.8)
        if movable:
            x0 = np.r_[np.zeros(6),seed]
            lower = np.r_[np.full(3,-.025),np.full(3,-.35),hand.lower]
            upper = np.r_[np.full(3,.025),np.full(3,.35),hand.upper]
        else:
            x0, lower, upper = seed.copy(), hand.lower, hand.upper
        start = time.time()
        if a.constrained_refine:
            prior = json.loads(a.constrained_refine.read_text())
            relative = np.asarray(prior['wrist_in_knife'])
            seed = np.asarray(prior['touch_q'])
            x0 = np.r_[relative[:3,3]-wrist0[:3,3],
                Rotation.from_matrix(relative[:3,:3]@wrist0[:3,:3].T).as_rotvec(),seed]
            if a.convex_free_length:
                x0=np.r_[x0,np.zeros(5)]
                lower=np.r_[lower,np.maximum(-.02,-.0685-targets[:,2])]
                upper=np.r_[upper,np.minimum(.02,.0685-targets[:,2])]
            def inequalities(x):
                wrist,q,vertices,points,directions = sample(x,True)
                height = np.array([(v@knife_world[2,:3]+knife_world[2,3]-a.table_height).min() for v in vertices.values()])
                facing = np.sum(directions*(-outward),axis=1)
                palm_up = (knife_world[:3,:3]@wrist[:3,:3])[2,0]
                bounds=np.r_[(height-(.00055 if a.convex_free_length else .0005))*1000,
                    facing-(.32 if a.convex_free_length else .3), -.5-palm_up,
                    (.001-np.linalg.norm(points-desired(x),axis=1))*1000]
                if a.convex_free_length:
                    # Positive face-axis gaps are conservative certificates even
                    # without edge axes; negative means no certificate, not depth.
                    gaps=convex_gaps(wrist,q,vertices)
                    z=desired(x)[1:,2]
                    bounds=np.r_[bounds,(gaps-.00001)*1000,(z[:-1]-z[1:]-.012)*1000]
                return bounds
            fit = minimize(lambda x:float(np.sum(residual(x,True,seed)**2)),
                np.clip(x0,lower+1e-7,upper-1e-7),method='SLSQP',bounds=list(zip(lower,upper)),
                constraints=[dict(type='ineq',fun=inequalities)],options=dict(maxiter=160,ftol=1e-10))
            cost = float(fit.fun)
        else:
            fit = least_squares(residual,np.clip(x0,lower+1e-7,upper-1e-7),
                args=(movable,seed),bounds=(lower,upper),max_nfev=120,diff_step=1e-5)
            cost = float(fit.cost)
        wrist,q,vertices,points,directions = sample(fit.x,movable)
        final_targets=desired(fit.x)
        errors = np.linalg.norm(points-final_targets,axis=1)
        table = {n:float((v@knife_world[2,:3]+knife_world[2,3]-a.table_height).min()) for n,v in vertices.items()}
        facing = np.sum(directions*(-outward),axis=1)
        precheck = bool(errors.max()<=.001 and min(table.values())>=.0005 and facing.min()>.3)
        row = dict(name=name,scope='Geometry only; all five digits requested, zero physical execution',
            source_plan=str(a.source_plan),settled_localization=str(a.localization),
            movable_wrist=movable,less_flexed_initial_guess=flatter_seed,
            active_fingers=list(FINGERS),excluded_fingers=[],contact_normals=outward.tolist(),
            contact_targets=final_targets.tolist(),contact_points=points.tolist(),
            contact_errors_m=errors.tolist(),pad_facing_cosines=facing.tolist(),
            wrist_in_knife=wrist.tolist(),touch_q=q.tolist(),joint_names=hand.names,
            min_table_clearance_m=min(table.values()),link_table_clearances_m=table,
            palm_world_up_component=float((knife_world[:3,:3]@wrist[:3,:3])[2,0]),
            full_contact_table_precheck=precheck,
            joint_margin_min_rad=float(np.minimum(q-hand.lower,hand.upper-q).min()),
            solver_cost=cost,solver_nfev=fit.nfev,seconds=time.time()-start,
            constrained_refinement_source=str(a.constrained_refine) if a.constrained_refine else None,
            solver_message=str(fit.message),
            full_convex_constraints=a.convex_free_length,
            minimum_convex_separating_gap_m=float(convex_gaps(wrist,q,vertices).min()) if a.convex_free_length else None,
            outstanding='If precheck passes: exact self/body collision, open/close path, G2 reach and real continuous pickup. No readiness is implied.')
        (a.output/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
        rows.append(row)
        print(json.dumps({k:row[k] for k in ['name','contact_errors_m','pad_facing_cosines','min_table_clearance_m','full_contact_table_precheck','seconds']}),flush=True)
    (a.output/'summary.json').write_text(json.dumps(dict(candidates=rows,new_physical_trials=0,new_training_configs=0,
        conclusions='Numerical candidates are only local solves; rejection does not establish global infeasibility. No physics or motor drive parameters changed.'),indent=2)+'\n')


if __name__ == '__main__':
    main()
