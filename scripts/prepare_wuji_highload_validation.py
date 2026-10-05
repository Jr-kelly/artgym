"""Predeclare two new joint conditions for the frozen highload engineering candidate.

Synthetic initial estimates with declared nonzero error, no asset-ID policy
selection. These conditions must not be used to tune the delivered candidate.
Physical geometry, mass and inertia change together; original rail preserved.
"""
import argparse,hashlib,json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    source=Path('assets/objects/knife_wuji_real_size_20261002/000')
    meta=json.loads((source/'parameters.json').read_text());entries=[]
    cases=[('unseen05',[.0155,.0115,.134],[-.0004,.0003,-.002],.35,.78,0,.0004,.00015,'constant'),
           ('unseen06',[.017,.013,.137],[.0004,-.0003,.004],.35,.82,1,.0004,.00015,'sinusoidal')]
    for i,(label,size,shift,load,friction,delay,noise,bias,profile) in enumerate(cases):
        folder=a.output/label;folder.mkdir();size=np.asarray(size);shift=np.asarray(shift)
        shutil.copy2(source/'slider-shoulder.obj',folder/'slider-shoulder.obj')
        tree=ET.parse(source/'mobility.urdf');origin=np.asarray(meta['slider_origin'])+shift;origin[1]+=(size[1]-.012)/2
        for item in tree.findall("./link[@name='link_0']/visual/geometry/box")+tree.findall("./link[@name='link_0']/collision/geometry/box"):item.set('size',' '.join(map(str,size)))
        tree.find('./joint/origin').set('xyz',' '.join(map(str,origin)))
        mass=.029*float(np.prod(size)/np.prod([.016,.012,.135]));inert=tree.find("./link[@name='link_0']/inertial");inert.find('mass').set('value',str(mass));x,y,z=size
        for key,val in zip(['ixx','iyy','izz'],[mass*(y*y+z*z)/12,mass*(x*x+z*z)/12,mass*(x*x+y*y)/12]):inert.find('inertia').set(key,str(val))
        tree.write(folder/'mobility.urdf',encoding='utf-8',xml_declaration=True)
        error=np.array([.00018,-.00015,.00025])*(-1 if i%2 else 1)
        estimate=dict(source='Fresh synthetic once observation, fixed declared error; frozen before execution and never used for tuning',uncertainty_m=.0003,handle_size_WTL_m=(size+error).tolist(),slider_size_WTL_m=meta['slider_size'],slider_contact_shift_m=(shift+error).tolist())
        (folder/'once-estimate.json').write_text(json.dumps(estimate,indent=2))
        par=dict(meta,id=label,split='fresh-joint-validation-never-training',handle_size=size.tolist(),masses=[mass,.006],slider_origin=origin.tolist(),slider_initial_center=(origin+[0,0,meta['joint_lower']]).tolist(),scope=__doc__)
        (folder/'parameters.json').write_text(json.dumps(par,indent=2))
        flags=['--initial-estimate',str(folder/'once-estimate.json'),'--knife-asset',str(folder/'mobility.urdf'),'--load',str(load),'--detent',str(load),'--hand-friction',str(friction),'--actuation-delay-frames',str(delay),'--observation-noise',str(noise),'--observation-bias',str(bias),'--load-profile',profile,'--seed',str(2026100535+i)]
        entries.append(dict(label=label,physical_dimensions_WTL_m=size.tolist(),actual_slider_shift_m=shift.tolist(),flags=flags,asset_sha256=hashlib.sha256((folder/'mobility.urdf').read_bytes()).hexdigest()))
    result=dict(scope=__doc__,frozen_candidate='research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json',candidate_sha256=hashlib.sha256(Path('research/highload-20261005/FROZEN-ENGINEERING-CANDIDATE.json').read_bytes()).hexdigest(),entries=entries)
    (a.output/'registry.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
