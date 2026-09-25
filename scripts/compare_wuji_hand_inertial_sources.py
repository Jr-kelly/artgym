"""Compare source mass/inertia after merging each movable link's fixed children.

This is an offline source audit of 20 rigid groups. Eigenvalues avoid confusing
different inertia frames; fixed pads must be included because the official
MJCF lumps them into adjacent bodies. It excludes the palm and does not certify
imported PhysX or measured hardware mass.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import yaml
from scipy.spatial.transform import Rotation


def urdf_fixed_group(link_name, links, fixed_children):
    parts=[]
    def visit(name, transform):
        link=links[name];inertial=link.find('inertial')
        if inertial is not None:
            origin=inertial.find('origin')
            xyz=np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
            rotate=Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix()
            x=inertial.find('inertia')
            matrix=np.array([[float(x.get('i'+i+j if 'xyz'.index(i)<='xyz'.index(j) else 'i'+j+i)) for j in 'xyz'] for i in 'xyz'])
            rot=transform[:3,:3]@rotate
            parts.append(dict(name=name,mass=float(inertial.find('mass').get('value')),
                com=transform[:3,:3]@xyz+transform[:3,3],inertia=rot@matrix@rot.T))
        for joint in fixed_children.get(name,[]):
            origin=joint.find('origin');relative=np.eye(4)
            relative[:3,:3]=Rotation.from_euler('xyz',np.fromstring(origin.get('rpy','0 0 0'),sep=' ')).as_matrix()
            relative[:3,3]=np.fromstring(origin.get('xyz','0 0 0'),sep=' ')
            visit(joint.find('child').get('link'),transform@relative)
    visit(link_name,np.eye(4))
    mass=sum(p['mass'] for p in parts)
    com=sum(p['mass']*p['com'] for p in parts)/mass
    inertia=np.zeros((3,3))
    for p in parts:
        delta=p['com']-com
        inertia+=p['inertia']+p['mass']*(np.dot(delta,delta)*np.eye(3)-np.outer(delta,delta))
    return mass,inertia,[p['name'] for p in parts]


def main():
    root=Path(__file__).resolve().parents[1]
    artbot=root/'assets/hands/wuji_artbot/right.urdf'
    official=root/'runs/wuji-goal/research/wuji-official/wuji-mjlab/src/wuji_mjlab/assets/robots/wuji_hand/mjcf/right_mjlab.xml'
    ur,mj=ET.parse(artbot),ET.parse(official)
    cfg=yaml.safe_load((root/'isaacgymenvs/cfg/hand/wuji.yaml').read_text())
    joints={j.get('name'):j for j in ur.findall('joint')}
    links={l.get('name'):l for l in ur.findall('link')}
    fixed_children={}
    for joint in ur.findall('joint'):
        if joint.get('type')=='fixed':
            fixed_children.setdefault(joint.find('parent').get('link'),[]).append(joint)
    bodies={b.find('joint').get('name'):b for b in mj.findall('.//worldbody//body') if b.find('joint') is not None}
    fingers=dict(thumb=1,index=2,middle=3,ring=4,pinky=5)
    rows=[]
    for name in cfg['dof_names']:
        finger,joint=name[len('hand_r_'):].split('_')
        canonical='right_finger%d_%s'%(fingers[finger],joint)
        a=links[joints[name].find('child').get('link')]
        b=bodies[canonical]
        bi=b.find('inertial')
        mass_a,matrix,components=urdf_fixed_group(a.get('name'),links,fixed_children)
        mass_b=float(bi.get('mass'))
        eig_a=np.linalg.eigvalsh(matrix)
        eig_b=np.sort(np.fromstring(bi.get('diaginertia'),sep=' '))
        assert np.all(eig_a>0) and np.all(eig_b>0)
        rows.append(dict(artbot_joint=name,official_joint=canonical,artbot_link=a.get('name'),artbot_group_components=components,official_body=b.get('name'),
            artbot_mass_kg=mass_a,official_mass_kg=mass_b,mass_ratio=mass_a/mass_b,
            artbot_inertia_eigenvalues=eig_a.tolist(),official_inertia_eigenvalues=eig_b.tolist(),
            inertia_eigenvalue_ratio=(eig_a/eig_b).tolist()))
    out=root/'runs/wuji-goal/diagnostics/hand-inertial-fixed-group-comparison'
    out.mkdir(exist_ok=False)
    ratios=np.array([r['inertia_eigenvalue_ratio'] for r in rows])
    record=dict(scope=__doc__,bodies=20,rows=rows,
        mass_ratio_range=[min(r['mass_ratio'] for r in rows),max(r['mass_ratio'] for r in rows)],
        eigenvalue_ratio_range=[float(ratios.min()),float(ratios.max())],
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [artbot,official,Path(__file__)]})
    (out/'report.json').write_text(json.dumps(record,indent=2)+'\n')
    (out/'source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:v for k,v in record.items() if k not in ['rows','source_sha256']}))


if __name__=='__main__':main()
