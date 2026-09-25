"""Acquisition hold check independent of the frozen policy and Isaac Gym."""
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.g2_kinematics import transform


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
