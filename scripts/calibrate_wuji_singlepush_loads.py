"""Minimal known-force fixture for increased capacities, never a task aid."""
from isaacgym import gymapi
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
from scripts.calibrate_wuji_solver_brake import run
def main():
 p=argparse.ArgumentParser();p.add_argument('--levels',type=float,nargs='+',default=[.73549875,1.,1.5]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);src=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5');tree=ET.parse(src/'mobility.urdf');joint=tree.find('joint');joint.find('limit').set('lower','-100');joint.find('limit').set('upper','100')
 for m in tree.findall('.//mesh'):m.set('filename',str((src/m.get('filename')).resolve()))
 tree.write(a.output/'fixture.urdf');rows=[]
 for cap in a.levels:
  for f in [cap*.95,cap+.0015]:
   r=run(a.output.resolve(),240,f,cap,25000);rows.append(r);(a.output/'raw.json').write_text(json.dumps(rows,indent=2))
 summary=[]
 for cap in a.levels:
  low,high=[r for r in rows if r['drive_force_cap_N']==cap];summary.append(dict(capacity_N=cap,below_force_N=low['external_known_force_N'],below_displacement_m=low['samples'][-1]['q'],above_force_N=high['external_known_force_N'],above_displacement_m=high['samples'][-1]['q'],threshold_response_passed=abs(low['samples'][-1]['q'])<.00002 and high['samples'][-1]['q']>.001))
 (a.output/'summary.json').write_text(json.dumps(dict(scope=__doc__,rows=summary,all_passed=all(r['threshold_response_passed'] for r in summary)),indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
