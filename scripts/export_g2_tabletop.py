"""Export the supplied G2 right-arm chain, retaining the frozen Wuji URDF.

Other G2 joints are locked at their authored zero pose for a fixed-base tabletop
baseline. The hand's geometry/inertia are copied verbatim, never re-estimated.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics
from scipy.spatial.transform import Rotation

from scripts.import_wuji_artbot import mesh_data, rotation, vector, write_obj, write_hull

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('/data/research/ArtBot/G2_crsB_wuji/robot.usd'))
    p.add_argument('--output', type=Path, default=ROOT/'assets/robots/g2_wuji')
    args = p.parse_args()
    stage = Usd.Stage.Open(str(args.source))
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    cache = UsdGeom.XformCache()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    robot = ET.Element('robot', name='g2_wuji_fixed_base_right_arm')
    joints = [UsdPhysics.Joint(p) for p in stage.Traverse() if p.IsA(UsdPhysics.Joint)]
    links = {}
    for j in joints:
        for t in list(j.GetBody0Rel().GetTargets()) + list(j.GetBody1Rel().GetTargets()):
            links[t.name] = stage.GetPrimAtPath(t)
    audit = dict(source=str(args.source), active_arm=[], locked_joints=[], links={},
                 hand_source='assets/hands/wuji_artbot/right.urdf',
                 differences=['Fixed base and non-right-arm G2 joints locked at zero.',
                              'Missing G2 collision meshes replaced with per-link visual convex hulls.',
                              'Wuji right hand retains frozen URDF, collider geometry and inertia.'])
    hand_path = ROOT/audit['hand_source']
    hand = ET.parse(hand_path).getroot()
    for name, prim in links.items():
        if name.startswith('hand_r_'):
            continue
        link = ET.SubElement(robot, 'link', name=name)
        mass = UsdPhysics.MassAPI(prim)
        m = mass.GetMassAttr().Get()
        diag = mass.GetDiagonalInertiaAttr().Get()
        if m is not None and m > 0 and diag is not None and min(diag) > 0:
            inertial = ET.SubElement(link, 'inertial')
            ET.SubElement(inertial, 'origin', xyz=vector(mass.GetCenterOfMassAttr().Get()), rpy='0 0 0')
            ET.SubElement(inertial, 'mass', value=str(m))
            axes = rotation(mass.GetPrincipalAxesAttr().Get()).as_matrix()
            inertia = axes @ np.diag(diag) @ axes.T
            ET.SubElement(inertial, 'inertia', **{k:str(inertia[i,j]) for k,i,j in
                [('ixx',0,0),('ixy',0,1),('ixz',0,2),('iyy',1,1),('iyz',1,2),('izz',2,2)]})
        try:
            vertices, faces = mesh_data(prim, cache)
        except ValueError:
            audit['links'][name] = dict(mesh=False, mass=m)
            continue
        audit['links'][name] = dict(mesh=True, vertices=len(vertices), mass=m,
                                  bounds=[vertices.min(0).tolist(),vertices.max(0).tolist()])
        for kind in ['visual','collision']:
            relative = Path('meshes')/kind/(name+'.obj')
            if kind == 'visual': write_obj(out/relative, vertices, faces)
            else: write_hull(out/relative,vertices)
            element = ET.SubElement(link,kind)
            ET.SubElement(ET.SubElement(element,'geometry'),'mesh',filename=str(relative))
            if kind == 'visual':
                mat=ET.SubElement(element,'material',name=name+'_color')
                ET.SubElement(mat,'color',rgba='0.65 0.70 0.77 1')
    for element in hand:
        element=copy.deepcopy(element)
        for mesh in element.findall('.//mesh'):
            mesh.set('filename','../../hands/wuji_artbot/'+mesh.get('filename'))
        robot.append(element)
    for j in joints:
        name=j.GetPrim().GetName()
        if name.startswith('hand_r_') and name != 'hand_r_base_joint': continue
        active=name in [f'idx{61+i}_arm_r_joint{i+1}' for i in range(7)]
        element=ET.SubElement(robot,'joint',name=name,type='revolute' if active else 'fixed')
        ET.SubElement(element,'parent',link=j.GetBody0Rel().GetTargets()[0].name)
        ET.SubElement(element,'child',link=j.GetBody1Rel().GetTargets()[0].name)
        r0=rotation(j.GetLocalRot0Attr().Get()); r1=rotation(j.GetLocalRot1Attr().Get())
        rot=r0*r1.inv()
        pos=np.asarray(j.GetLocalPos0Attr().Get())-rot.apply(j.GetLocalPos1Attr().Get())
        ET.SubElement(element,'origin',xyz=vector(pos),rpy=vector(rot.as_euler('xyz')))
        if active:
            assert np.allclose(r1.as_matrix(),np.eye(3)) and np.allclose(j.GetLocalPos1Attr().Get(),0)
            rev=UsdPhysics.RevoluteJoint(j.GetPrim()); d=UsdPhysics.DriveAPI.Get(j.GetPrim(),'angular')
            axis=np.eye(3)['XYZ'.index(rev.GetAxisAttr().Get())]
            lower,upper=np.deg2rad([rev.GetLowerLimitAttr().Get(),rev.GetUpperLimitAttr().Get()])
            velocity=float(np.deg2rad(j.GetPrim().GetAttribute('physxJoint:maxJointVelocity').Get()))
            effort=float(d.GetMaxForceAttr().Get())
            ET.SubElement(element,'axis',xyz=vector(axis))
            ET.SubElement(element,'limit',lower=str(lower),upper=str(upper),velocity=str(velocity),effort=str(effort))
            audit['active_arm'].append(dict(name=name,lower=lower,upper=upper,velocity=velocity,effort=effort,
                stiffness=float(d.GetStiffnessAttr().Get()*180/np.pi),damping=float(d.GetDampingAttr().Get()*180/np.pi),
                armature=float(j.GetPrim().GetAttribute('physxJoint:armature').Get() or 0)))
        else: audit['locked_joints'].append(name)
        if name=='hand_r_base_joint':
            audit['wuji_mount']=dict(parent=j.GetBody0Rel().GetTargets()[0].name,child=j.GetBody1Rel().GetTargets()[0].name,
                                    position=pos.tolist(),quaternion_xyzw=rot.as_quat().tolist())
    ET.indent(robot)
    ET.ElementTree(robot).write(out/'g2_wuji.urdf',encoding='utf-8',xml_declaration=True)
    audit['source_hashes']={str(Path(l.realPath).relative_to(args.source.parent)):hashlib.sha256(Path(l.realPath).read_bytes()).hexdigest()
                            for l in stage.GetUsedLayers() if l.realPath}
    audit['hand_sha256']=hashlib.sha256(hand_path.read_bytes()).hexdigest()
    audit['urdf_sha256']=hashlib.sha256((out/'g2_wuji.urdf').read_bytes()).hexdigest()
    (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(links=len(robot.findall('link')),joints=len(robot.findall('joint')),active_arm=len(audit['active_arm']),mount=audit['wuji_mount'])))


if __name__=='__main__': main()
