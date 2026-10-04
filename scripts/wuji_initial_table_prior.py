"""Known tabletop geometry + once initial estimate, never current object truth.

Returns world priors; a caller transforms them with measured arm FK once at
acquisition takeover. Contact-roof shifts and slider-center poses are separate.
The authored nominal retracted rail reference is an engineering convention,
not measured real closed-blade position or a live slider state.
"""
import numpy as np
NOMINAL_ORIGIN=np.array([0.,.0075,.010624586881962734])
NOMINAL_RETRACTED=-.03267458688196273

def known_world_poses(plan,estimate=None):
    world=np.asarray(plan['object_world_matrix'],dtype=float).copy()
    estimate=estimate or {}
    center=np.asarray(estimate.get('initial_object_center_shift_knife_m',[0.,0.,0.]))
    world[:3,3]+=world[:3,:3]@center
    offset=np.asarray(estimate.get('slider_contact_shift_m',[0.,0.,0.]),dtype=float).copy()
    body=np.asarray(estimate.get('handle_size_WTL_m',[.016,.012,.135]))
    slider=np.asarray(estimate.get('slider_size_WTL_m',[.01,.003,.03]))
    # Roof-contact observation includes the extra half-height. Remove it for
    # the center pose encoded by R800; keep it in contact trajectory planning.
    offset[1]+=(body[1]-.012)/2-(slider[1]-.003)/2
    local=np.eye(4);local[:3,3]=NOMINAL_ORIGIN+[0.,0.,NOMINAL_RETRACTED]+offset
    return world,world@local

def measured_arm_relative(plan,estimate,wrist_world):
    inverse=np.linalg.inv(np.asarray(wrist_world,dtype=float))
    return tuple(inverse@pose for pose in known_world_poses(plan,estimate))
