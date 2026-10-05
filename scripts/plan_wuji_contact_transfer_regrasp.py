"""A small motor-only post-lift regrasp path from existing pickup to new grip.
Known offline calibration only. No simulator reset, live object pose or fixture.
Arm velocity/table geometry and sampled motor self-clearance are screened;
contact continuity is intentionally left to an actual physical rollout.
"""
import argparse,json,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_cartesian_acquisition import plan_translation
from scripts.g2_table_collision import ArmTableCollision
from scripts.g2_contact_geometry import DigitGeometry
from scripts.wuji_kinematics import FINGERS

def main():
 p=argparse.ArgumentParser();p.add_argument('--resolve-index-middle',action='store_true');p.add_argument('--reachable-pinky-path',action='store_true',help='Use FK of bounded joint interpolation as pinky surface waypoint; other contact points retain Cartesian paths');p.add_argument('--knife-spec',type=Path,default=Path('research/robust-knife-family-20261003/real-knife-asset-spec.json'));p.add_argument('--table-y',type=float,default=-.25);p.add_argument('--pickup-plan',type=Path,required=True);p.add_argument('--acquisition',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--operation-plan',type=Path,required=True);p.add_argument('--resolve-ring-pinky',action='store_true',help='Track ring after pinky and penalize their actual collision-hull overlap during IK; final full-mesh preflight unchanged');p.add_argument('--staged-contact-gait',action='store_true',help='Move index then middle then pinky nominal contact sites while other sites remain fixed; originalIK/motorlimits/selfchecks');p.add_argument('--fixed-support-sites',action='store_true',help='Keep middle/pinky nominal contact points fixed during wrist transfer; requires contact-preserving-ik');p.add_argument('--contact-preserving-ik',action='store_true',help='Track nominal authored-mesh contact-point paths during wrist motion, rather than joint interpolation; actual contact remains unverified');p.add_argument('--output',type=Path,required=True);p.add_argument('--start',type=float,default=12);p.add_argument('--end',type=float,default=14.2);a=p.parse_args();assert 12<=a.start<a.end<=16-50/30 and not a.output.exists()
 old=json.loads(a.pickup_plan.read_text());new=json.loads(a.operation_plan.read_text());cal=json.loads(a.calibration.read_text());acq=json.loads(a.acquisition.read_text());k=G2Kinematics();g=DigitGeometry(max_face_axes=10000,knife_spec=a.knife_spec);arm0=np.array(acq['lift_q'][-1]);expected_knife=k.forward(arm0)@np.array(cal['object_in_wrist']);desired=expected_knife@np.array(new['wrist_in_knife']);path,arm_audit=plan_translation(k,arm0,desired,a.end-a.start,1/30,ArmTableCollision(.75,table_y=a.table_y))
 arm=np.array([arm0]+path);u=np.linspace(0,1,len(arm));fraction=u*u*u*(10-15*u+6*u*u);q0=np.array(old['close_q']);q1=np.array(new['close_q']);hand=q0[None]+fraction[:,None]*(q1-q0)[None]
 contact_audits=[]
 if a.contact_preserving_ik:
  vertices={f:np.concatenate([v for v,_ in g.meshes['hand_r_'+f+'_pad_link']]) for f in FINGERS}
  def points(q,wrist,normals):
   frames=g.w.forward(q);out=[]
   for f,n in zip(FINGERS,normals):
    mat=wrist@frames['hand_r_'+f+'_pad_link'];v=vertices[f]@mat[:3,:3].T+mat[:3,3];p=v@n;weight=np.exp(-(p-p.min())/.0002);out.append(weight@v/weight.sum())
   return np.array(out)
  normal0=np.array(old['contact_normals']);normal1=np.array(new['contact_normals']);world_to_knife=np.linalg.inv(expected_knife)
  endpoint0=points(q0,world_to_knife@k.forward(arm0),normal0);endpoint1=points(q1,np.array(new['wrist_in_knife']),normal1)
  assert not a.fixed_support_sites or a.contact_preserving_ik
  if a.fixed_support_sites:
   for f in ['middle','pinky']:endpoint1[FINGERS.index(f)]=endpoint0[FINGERS.index(f)]
  tracking=['thumb','index','middle','pinky','ring'] if a.resolve_ring_pinky else ['thumb','index','middle','pinky'] if a.staged_contact_gait or a.resolve_index_middle else ['thumb','middle','pinky'];active=[FINGERS.index(f) for f in tracking];previous=q0.copy()
  for i,(aq,alpha) in enumerate(zip(arm,fraction)):
   wrist=world_to_knife@k.forward(aq);progress=np.full(5,alpha)
   if a.staged_contact_gait:
    for f,first,last in ([('index',0.,.3),('middle',.3,.6),('pinky',.6,.8),('ring',.8,1.)] if a.resolve_ring_pinky else [('index',0.,.35),('middle',.35,.70),('pinky',.70,1.)]):
     v=np.clip((alpha-first)/(last-first),0,1);progress[FINGERS.index(f)]=v*v*v*(10-15*v+6*v*v)
   progress=progress[:,None];normals=normal0*(1-progress)+normal1*progress;normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8);target=endpoint0*(1-progress)+endpoint1*progress;prior=hand[i].copy()
   if a.reachable_pinky_path:target[FINGERS.index('pinky')]=points(prior,wrist,normals)[FINGERS.index('pinky')]
   def residual(q):
    value=np.r_[((points(q,wrist,normals)-target)[active]*1000).ravel(),.03*(q-prior),.02*(q-previous)]
    if a.resolve_index_middle:
     gaps=np.array([z['gap_lower_bound_m'] for z in g.pair_gaps(q,[('hand_r_index_link2','hand_r_middle_link2')])]);value=np.r_[value,np.minimum(gaps-.0001,0)*5000]
    if a.resolve_ring_pinky:
     pairs=[('hand_r_ring_'+x,'hand_r_pinky_'+y) for x in ['link3','link4','pad_link'] for y in ['link3','link4','pad_link']]
     gaps=np.array([z['gap_lower_bound_m'] for z in g.pair_gaps(q,pairs)]);value=np.r_[value,np.minimum(gaps-.0001,0)*3000]
    return value
   fit=least_squares(residual,previous,bounds=(g.w.lower+.005,g.w.upper-.005),max_nfev=100,diff_step=1e-5);hand[i]=fit.x;previous=fit.x
   contact_audits.append(dict(frame=i,max_active_point_error_m=float(np.linalg.norm(points(fit.x,wrist,normals)-target,axis=1)[active].max()),scope='Nominal motor surface points; not measured contact/force'))
 hand[0]=q0
 root=Path(__file__).resolve().parents[1];xml=ET.parse(root/g.w.config['asset']);velocity={j.get('name'):float(j.find('limit').get('velocity')) for j in xml.findall('joint') if j.get('type')=='revolute'};v=np.array([velocity[name] for name in g.w.names]);maximum_rates=np.max(abs(np.diff(hand,axis=0)),axis=0)*30;rate_ok=bool(np.all(maximum_rates<v))
 rows=[]
 for i in np.unique(np.linspace(0,len(arm)-1,11).astype(int)):
  q=hand[i];w=k.forward(arm[i]);frames=g.w.forward(q);tablegaps=[];selfgaps=[]
  for f in FINGERS:selfgaps+=g.self_gaps(q,f,certify_clearance_m=.000015)
  for name,meshes in g.meshes.items():
   frame=w@frames[name]
   for vertices,normals in meshes:
    vertices=vertices@frame[:3,:3].T+frame[:3,3];axes=np.r_[np.eye(3),normals@frame[:3,:3].T];projection=(vertices-np.array([.6,a.table_y,.725]))@axes.T;radius=abs(axes)@np.array([.3,.4,.025]);tablegaps.append(float(np.maximum(projection.min(0)-radius,-radius-projection.max(0)).max()))
  negative=[r for r in selfgaps if r['gap_lower_bound_m']<.000015-1e-7]
  rows.append(dict(frame=int(i),time_s=float(a.start+i/30),minimum_table_gap_m=min(tablegaps),uncertified_self_pairs=negative))
 passed=rate_ok and all(r['minimum_table_gap_m']>.0003 and not r['uncertified_self_pairs'] for r in rows)
 relative=np.linalg.inv(np.array(new['wrist_in_knife']));slider=relative.copy();slider[:3,3]+=relative[:3,:3]@np.array([0,.0075,.010624586881962734+new['planning_slider_m']])
 result=dict(format='wuji-postlift-regrasp-v1',args=vars(a),times_s=np.linspace(a.start,a.end,len(arm)).tolist(),arm_q=arm.tolist(),hand_q=hand.tolist(),object_in_wrist=relative.tolist(),slider_in_wrist=slider.tolist(),expected_knife_world=expected_knife.tolist(),nominal_pose_source='Once-loaded offline baseline grip calibration and known pickup lift motor command; not current simulator truth or real perception',scope=__doc__,preflight_passed=passed,hand_original_velocity_limits_passed=rate_ok,maximum_hand_command_rates_rad_s=maximum_rates.tolist(),sampled_geometry=rows,arm_audit=arm_audit,operation_plan=str(a.operation_plan),operation_plan_sha256=hashlib.sha256(a.operation_plan.read_bytes()).hexdigest(),contact_continuity_verified=False,initial_estimate_uncertainty='Nominal development path only; later paired evaluation must perturb initial estimates and actual pickup ends')
 result['contact_point_tracking']=contact_audits;result['tracking_fingers']=tracking if a.contact_preserving_ik else []
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,default=str,indent=2));print(json.dumps(dict(preflight_passed=passed,frames=len(arm),minimum_table_gap_m=min(r['minimum_table_gap_m'] for r in rows),uncertified_pairs=sum(len(r['uncertified_self_pairs']) for r in rows),rate_ok=rate_ok)));assert passed,'Do not execute rejected postlift path'
if __name__=='__main__':main()
