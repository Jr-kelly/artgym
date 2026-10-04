"""Two finite original-model boundary challenges, never added to the grasp pool.

Density/inertia follow the existing family approximation. The planner receives
only a synthetic once-estimate with declared error, never the asset identity.
"""
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 source=Path('assets/objects/knife_wuji_real_size_20261002/000');meta=json.loads((source/'parameters.json').read_text());entries=[]
 for label,size,shift in [('thin130x14x10',[.014,.010,.130],[0,0,0]),('nominal-axial-plus5mm',[.016,.012,.135],[0,0,.005])]:
  folder=a.output/label;folder.mkdir();size=np.asarray(size);shift=np.asarray(shift);shutil.copy2(source/'slider-shoulder.obj',folder/'slider-shoulder.obj');tree=ET.parse(source/'mobility.urdf');origin=np.asarray(meta['slider_origin'])+shift;origin[1]+=(size[1]-.012)/2
  for item in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):item.set('size',' '.join(map(str,size)))
  tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)));mass=.029*float(np.prod(size)/np.prod([.016,.012,.135]));inert=tree.find("./link[@name='link_0']/inertial");inert.find('mass').set('value',str(mass));x,y,z=size
  for key,val in zip(['ixx','iyy','izz'],[mass*(y*y+z*z)/12,mass*(x*x+z*z)/12,mass*(x*x+y*y)/12]):inert.find('inertia').set(key,str(val))
  tree.write(folder/'mobility.urdf',encoding='utf-8',xml_declaration=True)
  estimate=dict(source='Synthetic once observation with fixed declared nonzero error, no physical identity input',uncertainty_m=.0003,handle_size_WTL_m=(size+[.00015,-.00012,.0003]).tolist(),slider_size_WTL_m=meta['slider_size'],slider_contact_shift_m=(shift+[.00015,-.00015,.00015]).tolist())
  (folder/'once-estimate.json').write_text(json.dumps(estimate,indent=2));par=dict(meta,id=label,split='boundary-diagnostic-not-training',handle_size=size.tolist(),masses=[mass,.006],slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),total_size_lwt=[float(z),float(x),float(y+.003)],scope=__doc__);(folder/'parameters.json').write_text(json.dumps(par,indent=2));entries.append(dict(label=label,asset=str(folder/'mobility.urdf'),estimate=str(folder/'once-estimate.json'),physical_dimensions_WTL_m=size.tolist(),actual_slider_shift_m=shift.tolist(),sha256=hashlib.sha256((folder/'mobility.urdf').read_bytes()).hexdigest()))
 (a.output/'registry.json').write_text(json.dumps(dict(scope=__doc__,entries=entries,weight_selection_changed=False,original_geometry_split_preserved=True),indent=2));print(json.dumps(entries))
if __name__=='__main__':main()
