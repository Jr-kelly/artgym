"""Nominal motor-point axial Jacobians from FK and an initial geometry estimate.

These derivatives map measured joint error to a motor-point displacement in
metres. They do not measure slider displacement, contact state or force.
"""
import copy
import numpy as np
from scripts.g2_contact_geometry import DigitGeometry

def attach_axial_jacobians(plan,reference):
    ref=copy.deepcopy(reference);geometry=DigitGeometry();hand=geometry.w
    vertices=np.concatenate([v for v,_ in geometry.meshes['hand_r_thumb_pad_link']])
    wrist=np.asarray(plan['wrist_in_knife']);full=np.asarray(plan['close_q']).copy()
    def point(thumb):
        q=full.copy();q[16:]=thumb
        matrix=wrist@hand.forward(q)['hand_r_thumb_pad_link']
        v=vertices@matrix[:3,:3].T+matrix[:3,3]
        weight=np.exp(-(v[:,1]-v[:,1].min())/.0002)
        return weight@v/weight.sum()
    for row in ref['rows']:
        q=np.asarray(row['q_thumb']);steps=np.eye(4)*1e-4
        jac=np.stack([(point(q+d)-point(q-d))/.0002 for d in steps],axis=1)
        row['axial_jacobian_m_per_rad']=jac[2].tolist()
    ref['axial_jacobian_scope']=__doc__
    return ref
