"""Finite palm-down thumb-versus-four-pad geometry search, no simulator imports."""
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
    p=argparse.ArgumentParser()
    p.add_argument('--localization',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--refine',type=Path,action='append',default=[],help='Bounded hard-constraint follow-up; contact height can use the actual side face instead of the arbitrary old y=-1mm line')
    p.add_argument('--avoid-thumb-palm',action='store_true',help='Add the exact-audit identified thumb-link3 / palm separation constraint')
    p.add_argument('--balance-long-axis',action='store_true',help='Bound thumb contact within4mm of the four-pad longitudinal centroid; geometric moment-arm hypothesis, not a measured force condition')
    p.add_argument('--balanced-margin',action='store_true',help='Leave0.08rad finger opening margin and request <=10mm longitudinal offset, allowing a closer wrist planning box')
    p.add_argument('--self-collision-audit',type=Path,help='Add all exact-audit identified link pairs as conservative separating-plane constraints')
    p.add_argument('--long-spacing',type=float,default=.012)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    g=DigitGeometry(max_face_axes=20);h=g.w
    object_world=transform(*[json.loads(a.localization.read_text())['object'][v] for v in [slice(0,3),slice(3,7)]])
    base_rotation=np.array([[0.,0,1],[1.,0,0],[0,1.,0]])
    normals=np.array([[-1.,0,0]]+[[1.,0,0]]*4)
    # Long-axis slots may be used anywhere within them; no fixed old contact z.
    zmin=np.array([-.02,.019,-.007,-.031,-.060])
    zmax=np.array([.06,.063,.024,.002,-.019])
    boxes=[(np.zeros(3),np.array([.0095,.004,.0735])),
        (np.array([0,.0055,-.02205]),np.array([.005,.0015,.015]))]
    meshes={n:np.concatenate([v for v,_ in m]) for n,m in g.meshes.items()}
    axes={n:np.concatenate([v for _,v in m]) for n,m in g.meshes.items()}
    self_pairs=[]
    if a.self_collision_audit:self_pairs=[tuple(r['pair']) for r in json.loads(a.self_collision_audit.read_text())['hand_intersections']]
    if a.avoid_thumb_palm:self_pairs.append(('hand_r_base_link','hand_r_thumb_link3'))
    self_pairs=list(dict.fromkeys(self_pairs))
    def geometry(x):
        wrist=transform(x[:3]);wrist[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@base_rotation
        q=x[6:];frames={n:wrist@t for n,t in h.forward(q).items()}
        vertices={n:v@frames[n][:3,:3].T+frames[n][:3,3] for n,v in meshes.items()}
        contact=[];facing=[];separation=[];height=[]
        for f,normal in zip(FINGERS,normals):
            n='hand_r_%s_pad_link'%f;v=vertices[n];proj=v@normal
            weights=np.exp(-(proj-proj.min())/.0002);weights/=weights.sum()
            contact.append(weights@v);facing.append(frames[n][:3,0]@(-normal))
        for n,v in vertices.items():
            ax=np.r_[np.eye(3),axes[n]@frames[n][:3,:3].T]
            proj=v@ax.T
            for center,half in boxes:
                low=center@ax.T-abs(ax)@half;high=center@ax.T+abs(ax)@half
                separation.append(np.maximum(proj.min(0)-high,low-proj.max(0)).max())
            height.append((v@object_world[2,:3]+object_world[2,3]-.75).min())
        for n,m in self_pairs:
            ax=np.r_[axes[n]@frames[n][:3,:3].T,axes[m]@frames[m][:3,:3].T]
            va,vb=vertices[n]@ax.T,vertices[m]@ax.T
            separation.append(np.maximum(va.min(0)-vb.max(0),vb.min(0)-va.max(0)).max())
        return wrist,q,np.array(contact),np.array(facing),np.array(separation),np.array(height)
    def residual(x,seed,collision_weight):
        wrist,q,contact,facing,gap,height=geometry(x)
        target_y=np.clip(contact[:,1],-.003,.002) if a.refine else np.full(5,-.001)
        xy=contact[:,:2]-np.c_[normals[:,0]*(.0097 if a.refine else .00952),target_y]
        z=contact[:,2];range_error=z-np.clip(z,zmin,zmax)
        residuals=np.r_[xy.ravel()*200,range_error*150,
            np.minimum(z[1:-1]-z[2:]-a.long_spacing,0)*150,
            np.maximum(.6-facing,0)*1.,np.minimum(height-.0007,0)*250,
            np.minimum(gap-.000015,0)*collision_weight,
            (q-seed)*.007,np.maximum((object_world[:3,:3]@wrist[:3,:3])[2,0]+.7,0)*2]
        if a.balance_long_axis:
            zerr=z[0]-z[1:].mean()
            residuals=np.r_[residuals,(zerr-np.clip(zerr,-.008,.008) if a.balanced_margin else zerr)*200]
        return residuals
    lower=np.r_[[-.17,-.10,-.025],[-.6,-.6,-.6],h.lower+.015]
    upper=np.r_[[-.065,-.02,.025],[.6,.6,.6],h.upper-.015]
    thumb_seeds=[[1.46384255,.61801879,-.41471956,-.44764651],
        [1.49269234,.14433740,-.38077782,-.40536288]]
    results=[]
    seeds=list((f,p,t) for f in [.45,.7] for p in [-.3,0.,.3] for t in thumb_seeds)
    if a.refine:
        seeds=[(None,None,None)]*len(a.refine)
        # Previous solutions hit wrist search-box edges; these are planning
        # bounds, not robot joint limits or changes to the physical task.
        lower[:3]=[-.18,-.14,-.060];upper[:3]=[-.06,-.020,.060]
        lower[3:6]=-.9;upper[3:6]=.9
        if a.balance_long_axis:lower[2]=-.085
        if a.balanced_margin:
            assert a.balance_long_axis
            lower[6:]=h.lower+.08;upper[6:]=h.upper-.08;upper[0]=-.04
    for seedid,(flex,pitch,th) in enumerate(seeds):
        if a.refine:
            prior=json.loads(a.refine[seedid].read_text());w=np.asarray(prior['wrist_in_knife'])
            seed=np.asarray(prior['touch_q'])
            x=np.r_[w[:3,3],Rotation.from_matrix(w[:3,:3]@base_rotation.T).as_rotvec(),seed]
        else:
            seed=np.array([0 if n.endswith('joint2') else flex for n in h.names]);seed[-4:]=th
            x=np.r_[[-.125,-.06,0],[0,0,pitch],seed]
        begin=time.time()
        stages=[]
        for cw,maxiter in [(100,65),(500,110)]:
            fit=least_squares(residual,np.clip(x,lower+1e-8,upper-1e-8),args=(seed,cw),
                bounds=(lower,upper),max_nfev=maxiter,diff_step=1e-5)
            x=fit.x;stages.append(dict(collision_weight=cw,cost=float(fit.cost),nfev=fit.nfev,message=fit.message))
        if a.refine:
            def constraints(v):
                w,q,c,f,gap,height=geometry(v)
                tg=np.c_[normals[:,0]*.0095,np.clip(c[:,1],-.003,.002),np.clip(c[:,2],zmin,zmax)]
                values=np.r_[(height-.00055)*1000,(gap-.00001)*1000,
                    f-.32,(.0009-np.linalg.norm(c-tg,axis=1))*1000,
                    (c[1:-1,2]-c[2:,2]-a.long_spacing)*1000,
                    -.7-(object_world[:3,:3]@w[:3,:3])[2,0]]
                if a.balance_long_axis:values=np.r_[values,((.010 if a.balanced_margin else .004)-abs(c[0,2]-c[1:,2].mean()))*1000]
                return values
            fit=minimize(lambda v:float(np.sum(residual(v,seed,100)**2)),x,
                method='SLSQP',bounds=list(zip(lower,upper)),constraints=[dict(type='ineq',fun=constraints)],
                options=dict(maxiter=180,ftol=1e-10))
            x=fit.x;stages.append(dict(method='SLSQP',success=bool(fit.success),iterations=fit.nit,message=fit.message))
        wrist,q,points,facing,gaps,heights=geometry(x)
        targets=np.c_[normals[:,0]*.0095,np.clip(points[:,1],-.003,.002) if a.refine else np.full(5,-.001),np.clip(points[:,2],zmin,zmax)]
        error=np.linalg.norm(points-targets,axis=1)
        ordering=points[1:-1,2]-points[2:,2]
        accepted=bool(error.max()<.001 and facing.min()>.3 and gaps.min()>=0 and heights.min()>=.0005 and ordering.min()>=a.long_spacing)
        row=dict(name=('side-face-refine-' if a.refine else 'fresh-five-pad-')+'%02d'%seedid,kind='geometric_touch_only',
            validation='No physics execution; accepted only requests further exact collision/path checks',
            initial_flex=flex,initial_pitch_rad=pitch,initial_thumb=th,
            wrist_in_knife=wrist.tolist(),touch_q=q.tolist(),joint_names=h.names,
            contact_targets=targets.tolist(),contact_normals=normals.tolist(),contact_points=points.tolist(),
            contact_errors_m=error.tolist(),pad_facing_cosines=facing.tolist(),
            min_convex_separating_gap_m=float(gaps.min()),min_table_clearance_m=float(heights.min()),
            length_contact_spacing_m=ordering.tolist(),joint_margin_min_rad=float(np.minimum(q-h.lower,h.upper-q).min()),
            geometric_pass=accepted,stages=stages,seconds=time.time()-begin,
            active_fingers=list(FINGERS),excluded_fingers=[])
        row['thumb_palm_constraint']=a.avoid_thumb_palm
        row['balance_long_axis_requested']=a.balance_long_axis
        row['thumb_to_four_pad_centroid_z_m']=float(points[0,2]-points[1:,2].mean())
        if a.balance_long_axis:row['geometric_pass']=row['geometric_pass'] and abs(row['thumb_to_four_pad_centroid_z_m'])<=(.010 if a.balanced_margin else .004)
        row['balanced_margin_requested']=a.balanced_margin
        row['self_collision_pairs_constrained']=self_pairs
        row['required_long_spacing_m']=a.long_spacing
        if a.refine:
            row.update(source_plan=str(a.refine[seedid]),contact_height_interval_m=[-.003,.002],
                constraint_change='Contact may occupy real side face y in [-3,+2]mm; old y=-1mm was an arbitrary planner line. Physical dimensions, collision and acceptance thresholds unchanged.')
        (a.output/(row['name']+'.json')).write_text(json.dumps(row,indent=2)+'\n');results.append(row)
        print(json.dumps({k:row[k] for k in ['name','contact_errors_m','pad_facing_cosines','min_convex_separating_gap_m','min_table_clearance_m','geometric_pass','seconds']}),flush=True)
    (a.output/'summary.json').write_text(json.dumps(dict(candidates=results,physics_executions=0,training_configs=0),indent=2)+'\n')


if __name__=='__main__':main()
