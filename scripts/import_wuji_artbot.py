"""Extract an ArtBot Wuji hand from USD for Isaac Gym (usd-core, numpy, scipy, pyyaml)."""
import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
import yaml


def vector(values):
    return " ".join(f"{float(v):.10g}" for v in values)


def rotation(quaternion):
    return Rotation.from_quat([*quaternion.GetImaginary(), quaternion.GetReal()])


def mesh_data(prim, cache):
    """Bake all mesh transforms into the rigid body's local coordinate system."""
    vertices, faces = [], []
    count = 0
    inverse = np.asarray(cache.GetLocalToWorldTransform(prim).GetInverse())
    for child in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
        if not child.IsA(UsdGeom.Mesh) or '/visuals/' not in str(child.GetPath()):
            continue
        mesh = UsdGeom.Mesh(child)
        points = np.asarray(mesh.GetPointsAttr().Get())
        transform = np.asarray(cache.GetLocalToWorldTransform(child)) @ inverse
        points = (np.c_[points, np.ones(len(points))] @ transform)[:, :3]
        unique, remap = np.unique(points, axis=0, return_inverse=True)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
        cursor = 0
        reverse = (mesh.GetOrientationAttr().Get() == 'leftHanded') != (np.linalg.det(transform[:3, :3]) < 0)
        for size in mesh.GetFaceVertexCountsAttr().Get():
            polygon = remap[indices[cursor:cursor + size]] + count
            for i in range(1, size - 1):
                face = [polygon[0], polygon[i], polygon[i + 1]]
                faces.append(face[::-1] if reverse else face)
            cursor += size
        vertices.append(unique)
        count += len(unique)
    if not vertices:
        raise ValueError(f'No visual mesh for {prim.GetPath()}')
    return np.concatenate(vertices), np.asarray(faces)


def write_obj(path, vertices, faces):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as stream:
        for point in vertices:
            stream.write('v ' + vector(point) + '\n')
        for face in faces:
            stream.write('f ' + ' '.join(str(int(i) + 1) for i in face) + '\n')


def write_hull(path, points):
    points = np.unique(points, axis=0)
    hull = ConvexHull(points)
    faces = hull.simplices.copy()
    for i, face in enumerate(faces):
        a, b, c = points[face]
        if np.dot(np.cross(b - a, c - a), hull.equations[i, :3]) < 0:
            faces[i] = face[::-1]
    used, remap = np.unique(faces, return_inverse=True)
    write_obj(path, points[used], remap.reshape(-1, 3))


