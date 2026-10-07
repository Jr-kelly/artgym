"""Prepare a fresh natural table pinch around the new functional grip regions.

No historical loaded motor or operating handoff is consumed. Three measured
mesh regions are approached with clearance, then their own side/back normal
references act through the unchanged finite PD. The initial thumb stays free.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_direct_pickup import smooth
from scripts.check_wuji_action_quality import HandIntersection
from scripts.record_wuji_flat_table_event import record


def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.candidate.read_text());assert c['geometry_permits_native'] or c.get('native_precontact_grip_reachable',False);a.output.mkdir(parents=True,exist_ok=False)
 e=record('functional_table_pickup_prepare_start',[str(a.candidate),str(a.output)],config=dict(candidate='D672',uncertainty='Can tableclear opening/descent and25mmG2approach supportnewactualinitialpinch?',decision='Denseclear -> nativefreshpickup; blocked -> exactpathsegmentrepair only'),next_step='Prepare motoronly approach, original55g/physics preserved')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')
 g=DigitGeometry(max_face_axes=8,knife_spec=Path('assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json'));k=G2Kinematics();q=np.array(c['hand_q']);L=np.array(c['wrist_in_knife']);W=np.array(c['table_object_world'])@L
 theta=c.get('ring_corner_angle_rad',.7);dirs={'hand_r_index_pad_link':[1,0,0],'hand_r_middle_pad_link':[0,1,0],'hand_r_ring_link4':[-np.cos(theta),np.sin(theta),0.]};openq=q.copy()
 for part in c['contacts']:
  name=part['link'];digit=name.split('_')[2];ids=[g.w.names.index('hand_r_'+digit+'_joint'+str(j)) for j in range(1,5)];m=np.array(part['material']);target=np.array(part['point'])-.003*np.array(dirs[name])
  def residual(x):
   h=openq.copy();h[ids]=x;T=L@g.w.forward(h)[name];r=list((T[:3,:3]@m+T[:3,3]-target)*500);r.extend((x-q[ids])*.1)
   for gap in g.self_gaps(h,digit,certify_clearance_m=.0003):r.append(min(0.,gap['gap_lower_bound_m']-.0003)*600)
   return np.asarray(r)
  fit=least_squares(residual,q[ids],bounds=(g.w.lower[ids]+.04,g.w.upper[ids]-.04),max_nfev=60,diff_step=1e-5);openq[ids]=fit.x
 above=W.copy();above[2,3]+=.025;initial,ik=k.solve_near(above,np.array(c['arm_q']),max_step=1.2,minimum_margin=.06);check=HandIntersection();guard=[]
 for t in np.arange(3.,5.0001,1/30):
  u=smooth((t-3)/2);h=openq*(1-u)+q*u;goal=W.copy();goal[2,3]+=.02*(1-smooth(t-3));F=g.w.forward(h)
  height=min(float((v@(goal@F[n])[:3,:3].T+(goal@F[n])[:3,3])[:,2].min()-.75) for n,parts in g.meshes.items() for v,_ in parts);guard.append(dict(time_s=float(t),table_clearance_m=height,self=check.inspect(h)))
 summary=dict(min_table_clearance_m=min(v['table_clearance_m'] for v in guard),self_frames=sum(bool(v['self']) for v in guard),initial_arm_ik=ik,scope='Plannedgeometric descent only; actualcontact/servo tracking stillrequired');assert summary['min_table_clearance_m']>.0001 and not summary['self_frames'] and ik['position_m']<.0005,summary
 physics=json.loads(Path('runs/flat-table-20261006/direct/development/current-C560-relative-proximal-acquisition-v642/simulation/physics.json').read_text());spec=dict(duration_s=9.,initial_arm_q=initial.tolist(),wrist_in_knife=L.tolist(),open_q=openq.tolist(),close_q=q.tolist(),pregrasp_clearance_m=.02,lift_m=.025,arm_command_margin_rad=.06,material_points={v['link']:v['material'] for v in c['contacts']},grip_normal_reference_N={'hand_r_index_pad_link':float(.9*np.cos(theta)),'hand_r_middle_pad_link':.15,'hand_r_ring_link4':.9},grip_motor_margin_rad=.035,grip_force_directions_knife=dirs,hand_kp=physics['kp'][7:],knife_spec='assets/objects/knife_wuji_newknife_20261005/nominal-v5/spec.json')
 prefix=dict(duration_s=9.,physical_initial_xy=np.asarray(c['table_object_world'])[:2,3].tolist(),physical_initial_yaw_deg=c['table_yaw_degrees'],physical_initial_object_world=c['table_object_world'],direct_pickup=spec,rows=[dict(time_s=0.,arm_q=initial.tolist(),hand_q=openq.tolist())],candidate='D672',grasp_geometry=str(a.candidate),operating_geometry=c['operating'],lineage='D665functionalcornergrip -> D669tableinverse/D670forwardworkspace -> D672ownfreshpickup; source643geometryprior only, no oldrecordedcontrollerstage',scope=__doc__)
 (a.output/'prefix.json').write_text(json.dumps(prefix,indent=2));(a.output/'dense-approach-guard.json').write_text(json.dumps(dict(summary=summary,rows=guard),indent=2));print(json.dumps(summary),flush=True)
 e=record('functional_table_pickup_motor_prepared',[str(a.output/'prefix.json'),str(a.output/'dense-approach-guard.json')],config=dict(candidate='D672',grasp_end='Pendingnewnativepickup',support_layout='D666actualmesh threecarrierregions, initialThumbfree',control='D672 threeperpartnormaldirection boundedPD +25mmlift fordevelopment; heightnotacceptancerequirement',guard=summary),next_step='Freshnativepickup9s thenownactualstateflip; no oldC560motorconsumption')
 with Path('research/flat-table-20261006/CONTINUATION.md').open('a') as f:f.write('\n'+e['utc']+' '+json.dumps(e['config'])+'\n')

if __name__=='__main__':main()
