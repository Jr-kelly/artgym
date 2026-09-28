"""CPU resting-pitch prior for the fixed slider-down tabletop condition.

Minimizes geometric gravitational potential with the slider hypothetically at
its lower limit. Does not run physics, constrain the slider, or assert a measured
rest pose. The actual runner must naturally settle and recheck its motor path.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from scripts.g2_knife_geometry import KnifeGeometry
from scripts.g2_kinematics import transform


def centroid(vertices):
    hull=ConvexHull(vertices);ref=vertices.mean(0)
    tet=vertices[hull.simplices]-ref
    vol=abs(np.einsum('ij,ij->i',np.cross(tet[:,0],tet[:,1]),tet[:,2]))/6
    return (vol[:,None]*(tet.sum(1)/4+ref)).sum(0)/vol.sum(),vol.sum()


def main():
    p=argparse.ArgumentParser()
    for key in ['spec','reference-localization','output']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--yaw',type=float,default=180)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    k=KnifeGeometry(a.spec);parts=k.collision_parts();v=np.concatenate([x['vertices'] for x in parts])
    cs=[centroid(x['vertices']) for x in parts]
    body=cs[0][0];slider=sum(c*volume for c,volume in cs[1:])/sum(volume for c,volume in cs[1:])
    ph=k.spec['physics_hypothesis'];m1,m2=ph['body_mass_kg'],ph['button_mass_kg']
    com=(m1*body+m2*slider)/(m1+m2)
    r0=(Rotation.from_euler('z',a.yaw,degrees=True)*Rotation.from_euler('x',90,degrees=True)*Rotation.from_euler('z',180,degrees=True)).as_matrix()
    def objective(theta):
        row=(r0@Rotation.from_euler('x',theta).as_matrix())[2]
        return float(com@row-(v@row).min())
    fit=minimize_scalar(objective,bounds=(-.1,.1),method='bounded',options={'xatol':1e-12})
    r=r0@Rotation.from_euler('x',fit.x).as_matrix()
    old=json.loads(a.reference_localization.read_text());t=transform(old['object'][:3],old['object'][3:])
    z=float(.75-(v@r[2]).min()+.0001)
    result=dict(scope='Geometric static-rest prior, not measured pose or dynamics; no physical slider constraint',
        com_proxy_m=com.tolist(),assumed_rest_pitch_rad=float(fit.x),assumed_rest_xyzw=Rotation.from_matrix(r).as_quat().tolist(),
        object_root_z_m=z,old_orientation_newmesh_root_z_m=float(k.table_pose(t)[2,3]),
        rotation_difference_from_old_rest_rad=float(Rotation.from_matrix(t[:3,:3].T@r).magnitude()),
        limitations=['Slider may move passively','Actual simulator COM may differ','Actual contact/friction/settling must be checked'],physics_trials=0)
    (a.output/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    old['object']=[*old['object'][:2],z,*result['assumed_rest_xyzw']]
    old['method']='CPU static-rest prior only, not measured. Arm q is only an IK seed.'
    (a.output/'planning-localization.json').write_text(json.dumps(old,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
