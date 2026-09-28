"""Acquisition hold check independent of the frozen policy and Isaac Gym."""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


def fixed_acquisition_hold(records,initial_object,initial_wrist,table_height=.75):
    """Independent fixed-reference hold, unrelated to a cached functional pose."""
    obj=np.asarray([r['object'] for r in records]);wrist=np.asarray([r['wrist'] for r in records])
    objt=np.array([transform(o[:3],o[3:]) for o in obj])
    rel=np.array([np.linalg.inv(transform(w[:3],w[3:]))@o for w,o in zip(wrist,objt)])
    rel0=np.linalg.inv(initial_wrist)@initial_object
    world_dist=np.linalg.norm(objt[:,:3,3]-initial_object[:3,3],axis=1)
    world_ang=Rotation.from_matrix(initial_object[:3,:3].T@objt[:,:3,:3]).magnitude()
    hand_dist=np.linalg.norm(rel[:,:3,3]-rel0[:3,3],axis=1)
    hand_ang=Rotation.from_matrix(rel0[:3,:3].T@rel[:,:3,:3]).magnitude()
    contact=np.asarray([r['finger_knife_contacts'] for r in records])>0
    opposed=contact[:,0]&(contact[:,1:].sum(1)>=2)
    table_free=bool(all(r['knife_table_contacts']==0 for r in records))
    stable=bool(world_dist.max()<.01 and world_ang.max()<.25 and hand_dist.max()<.01 and hand_ang.max()<.25)
    retained=bool(stable and obj[:,2].min()>table_height+.10 and table_free and opposed.mean()>=.9)
    return dict(retained=retained,stable=stable,frames=len(records),
        fixed_initial_object=initial_object.tolist(),fixed_initial_hand_object=rel0.tolist(),
        world_translation_max_m=float(world_dist.max()),world_rotation_max_rad=float(world_ang.max()),
        hand_translation_max_m=float(hand_dist.max()),hand_rotation_max_rad=float(hand_ang.max()),
        min_object_height_m=float(obj[:,2].min()),table_free=table_free,
        contact_order=['thumb','index','middle','ring','pinky'],per_finger_contact_fraction=contact.mean(0).tolist(),
        all_five_contact_fraction=float(contact.all(1).mean()),opposed_contact_fraction=float(opposed.mean()),
        interpretation='Contact presence is not measured load. References fixed before the hold, not refreshed.',
        thresholds=dict(translation_m=.01,rotation_rad=.25,min_height_m=table_height+.10,opposed_fraction=.9))


def acquisition_hold(trace,reference,table_height=.75):
    indices=np.flatnonzero(np.asarray(trace['phase'])=='settle_history')[-30:]
    if len(indices)<30:return dict(success=False,reason='fewer_than_30_actual_settled_frames')
    obj=np.asarray(trace['object'])[indices];wrist=np.asarray(trace['wrist'])[indices]
    rel=np.array([np.linalg.inv(transform(w[:3],w[3:]))@transform(o[:3],o[3:]) for w,o in zip(wrist,obj)])
    drift=np.linalg.norm(rel[:,:3,3]-rel[0,:3,3],axis=1)
    rotation=(Rotation.from_matrix(rel[0,:3,:3]).inv()*Rotation.from_matrix(rel[:,:3,:3])).magnitude()
    contacts=np.asarray(trace['finger_knife_contacts'])[indices]>0
    opposed=contacts[:,0] & (contacts[:,1:].sum(1)>=2)
    near=np.linalg.norm(rel[:,:3,3]-reference[40:43],axis=1)
    table_free=None
    if 'knife_table_contacts' in trace:table_free=bool((np.asarray(trace['knife_table_contacts'])[indices]==0).all())
    minimum_height=table_height+.10
    success=bool((obj[:,2]>minimum_height).all() and (near<.05).all() and (drift<.01).all() and
                 (rotation<.25).all() and opposed.mean()>=.9 and table_free is not False)
    return dict(success=success,frames=30,duration_s=1.,relative_drift_max_m=float(drift.max()),
        relative_rotation_max_rad=float(rotation.max()),opposed_contact_fraction=float(opposed.mean()),
        min_object_height_m=float(obj[:,2].min()),table_free=table_free,
        functional_position_error_m=float(near[-1]),
        functional_rotation_error_rad=float((Rotation.from_quat(reference[43:47]).inv()*Rotation.from_matrix(rel[-1,:3,:3])).magnitude()),
        thresholds=dict(height_m=minimum_height,proximity_m=.05,relative_drift_m=.01,relative_rotation_rad=.25,opposed_contact_fraction=.9),
        definition='Stable pickup for one settled second; functional-pose error reported separately, not hidden in pickup success.')


def preset_support_hold(records,table_height=.75):
    """Preset final-second support test. No thumb opposition requirement.
    Physical fixed-reference thresholds unchanged; doesn't count as pickup.
    """
    indices=np.flatnonzero(np.array([r['phase'] for r in records])=='settle_history')[-30:]
    if len(indices)!=30:return dict(success=False,reason='insufficient_actual_history')
    rows=[records[i] for i in indices];first=rows[0]
    o=transform(first['object'][:3],first['object'][3:]);w=transform(first['wrist'][:3],first['wrist'][3:])
    metrics=fixed_acquisition_hold(rows,o,w,table_height)
    contacts=np.array([r['finger_knife_contacts'] for r in rows])>0
    support=(contacts[:,1:].sum(1)>=2).mean()
    metrics.update(success=bool(metrics['stable'] and metrics['table_free'] and metrics['min_object_height_m']>table_height+.1 and support>=.9),nonthumb_support_fraction=float(support),scope='Preset-only final pose feasibility, not actual acquisition. Contact numbers are not load measurements.',definition='Fixed world and hand references;10mm/.25rad, no table/drop; >=2 nonthumb digits present90% of frames; thumb may be free.')
    return metrics
