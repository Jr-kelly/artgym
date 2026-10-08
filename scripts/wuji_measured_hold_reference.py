"""Thumb path anchored at settled measured FK, with known initial rail direction.

No contact identity, physical asset or live object/slider state is accepted.
The motor preload is retained by the existing issued-target reference anchor;
it is a position offset and does not prescribe constant force.
"""
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scipy.spatial.transform import Rotation

_GEOMETRY=None
_THUMB_CHAIN=None
def _thumb_geometry():
    global _GEOMETRY,_THUMB_CHAIN
    if _GEOMETRY is None:
        _GEOMETRY=DigitGeometry();lookup={j[1]:j for j in _GEOMETRY.w.joints};chain=[];name='hand_r_thumb_pad_link'
        while name!='hand_r_base_link':
            joint=lookup[name];chain.append(joint);name=joint[0]
        _THUMB_CHAIN=list(reversed(chain))
    return _GEOMETRY,_THUMB_CHAIN

def _thumb_frame(q,chain):
    frame=np.eye(4)
    for parent,child,origin,index,axis in chain:
        value=origin.copy()
        if index is not None:value[:3,:3]=value[:3,:3]@Rotation.from_rotvec(axis*q[index]).as_matrix()
        frame=frame@value
    return frame


def measured_hold_path(measured_q,normal_wrist,rail_wrist,shifts):
    g,chain=_thumb_geometry();h=g.w;q=np.clip(np.asarray(measured_q,dtype=float),h.lower+1e-5,h.upper-1e-5)
    normal=np.asarray(normal_wrist,dtype=float);normal/=np.linalg.norm(normal)
    rail=np.asarray(rail_wrist,dtype=float);rail/=np.linalg.norm(rail)
    vertices=np.concatenate([v for v,_ in g.meshes['hand_r_thumb_pad_link']])
    def surface(values):
        m=_thumb_frame(values,chain);v=vertices@m[:3,:3].T+m[:3,3]
        p=v@normal;w=np.exp(-(p-p.min())/.0002);w/=w.sum()
        return w@v,m[:3,0]
    origin,axis=surface(q);seed=q.copy();rows=[];audit=[]
    for shift in shifts:
        if abs(shift)<1e-10:chosen=q.copy();error=0.
        else:
            desired=origin+float(shift)*rail
            def residual(x):
                value=q.copy();value[16:]=x;point,direction=surface(value)
                return np.r_[(point-desired)*100,(direction-axis)*.12,(x-seed[16:])*.002]
            fit=least_squares(residual,np.clip(seed[16:],h.lower[16:]+1e-5,h.upper[16:]-1e-5),
                bounds=(h.lower[16:]+1e-5,h.upper[16:]-1e-5),max_nfev=150)
            chosen=q.copy();chosen[16:]=fit.x;error=float(np.linalg.norm(surface(chosen)[0]-desired))
        jacobian=[]
        for j in range(16,20):
            plus=chosen.copy();minus=chosen.copy();plus[j]+=1e-5;minus[j]-=1e-5
            jacobian.append(float((surface(plus)[0]-surface(minus)[0])@rail/2e-5))
        rows.append(chosen[16:].tolist());audit.append(dict(shift_m=float(shift),FK_position_error_m=error,axial_jacobian_m_per_rad=jacobian))
        seed=chosen
    if max(row['FK_position_error_m'] for row in audit)>.00025:
        raise ValueError('Measured-hold thumb IK cannot preserve full40mm requested path: '+str(audit[-1]))
    return np.asarray(rows),dict(source='Mean50 actual measured joint frames during settledhold; FK plus explicitly onceestimatednormal/rail direction, no trueobject/contact input',
        measured_mean_q_rad=np.asarray(measured_q).tolist(),initial_pad_point_wrist_m=origin.tolist(),
        normal_wrist=normal.tolist(),rail_direction_wrist=rail.tolist(),rows=audit,
        preload_scope='Existing issuedtarget anchor retained; positionpreload is not constantforce')
