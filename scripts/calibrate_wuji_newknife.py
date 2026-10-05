"""Fixed-body known-force diagnostic; never a free pickup/demo result."""
from isaacgym import gymapi,gymtorch
import torch
import argparse,json,xml.etree.ElementTree as E
from pathlib import Path
import numpy as np
from scripts.calibrate_wuji_solver_brake import run
from scripts.wuji_newknife_resistance import REFERENCE_N

def main():
 p=argparse.ArgumentParser();p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 tree=E.parse(a.asset);joint=tree.find('joint');joint.find('limit').set('lower','-100');joint.find('limit').set('upper','100');joint.find('limit').set('velocity','100')
 for node in tree.findall('.//mesh'):node.set('filename',str((a.asset.parent/node.get('filename')).resolve()))
 tree.write(a.output/'fixture.urdf',encoding='utf-8',xml_declaration=True)
 trials=[]
 for force,cap in [(0.1,0),(.68,REFERENCE_N),(.735,REFERENCE_N),(.79,REFERENCE_N),(-.68,REFERENCE_N),(-.79,REFERENCE_N),(.90,REFERENCE_N*1.12)]:
  r=run(a.output.resolve(),240,force,cap,25000 if cap else 0);trials.append(r)
  (a.output/'raw.json').write_text(json.dumps(trials,indent=2))
 effective_mass=.1/np.mean([x['acceleration'] for x in trials[0]['samples'][:3]])
 rows=[]
 for r in trials:
  last=r['samples'][-1];reaction=r['external_known_force_N']-effective_mass*last['acceleration'];rows.append(dict(known_external_N=r['external_known_force_N'],configured_capacity_N=r['drive_force_cap_N'],reported_velocity_m_s=last['v'],position_difference_velocity_m_s=last['dq']*240,displacement_m=last['q'],acceleration_inferred_opposing_N=reaction,scope='Fixture-only inference; native sensor is not promoted to trustworthy force channel'))
 result=dict(reference_N=REFERENCE_N,effective_mass_kg=effective_mass,rows=rows,interpretation='Finite25000Ns/m velocity brake creep checked by position differences; above cap accelerates. Capacity is not ideal static friction. Direction and threshold checked by response; no original-task axialB/C measurement.')
 (a.output/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