def split_hull(points, height):
    """Split a distal link at a plane so its fingertip collider does not overlap it."""
    hull = ConvexHull(points)
    points = points[hull.vertices]
    hull = ConvexHull(points)
    edges = {tuple(sorted((int(a), int(b)))) for face in hull.simplices
             for a, b in zip(face, np.roll(face, 1))}
    intersections = []
    for a, b in edges:
        pa, pb = points[a], points[b]
        if (pa[2] - height) * (pb[2] - height) < 0:
            intersections.append(pa + (height - pa[2]) / (pb[2] - pa[2]) * (pb - pa))
    if not intersections:
        raise ValueError('Fingertip split plane does not intersect the distal link')
    return (np.concatenate([points[points[:, 2] <= height], intersections]),
            np.concatenate([points[points[:, 2] >= height], intersections]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='ArtBot robot.usd')
    parser.add_argument('--output', type=Path, default=Path('assets/hands/wuji_artbot'))
    args = parser.parse_args()
    stage = Usd.Stage.Open(str(args.source.resolve()))
    if UsdGeom.GetStageMetersPerUnit(stage) != 1:
        raise ValueError('This exporter expects a stage in metres')
    cache = UsdGeom.XformCache()
    root_path = stage.GetDefaultPrim().GetPath()
    base_name = 'hand_r_base_link'
    joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.Joint)
              and p.GetName().startswith('hand_r_') and p.GetName() != 'hand_r_base_joint']
    links = {base_name: stage.GetPrimAtPath(root_path.AppendChild(base_name))}
    by_child = {}
    for prim in joints:
        joint = UsdPhysics.Joint(prim)
        child = stage.GetPrimAtPath(joint.GetBody1Rel().GetTargets()[0])
        links[child.GetName()] = child
        by_child[child.GetName()] = joint
        if not np.allclose(joint.GetLocalPos1Attr().Get(), 0) or not np.allclose(rotation(joint.GetLocalRot1Attr().Get()).as_matrix(), np.eye(3)):
            raise ValueError(f'Non-identity child joint frame: {prim.GetPath()}')
    if len(links) != 26 or sum(p.IsA(UsdPhysics.RevoluteJoint) for p in joints) != 20:
        raise ValueError('Expected the 26-link, 20-DOF Wuji right hand')

    args.output.mkdir(parents=True, exist_ok=True)
    meshes = {name: mesh_data(prim, cache) for name, prim in links.items()}
    colliders = {name: vertices for name, (vertices, _) in meshes.items()}
    # ArtBot has empty collision nodes. Build hulls from its visual meshes.
    # Its pad visuals duplicate most of link4, so assign only the distal 14 mm
    # to each pad body, using one split surface shared with link4.
    for finger in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        distal = f'hand_r_{finger}_link4'
        pad = f'hand_r_{finger}_pad_link'
        joint = by_child[pad]
        offset = np.asarray(joint.GetLocalPos0Attr().Get())
        if not np.allclose(rotation(joint.GetLocalRot0Attr().Get()).as_matrix(), np.eye(3)):
            raise ValueError('Expected aligned fingertip pad frames')
        lower, upper = split_hull(meshes[distal][0], meshes[distal][0][:, 2].max() - 0.014)
        colliders[distal] = lower
        colliders[pad] = upper - offset

    robot = ET.Element('robot', name='wuji-artbot-right')
    for name, prim in links.items():
        link = ET.SubElement(robot, 'link', name=name)
        mass = UsdPhysics.MassAPI(prim)
        inertial = ET.SubElement(link, 'inertial')
        ET.SubElement(inertial, 'origin', xyz=vector(mass.GetCenterOfMassAttr().Get()), rpy='0 0 0')
        ET.SubElement(inertial, 'mass', value=str(mass.GetMassAttr().Get()))
        axes = rotation(mass.GetPrincipalAxesAttr().Get()).as_matrix()
        inertia = axes @ np.diag(mass.GetDiagonalInertiaAttr().Get()) @ axes.T
        if np.linalg.eigvalsh(inertia).min() <= 0:
            raise ValueError(f'Non-positive inertia for {name}')
        ET.SubElement(inertial, 'inertia', **{key: f'{inertia[i,j]:.10g}'
                      for key, i, j in [('ixx',0,0),('ixy',0,1),('ixz',0,2),('iyy',1,1),('iyz',1,2),('izz',2,2)]})
        for kind in ('visual', 'collision'):
            relative = Path('meshes') / kind / f'{name}.obj'
            if kind == 'visual':
                write_obj(args.output / relative, *meshes[name])
            else:
                write_hull(args.output / relative, colliders[name])
            element = ET.SubElement(link, kind)
            ET.SubElement(element, 'origin', xyz='0 0 0', rpy='0 0 0')
            ET.SubElement(ET.SubElement(element, 'geometry'), 'mesh', filename=relative.as_posix())
            if kind == 'visual':
                material = ET.SubElement(element, 'material', name=name + '_material')
                ET.SubElement(material, 'color', rgba='0.18 0.18 0.2 1' if '_pad_' in name else '0.8 0.82 0.84 1')

    names, properties = [], {key: [] for key in ('stiffness','damping','friction','armature')}
    for prim in joints:
        source_joint = UsdPhysics.Joint(prim)
        revolute = prim.IsA(UsdPhysics.RevoluteJoint)
        element = ET.SubElement(robot, 'joint', name=prim.GetName(), type='revolute' if revolute else 'fixed')
        ET.SubElement(element, 'parent', link=source_joint.GetBody0Rel().GetTargets()[0].name)
        ET.SubElement(element, 'child', link=source_joint.GetBody1Rel().GetTargets()[0].name)
        ET.SubElement(element, 'origin', xyz=vector(source_joint.GetLocalPos0Attr().Get()),
                      rpy=vector(rotation(source_joint.GetLocalRot0Attr().Get()).as_euler('xyz')))
        if revolute:
            joint = UsdPhysics.RevoluteJoint(prim)
            drive = UsdPhysics.DriveAPI.Get(prim, 'angular')
            axis = np.eye(3)['XYZ'.index(joint.GetAxisAttr().Get())]
            ET.SubElement(element, 'axis', xyz=vector(axis))
            ET.SubElement(element, 'limit', lower=str(np.deg2rad(joint.GetLowerLimitAttr().Get())),
                          upper=str(np.deg2rad(joint.GetUpperLimitAttr().Get())),
                          effort=str(drive.GetMaxForceAttr().Get()),
                          velocity=str(np.deg2rad(prim.GetAttribute('physxJoint:maxJointVelocity').Get())))
            names.append(prim.GetName())
            # USD angular drive gains are per degree; Isaac Gym uses radians.
            properties['stiffness'].append(float(drive.GetStiffnessAttr().Get() * 180 / np.pi))
            properties['damping'].append(float(drive.GetDampingAttr().Get() * 180 / np.pi))
            for key, attr in [('armature','physxJoint:armature'),('friction','physxJoint:jointFriction')]:
                properties[key].append(float(prim.GetAttribute(attr).Get() or 0))
    ET.indent(robot)
    ET.ElementTree(robot).write(args.output / 'right.urdf', encoding='utf-8', xml_declaration=True)
    config = {'type':'wuji', 'asset':(args.output / 'right.urdf').as_posix(), 'self_collisions':False,
              'force_links':[f'hand_r_{f}_pad_link' for f in ('thumb','index','middle','ring','pinky')],
              'track_links':[f'hand_r_{f}_pad_link' for f in ('thumb','index','middle','ring','pinky')],
              'dof_names':names, 'dof_props':properties,
              'task':{'numActions':20,'propDim':40,'policyObsDim':111,'studentInitObsDim':55},
              'randomization':{'randomize':False}}
    (args.output / 'hand_config.yaml').write_text(yaml.safe_dump(config, sort_keys=False))
    hashes = {str(Path(layer.realPath).relative_to(args.source.resolve().parent)):
              hashlib.sha256(Path(layer.realPath).read_bytes()).hexdigest()
              for layer in stage.GetUsedLayers() if layer.realPath}
    (args.output / 'source_hashes.yaml').write_text(yaml.safe_dump(hashes, sort_keys=True))
    print(f'Exported {len(links)} links and {len(names)} joints to {args.output}')


if __name__ == '__main__':
    main()
