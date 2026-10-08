"""New balanced pad pickup and acquired whole-wrist roll in ONE fresh episode.

Geometric motor-time allocation from original .006rad command increments.
No fingertip follower, state restoration or learned/physical B substitution.
"""
import argparse,json,sys,subprocess,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 src=Path('runs/flat-table-20261006/direct/development/balanced-flexed-pad-fresh-lift-v868');z=np.load(src/'simulation/trace.npz');f=FunctionalEntryAffordance();O=transform(z['object'][-1,:3],z['object'][-1,3:7]);W=f.kin.forward(z['applied_target'][-1,:7]);q=z['applied_target'][-1,:7].astype(float).copy()
 # Audit found min wholehandknife floor -16.3mm over fixedwrist roll.
 # Raising 60mm gives >=40mm predicted floor throughout, not a fixture.
 for u in np.linspace(0,1,61):
  G=W.copy();G[2,3]+=.06*u;q,e=f.kin.solve_near(G,q,max_step=.12,minimum_margin=.06);assert e['position_m']<.0001 and e['rotation_rad']<.001,e
 W[2,3]+=.06;axis=O[:3,2];times=[[0.,0.]];audit=[];previous=q.copy()
 for angle in np.linspace(.5,145,290):
  G=W.copy();G[:3,:3]=Rotation.from_rotvec(axis*np.deg2rad(angle)).as_matrix()@W[:3,:3];q,e=f.kin.solve_near(G,q,max_step=.12,minimum_margin=.06);assert e['position_m']<.0001 and e['rotation_rad']<.001,e
  step=float(abs(q-previous).max());frames=max(1,int(np.ceil(step/.0045)));times.append([times[-1][0]+frames/30,angle/145]);audit.append(dict(angle_deg=float(angle),frames=frames,arm_q=q.tolist(),diagnostic=e));previous=q.copy()
 duration=times[-1][0];base=json.loads((src/'prefix.json').read_text());s=base['direct_pickup'];first=s['continuous_stages'][0];first.update(duration_s=6.,world_translation_m=[0,0,.15],world_translation_duration_s=5.);stage=dict(first);stage.update(name='acquired_pad_whole_wrist_roll',duration_s=duration+2.,world_translation_m=[0,0,0],world_translation_duration_s=1.,world_rotation_degrees=145.,world_rotation_axis_knife=[0,0,1],world_rotation_duration_s=duration,world_rotation_pivot='wrist',world_rotation_fraction_rows=times);s['continuous_stages']=[first,stage];base['duration_s']=12.+duration+2.;base['scope']=__doc__;(a.output/'prefix.json').write_text(json.dumps(base,indent=2));proof=dict(source_actual_trace=str(src/'simulation/trace.npz'),lift_m=.15,roll_degree=145.,roll_s=duration,original_motor_step_rad=.006,time_allocation_step_rad=.0045,rows=audit,scope='Geometry-only fixedwrist roll feasible; truebearing must be observed in currentfreshphysics');(a.output/'roll-preflight.json').write_text(json.dumps(proof,indent=2))
 cmd=json.loads((src/'command.json').read_text());cmd[0]=sys.executable
 for flag,value in [('--flat-table-prefix',str(a.output/'prefix.json')),('--output',str(a.output/'simulation'))]:cmd[cmd.index(flag)+1]=value
 (a.output/'command.json').write_text(json.dumps(cmd,indent=2));runtime=a.output/'controller-source';runtime.mkdir()
 for name in ['prepare_wuji_balanced_pad_fresh_roll.py','wuji_direct_route.py','wuji_direct_pickup.py','run_g2_flat_table_demo.py']:shutil.copyfile(Path('scripts')/name,runtime/name)
 record('balanced_pad_fresh_acquired_wholewrist_roll_started_v870',[str(a.output/'command.json'),str(a.output/'roll-preflight.json')],dict(roll_s=duration,total_s=base['duration_s'],lift_m=.15,scope=__doc__,rejected_knife_center_pivot='145deg path reaches arm workspace limits, FK119mm; wristcenter145deg exactreachable. Additional60mm lift fromwholehand floor bound.'),updates={'add_active_jobs':[str(a.output)]},next_step='Actualfreshlift+roll allframecarry/H; ifheld, original773contact/30mmB workspace preflight then sameepisodefullB')
 try:subprocess.run(cmd,check=True)
 finally:record('balanced_pad_fresh_acquired_wholewrist_roll_terminal_v870',[str(a.output/'simulation')],updates={'remove_active_jobs':[str(a.output)]},next_step='Actualwholecarry/H/contact decide functionalthumbentry and fulloriginalB; geometry alone no acceptance')
if __name__=='__main__':main()
