"""Exact original convex-hull intersection after an inconclusive SAT certificate.

Face-only SAT gives a separation lower bound. Its negative result alone cannot
reject a pose. The original convex hull halfspaces certify actual intersection;
a negative optimum means the original hulls have no intersection. No mesh,
physics, tolerance or H rule is altered by this geometric fallback.
"""
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linprog

def convex_intersection_radius(vertices_a,vertices_b):
    planes=np.concatenate([ConvexHull(vertices_a).equations,ConvexHull(vertices_b).equations])
    result=linprog([0.,0.,0.,-1.],A_ub=np.column_stack([planes[:,:3],np.ones(len(planes))]),b_ub=-planes[:,3],bounds=[(None,None)]*4,method='highs')
    if not result.success:
        raise RuntimeError('Original convex intersection proof failed: '+result.message)
    return float(result.x[3])

def exact_hand_knife_intersection(g,hand_q,wrist_in_knife,slider,collision):
    frame=wrist_in_knife@g.w.forward(hand_q)[collision['hand_link']]
    knife=next(p for p in g.knife_geometry.collision_parts(slider)if p['link']==collision['knife_link']and p['index']==collision.get('knife_component',0))
    radii=[]
    for vertices,normals in g.meshes[collision['hand_link']]:
        transformed=vertices@frame[:3,:3].T+frame[:3,3]
        radii.append(convex_intersection_radius(transformed,knife['vertices']))
    return dict(hand_link=collision['hand_link'],knife_link=collision['knife_link'],knife_component=collision.get('knife_component',0),original_SAT_gap_lower_bound_m=collision['gap_lower_bound_m'],exact_intersection_radius_m=max(radii),no_intersection=bool(max(radii)<=0.),scope=__doc__)
