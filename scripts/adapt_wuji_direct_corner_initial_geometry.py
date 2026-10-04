"""Once-estimate adaptation of the direct wrap/corner pickup, without transfer.

The input is a labelled noisy initial observation. It does not read an asset
ID, physical geometry, contact, force, or a running object's state. Original
meshes and actuator limits must be screened separately before execution.
Pad IK preserves nominal preload; physical joint/pad support is not assumed.
"""
import argparse, copy, json
from pathlib import Path
import numpy as np
from scripts.plan_wuji_initial_geometry import adapt
from scripts.g2_contact_geometry import DigitGeometry
from scripts.g2_kinematics import G2Kinematics


def main():
    p = argparse.ArgumentParser()
    for name in ['estimate', 'plan', 'reference', 'localization', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--body-root-inset', type=float, default=.006,
                   help='Known initial body-root inset, not combined COM; same rule for every estimate')
    a = p.parse_args()
    assert .0035 <= a.body_root_inset <= .01
    a.output.mkdir(parents=True, exist_ok=False)
    estimate=json.loads(a.estimate.read_text())
    plan=json.loads(a.plan.read_text())
    reference=json.loads(a.reference.read_text())
    loc=json.loads(a.localization.read_text())
    g=DigitGeometry()
    new, _, ref, audit=adapt(estimate, copy.deepcopy(plan),
        {'post_lift_target_q':plan['close_q']}, copy.deepcopy(reference),
        support_surface_scaling=True, geometry=g)
    # Preserve the original motor reserve, rather than inheriting the nominal
    # path's certificate. Full motion and whole-hand geometry are recertified.
    new['close_q']=np.clip(new['close_q'],g.w.lower+.005,g.w.upper-.005).tolist()
    new['close_waypoints'][-1]['q']=new['close_q']
    world=np.asarray(loc['object_world_matrix'])
    world[0,3]=.3+a.body_root_inset
    world[2,3]=.7501+estimate['handle_size_WTL_m'][1]/2
    loc['object_world_matrix']=world.tolist()
    loc['object'][:3]=world[:3,3].tolist()
    loc.update(source='Known permissible tabletop corner placement and noisy initial dimensional observation',
               scope=__doc__, initial_body_root_inset_m=a.body_root_inset)
    loc.pop('initial_combined_com_scope',None)
    kin=G2Kinematics()
    arm,error=kin.solve(world@np.asarray(new['wrist_in_knife']),np.asarray(loc['grasp_q']))
    loc['grasp_q']=arm.tolist()
    new.update(object_world_matrix=world.tolist(),arm_grasp_q=arm.tolist(),arm_ik=error,
               initial_geometry_estimate=estimate)
    # One initial geometric prior: body follows the new grip, and the cap
    # estimate includes both body thickness and once-observed slider shift.
    relative=np.linalg.inv(np.asarray(new['wrist_in_knife']))
    cap=np.eye(4)
    cap[:3,3]=[0,.0075,-.02205]
    # The native policy adds initial dimensional/slider delta exactly once.
    # Keep this calibration unshifted to avoid applying that estimate twice.
    cal=dict(object_in_wrist=relative.tolist(),slider_in_wrist=(relative@cap).tolist(),
             initial_geometry_estimate=estimate,scope='Once noisy dimensional prior; never live object or slider truth')
    audit.update(scope=__doc__,body_root_inset_m=a.body_root_inset,
                 arm_ik=error,original_mesh_acquisition_and_full40_motor_certificate_pending=True)
    for name,value in [('motor-plan.json',new),('reference.json',ref),
                       ('localization.json',loc),('calibration.json',cal),('adaptation-audit.json',audit)]:
        (a.output/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(reference_ik_pass=ref['all_feasible'],arm_ik=error,
                         trajectory_error_m=audit['trajectory_max_error_m'])))
    assert ref['all_feasible'] and error['position_m']<.001 and error['rotation_rad']<.02


if __name__=='__main__':main()
