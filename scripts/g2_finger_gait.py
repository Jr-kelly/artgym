"""Sequential digit motor moves; free knife; fixed references and measured gates."""
import json
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


def stability(rows,world_reference,hand_reference,hand_indices,command_start,moving,table_z):
    objects=np.asarray([r['object'] for r in rows]);wrists=np.asarray([r['wrist'] for r in rows])
    relative=np.array([np.linalg.inv(transform(w[:3],w[3:]))@transform(o[:3],o[3:]) for w,o in zip(wrists,objects)])
    dp=np.linalg.norm(objects[:,:3]-world_reference[:3,3],axis=1)
    dr=(Rotation.from_matrix(world_reference[:3,:3]).inv()*Rotation.from_quat(objects[:,3:])).magnitude()
    hp=np.linalg.norm(relative[:,:3,3]-hand_reference[:3,3],axis=1)
    hr=(Rotation.from_matrix(hand_reference[:3,:3]).inv()*Rotation.from_matrix(relative[:,:3,:3])).magnitude()
    fingers=np.asarray([r['finger_knife_contacts'] for r in rows])>0
    q=np.asarray([r['q'] for r in rows]);cmd=np.asarray([r['reference_targets'][hand_indices] for r in rows])
    support=np.asarray([i for i in range(20) if i not in moving],dtype=int)
    bad=(dp>=.01)|(dr>=.25)|(objects[:,2]<=table_z+.10)|np.asarray([r['knife_table_contacts']>0 for r in rows])
    first=np.flatnonzero(bad)
    return dict(stable=bool(not bad.any()),frames=len(rows),world_position_max_m=float(dp.max()),world_rotation_max_rad=float(dr.max()),
        hand_position_max_m=float(hp.max()),hand_rotation_max_rad=float(hr.max()),first_instability_time_s=float(rows[first[0]]['time']) if len(first) else None,
        contact_fraction_thumb_index_middle_ring_pinky=fingers.mean(0).tolist(),min_object_height_m=float(objects[:,2].min()),
        knife_table_frames=int(sum(r['knife_table_contacts']>0 for r in rows)),
        support_command_change_max_rad=float(np.abs(cmd[:,support]-command_start[support]).max()) if len(support) else None,
        support_measured_change_max_rad=float(np.abs(q[:,support]-q[0,support]).max()) if len(support) else None,
        passive_slider_travel_m=float(np.ptp([r['slider'] for r in rows])))


def execute_gait(path,output,targets,hand_idx,arm_idx,current,tick,records,dt,k,fk,table_z):
    plan=json.loads(path.read_text());(output/'gait-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    assert plan['object_reference']=='fixed_world_at_gait_start'
    q,qa,slider,w,o,_=current();world=o.copy();relative=np.linalg.inv(w)@o
    initial_command=targets[hand_idx].copy()
    if 'initial_command' in plan:
        error=float(np.abs(initial_command-np.asarray(plan['initial_command'])).max())
        if error>1e-6:raise ValueError('Gait initial command mismatch: '+str(error))
    output_rows=[]
    for stage in plan['stages']:
        moving=list(stage.get('moving_indices',[]));start=targets[hand_idx].copy();goal=start.copy()
        goal[moving]=np.asarray(stage.get('target',[]))
        arm_start=targets[arm_idx].copy();arm_goal=None
        if 'arm_target' in stage:
            arm_goal=np.asarray(stage['arm_target'])
            if np.any(arm_goal<k.lower) or np.any(arm_goal>k.upper):raise ValueError('Gait arm outside limits')
        if np.any(goal<fk.lower-1e-6) or np.any(goal>fk.upper+1e-6):raise ValueError('Gait joint target outside source limits')
        seconds=stage.get('seconds',1.);steps=round(seconds/dt)
        if 1.875*np.max(np.abs(goal-start))/seconds>2.0:raise ValueError('Gait planned joint speed exceeds 2rad/s bound')
        if arm_goal is not None and np.any(1.875*np.abs(arm_goal-arm_start)/seconds>k.velocity):raise ValueError('Gait arm speed above source limit')
        first=len(records)
        for i in range(steps):
            u=(i+1)/steps;alpha=10*u**3-15*u**4+6*u**5
            targets[hand_idx]=start+(goal-start)*alpha
            if arm_goal is not None:targets[arm_idx]=arm_start+(arm_goal-arm_start)*alpha
            tick('gait_'+stage['name'])
        result=stability(records[first:],world,relative,hand_idx,start,moving,table_z)
        result.update(name=stage['name'],kind=stage['kind'],moving_indices=moving,
            first_command_delta_rad=float(np.abs(records[first]['reference_targets'][hand_idx]-start).max()),
            reference='Fixed at gait start, including all preceding moves; never refreshed after a move.')
        output_rows.append(result)
        if 'thumb_gap_lower_bound_m' in records[first]:
            gaps=np.array([row['thumb_gap_lower_bound_m'] for row in records[first:]])
            result['thumb_gap_min_m']=float(gaps.min());result['thumb_gap_final_m']=float(gaps[-1])
            free=np.array([row['finger_knife_contacts'][0]==0 for row in records[first:]])
            result['thumb_zero_contact_frames']=int(free.sum())
            if free.any():result['thumb_first_no_contact_time_s']=float(records[first+np.flatnonzero(free)[0]]['time'])
        (output/'gait-checks.json').write_text(json.dumps(dict(stages=output_rows,world_reference=world.tolist(),hand_reference=relative.tolist()),indent=2)+'\n')
        if not result['stable']:raise ValueError('Gait fixed-reference stability failed: '+stage['name'])
        if stage['kind']=='hold' and stage.get('require_contact') is not None:
            index=stage['require_contact'];fraction=result['contact_fraction_thumb_index_middle_ring_pinky'][index]
            if fraction<.9:raise ValueError('New contact not established for entire hold: '+stage['name'])
        if stage['kind']=='hold' and stage.get('require_no_contact') is not None:
            index=stage['require_no_contact'];fraction=result['contact_fraction_thumb_index_middle_ring_pinky'][index]
            if fraction!=0.:raise ValueError('Requested digit did not unload for the full hold: '+stage['name'])
        if stage.get('require_thumb_gap_m') is not None:
            if result.get('thumb_gap_min_m',-1)<stage['require_thumb_gap_m']:raise ValueError('Whole-thumb clearance below declared margin: '+stage['name'])
