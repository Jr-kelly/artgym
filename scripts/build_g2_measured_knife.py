"""Build a NEW provisional measured-envelope knife, never overwrite baseline.

Three convex collision components: tapered handle,45mm button, central raised
pad. Unknowns stay explicit; button length never determines joint travel.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial import ConvexHull


ROOT=Path(__file__).resolve().parents[1]


def write_mesh(path,vertices):
    hull=ConvexHull(vertices)
    lines=['# Convex geometry proxy; dimensions/assumptions in asset-spec.json']
    lines+=['v %.12g %.12g %.12g'%tuple(v) for v in vertices]
    for ids,eq in zip(hull.simplices,hull.equations):
        i,j,k=ids
        if np.dot(np.cross(vertices[j]-vertices[i],vertices[k]-vertices[i]),eq[:3])<0:j,k=k,j
        lines.append('f %d %d %d'%(i+1,j+1,k+1))
    path.write_text('\n'.join(lines)+'\n')


def build_box_v2(s, output):
    h=s['geometry_hypothesis']; j=s['joint_hypothesis']; m=s['measured']
    assert h['handle_thickness_m']==m['handle_thickness_m'] and h['button_base_thickness_m']==m['button_protrusion_m']
    output.mkdir(parents=True,exist_ok=False)
    baseline=ROOT/'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf'
    xml=ET.parse(baseline); robot=xml.getroot(); robot.set('name',s['version'])
    sizes=[[h['handle_width_m'],h['handle_thickness_m'],h['handle_length_m']],[h['button_width_m'],h['button_base_thickness_m'],m['button_body_length_m']]]
    for link,size in zip(robot.findall('link'),sizes):
        for tag in ['visual','collision']:
            link.find(tag+'/geometry/box').set('size',' '.join(map(str,size)))
        mass=float(link.find('inertial/mass').get('value'));x,y,z=size
        for key,val in zip(['ixx','iyy','izz'],[mass*(y*y+z*z)/12,mass*(x*x+z*z)/12,mass*(x*x+y*y)/12]):link.find('inertial/inertia').set(key,str(val))
    joint=robot.find('joint');joint.find('limit').set('lower',str(j['lower_m']));joint.find('limit').set('upper',str(j['lower_m']+j['travel_m']))
    joint.find('origin').set('xyz','0 %.12g %.12g'%(h['button_center_y_m'],h['button_closed_center_z_m']-j['lower_m']))
    xml.write(output/'mobility.urdf',encoding='utf-8',xml_declaration=True)
    s.update(asset_urdf=str((output/'mobility.urdf').resolve().relative_to(ROOT)),generated_audit=dict(handle_box_xyz_m=sizes[0],button_box_xyz_m=sizes[1],closed_envelope_xyz_m=[.030,.010,.170],collision_components=2,rigid_bodies=2,passive_prismatic_dofs=1,button_length_m=.045,button_protrusion_m=.002,travel_m=j['travel_m'],separate_bump=False,baseline_urdf_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),inertia_policy='URDF analytic boxes at unchanged declared masses; retained Isaac override_com/inertia and mass assignment, effective actual values logged per run. Uncalibrated.'))
    s['file_sha256']={'mobility.urdf':hashlib.sha256((output/'mobility.urdf').read_bytes()).hexdigest()}
    (output/'asset-spec.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s['generated_audit']))


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();s=json.loads(a.spec.read_text());h=s['geometry_hypothesis'];j=s['joint_hypothesis'];m=s['measured']
    if h.get('model')=='two_boxes_v2':return build_box_v2(s,a.output)
    a.output.mkdir(parents=True,exist_ok=False);meshdir=a.output/'meshes';meshdir.mkdir()
    half=h['handle_thickness_m']/2
    body=np.array([[x,y,z] for z,width in h['handle_cross_sections_z_width_m'] for x in [-width/2,width/2] for y in [-half,half]])
    corners=np.array([[x,y,z] for x in [-1,1] for y in [-1,1] for z in [-1,1]])
    button=corners*np.array([h['button_width_m'],h['button_base_thickness_m'],m['button_body_length_m']])/2
    basey=h['button_base_thickness_m']/2
    bump=np.array([[x,y,z] for y,ratio_w,ratio_l in [(basey,1,1),(basey+h['bump_height_m'],h['bump_top_width_ratio'],h['bump_top_length_ratio'])]
        for x in [-h['bump_width_m']*ratio_w/2,h['bump_width_m']*ratio_w/2]
        for z in [-h['bump_length_m']*ratio_l/2,h['bump_length_m']*ratio_l/2]])
    for name,v in [('handle',body),('button',button),('bump',bump)]:write_mesh(meshdir/(name+'.obj'),v)
    baseline=ROOT/'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf'
    xml=ET.parse(baseline);robot=xml.getroot();robot.set('name',s['version'])
    for link in robot.findall('link'):
        name=link.get('name');parts=['handle'] if name=='link_0' else ['button','bump']
        for tag in ['visual','collision']:
            for child in list(link.findall(tag)):link.remove(child)
            for part in parts:
                item=ET.SubElement(link,tag);geo=ET.SubElement(item,'geometry');ET.SubElement(geo,'mesh',filename='meshes/'+part+'.obj',scale='1 1 1')
                if tag=='visual':
                    mat=ET.SubElement(item,'material',name=part+'_color');ET.SubElement(mat,'color',rgba='.58 .60 .64 1' if part=='handle' else '.12 .13 .15 1')
        # Baseline inertial fields remain declared for provenance. Isaac's
        # existing override_com/override_inertia policy derives effective
        # values from geometry; runner must record those actual values.
    joint=robot.find('joint');lower=j['lower_m'];joint.find('limit').set('lower',str(lower));joint.find('limit').set('upper',str(lower+j['travel_m']))
    joint.find('origin').set('xyz','0 %.12g %.12g'%(h['button_center_y_m'],h['button_closed_center_z_m']-lower))
    xml.write(a.output/'mobility.urdf',encoding='utf-8',xml_declaration=True)
    closed=np.concatenate([body,button+[0,h['button_center_y_m'],h['button_closed_center_z_m']],bump+[0,h['button_center_y_m'],h['button_closed_center_z_m']]])
    bounds=closed.max(0)-closed.min(0)
    interpretation=h.get('thickness_measurement_interpretation','closed_assembly_includes_bump')
    assert interpretation in ['closed_assembly_includes_bump','closed_assembly_excludes_bump']
    measured_bounds=bounds.copy()
    if interpretation=='closed_assembly_excludes_bump':
        # An explicitly different future asset hypothesis only. Never silently
        # stack bump height on the user measurement in the primary version.
        measured_bounds[1]=np.ptp(np.concatenate([body,button+[0,h['button_center_y_m'],h['button_closed_center_z_m']]]),axis=0)[1]
    assert np.allclose(measured_bounds,[m['overall_max_width_m'],m['overall_thickness_m'],m['overall_length_m']],atol=1e-9)
    s.update(asset_urdf=str((a.output/'mobility.urdf').resolve().relative_to(ROOT)),
        generated_audit=dict(closed_envelope_xyz_m=bounds.tolist(),collision_components=3,passive_prismatic_dofs=1,
            button_length_m=float(np.ptp(button[:,2])),travel_m=j['travel_m'],bump_height_m=h['bump_height_m'],
            thickness_measurement_interpretation=interpretation,
            interpretation='Envelope agreement under the declared thickness hypothesis, not a measured CAD replica',
            baseline_urdf_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest()))
    s['file_sha256']={str(p.relative_to(a.output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.rglob('*')) if p.is_file()}
    (a.output/'asset-spec.json').write_text(json.dumps(s,indent=2)+'\n')
    print(json.dumps(s['generated_audit']))


if __name__=='__main__':main()
