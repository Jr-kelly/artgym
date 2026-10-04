"""Separate diagnostic asset: split original slider mass with an axial serial elastic sensor."""
import argparse,json,copy,shutil,xml.etree.ElementTree as ET
from pathlib import Path

def build(output,source):
 output.mkdir(parents=True,exist_ok=False);root=ET.parse(source).getroot();slider=root.find("link[@name='link_1']");original_mass=float(slider.find('inertial/mass').get('value'));carrier_mass=original_mass/3;cap_mass=original_mass*2/3
 slider.find('inertial/mass').set('value',str(cap_mass))
 for k in ['ixx','iyy','izz']:n=slider.find('inertial/inertia');n.set(k,str(float(n.get(k))*cap_mass/original_mass))
 carrier=ET.Element('link',{'name':'load_cell_carrier'});inertial=copy.deepcopy(slider.find('inertial'));inertial.find('mass').set('value',str(carrier_mass))
 for k in ['ixx','iyy','izz']:n=inertial.find('inertia');n.set(k,str(float(n.get(k))/2))
 carrier.append(inertial);root.insert(1,carrier);rail=root.find('joint');rail.find('child').set('link','load_cell_carrier')
 joint=ET.fromstring('<joint name="serial_load_cell" type="prismatic"><parent link="load_cell_carrier"/><child link="link_1"/><origin xyz="0 0 0"/><axis xyz="0 0 1"/><limit lower="-.002" upper=".002" effort="10" velocity="1"/><dynamics damping="0" friction="0"/></joint>');root.append(joint)
 for mesh in root.findall('.//mesh'):
  filename=mesh.get('filename');shutil.copy2(source.parent/filename,output/filename)
 ET.ElementTree(root).write(output/'mobility.urdf',encoding='utf-8',xml_declaration=True)
 par=json.loads((source.parent/'parameters.json').read_text());par['serial_load_cell']=dict(format='wuji-series-elastic-diagnostic-v1',spring_N_per_m=5000.,damper_N_s_per_m=2.,cap_mass_kg=cap_mass,carrier_mass_kg=carrier_mass,travel_limits_m=[-.002,.002],source_asset=str(source),original_slider_mass_kg=original_mass,scope='Diagnostic modifiedslider only. Passiveexplicit spring/damper force, no drive reference. Original total mass and cap collision preserved; axial compliance and split inertia alter dynamics. Never direct force measurement in original asset or hardware.')
 (output/'parameters.json').write_text(json.dumps(par,indent=2));return par['serial_load_cell']
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,default=Path('assets/objects/knife_wuji_real_size_20261002/000/mobility.urdf'));a=p.parse_args();print(json.dumps(build(a.output,a.source)))
if __name__=='__main__':main()
