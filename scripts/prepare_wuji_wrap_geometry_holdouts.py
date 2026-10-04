"""Four retained012-015 holdout geometries; no grasp-pool expansion or fitting.

Simulator identities remain external. Common planner consumes only labelled
noisy initial dimensional/slider observations; plan accuracy is not a contact
or physical success certificate. Original source2 initial motor layout retained.
"""
import argparse,json,copy,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.record_wuji_wrap_goal import record

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[1];scene=json.loads((root/'runs/wrap-force-20261004/batch/multi12-v1/scene.json').read_text());nominal=next(r for r in scene['initial_estimated_plans'] if r['selection_source']==2);rows=[];rng=np.random.default_rng(2026100437)
 for sid in ['012','013','014','015']:
  asset=root/'assets/objects/knife_wuji_acquired_family_20261003'/sid;par=json.loads((asset/'parameters.json').read_text());size=np.asarray(par['handle_size']);joint=ET.parse(asset/'mobility.urdf').find('.//joint[@type="prismatic"]');origin=np.fromstring(joint.find('origin').get('xyz'),sep=' ');axis=np.fromstring(joint.find('axis').get('xyz'),sep=' ');position=origin+float(joint.find('limit').get('lower'))*axis;delta=position-np.array([0.,.0075,-.02205]);delta[1]-=(size[1]-.012)/2;estimate=dict(source='Labelled synthetic noisy onceinitial dimensional/slider observation, heldout runtime; no asset ID supplied to planner',uncertainty_m=.00025,handle_size_WTL_m=(size+rng.uniform(-1,1,3)*[.00025,.00025,.0005]).tolist(),slider_size_WTL_m=par['slider_size'],slider_contact_shift_m=(delta+rng.uniform(-.00025,.00025,3)).tolist());folder=a.output/sid;folder.mkdir();record('geometry_holdout_initial_plan_started',evidence=str(folder),config={'runtime_geometry':sid,'split':'heldout','observation':estimate},next='Common geometry adaptation without physical identity input; motor self/velocity feasibility then actual helddiagnostic')
  plan,unused,reference,audit=adapt(estimate,copy.deepcopy(nominal['motor_plan']),{'post_lift_target_q':nominal['motor_plan']['close_q']},copy.deepcopy(nominal['thumb_reference']),support_surface_scaling=True,support_fingers=('index','middle','ring','pinky'));
  from scripts.wuji_kinematics import WujiKinematics
  hand=WujiKinematics();plan['close_q']=np.clip(plan['close_q'],hand.lower+.005,hand.upper-.005).tolist();plan['close_waypoints'][-1]['q']=plan['close_q'];plan['initial_geometry_estimate']=estimate;row=dict(nominal,estimate=estimate,motor_plan=plan,thumb_reference=reference,support_target_q=plan['close_q'],support_motor_waypoints=[dict(time_s=r['time_s'],q=plan['close_q']) for r in nominal['support_motor_waypoints']]);spec=dict(scene,initial_estimated_plans=[row],plan=plan,calibration=row['calibration'],geometry_holdout_scope=__doc__)
  (folder/'scene.json').write_text(json.dumps(spec,indent=2)+'\n');(folder/'reference.json').write_text(json.dumps(reference,indent=2)+'\n');(folder/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');entry=dict(instance=sid,split='heldout',asset=str(asset.relative_to(root)/'mobility.urdf'),asset_sha256=hashlib.sha256((asset/'mobility.urdf').read_bytes()).hexdigest(),scene=str(folder/'scene.json'),planner_accuracy_passed=bool(reference['all_feasible']),motor_collision_certified=False,physical_evaluated=False);rows.append(entry);record('geometry_holdout_initial_plan_completed',evidence=str(folder),conclusion=entry,next='Screen original motor self/velocity geometry before any physical validation; not training data')
 (a.output/'registry.json').write_text(json.dumps(dict(scope=__doc__,geometry_split={'train':'000–011','heldout':'012–015'},entries=rows),indent=2)+'\n')
if __name__=='__main__':main()
