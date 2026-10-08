"""Small contact-preserving whole-hand pivot diagnostic, not a physics success."""
import json,argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.wuji_functional_entry_affordance import FunctionalEntryAffordance
from scripts.g2_kinematics import transform
from scripts.record_wuji_flat_table_event import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--env',type=int,required=True);p.add_argument('--frame',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);z=np.load(a.source/'actual-regrasp-traces.npz');q=z['dof'][a.frame,a.env,:27,0].astype(float);o=z['object'][a.frame,a.env];O=transform(o[:3],o[3:7]);slider=float(z['dof'][a.frame,a.env,27,0]);f=FunctionalEntryAffordance();X=np.linalg.inv(O)@f.kin.forward(q[:7]);center=np.array(f.assess(q,O,slider,False)['foot_in_knife_m']);rows=[]
 record('cap_normal_pivot_geometry_started',[str(a.source)],dict(env=a.env,frame=a.frame,question='Does a small wholehand pivot about the existing slider-roof contact align the original full30mm workspace? If yes physically test a coordinated pivot; if no change grasp rather than perjoint patches.'),next_step='Readonly sixdistinct yaw endpoints, then one necessaryphysicalcandidate only')
 for angle in [0,-15,15,-30,30,-45,45]:
  arm=q[:7].copy();path=[]
  for intermediate in np.linspace(0,angle,max(2,int(np.ceil(abs(angle)/2))+1)):
   R=Rotation.from_rotvec(np.array([0.,np.deg2rad(intermediate),0.])).as_matrix();Y=X.copy();Y[:3,:3]=R@X[:3,:3];Y[:3,3]=center+R@(X[:3,3]-center);arm,ik=f.kin.solve_near(O@Y,arm,max_step=.08,minimum_margin=.01);path.append(dict(angle_deg=float(intermediate),arm=arm.tolist(),ik=ik))
   if ik['position_m']>.0002 or ik['rotation_rad']>.002:break
  qnew=q.copy();qnew[:7]=arm;actualX=np.linalg.inv(O)@f.kin.forward(arm);af=f.assess(qnew,O,slider);gaps=[]
  for digit in ['index','middle','ring','pinky','thumb']:
   values=f.g.gaps(q[7:],actualX,slider,digit);gaps.extend(dict(digit=digit,hand_link=v['hand_link'],knife_link=v['knife_link'],gap_m=v['gap_lower_bound_m'])for v in values if v['gap_lower_bound_m']<-.0002)
  rows.append(dict(angle_deg=angle,arm_q=arm.tolist(),arm_delta=(arm-q[:7]).tolist(),ik=ik,arm_path=path,affordance=af,collision_proxy=gaps));print(json.dumps(dict(angle_deg=angle,ik=ik,full30_error_m=af['full30mm_FK_error_m'],tail_m=af['tail_roof_distance_m'],collision_proxy=gaps)),flush=True)
 result=dict(rows=rows,initial_X=X.tolist(),contact_pivot_knife_m=center.tolist(),scope=__doc__+' Geometric gaps are proxies, actualcapacity requiresnativecompleteB. No physicalstateschanged.');(a.output/'result.json').write_text(json.dumps(result,indent=2));(a.output/'planner.py').write_text(Path(__file__).read_text());record('cap_normal_pivot_geometry_terminal',[str(a.output/'result.json')],dict(eligible_angles=[x['angle_deg'] for x in rows if x['affordance']['reference_eligible']],rows=len(rows)),next_step='Chooseonlyiffullworkspace improvesandbearinggeometry permits; otherwisedistinctgraspmechanism')
if __name__=='__main__':main()
