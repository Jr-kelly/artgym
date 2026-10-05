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
    p.add_argument('--thumb-lateral-bias-m',type=float,default=0.)
    p.add_argument('--thumb-normal-up',action='store_true')
    p.add_argument('--thumb-face-toward-cap',action='store_true',help='Authored pad+X toward knife is negative knifeY; opposite cap outward normal')
    p.add_argument('--preserve-middle-axis',action='store_true',help='Retain middle support axial contact while shifting wrist/tail-side digits to clear corner')
    p.add_argument('--grip-tail-shift-m',type=float,default=0.,help='Common geometric grasp relocation toward tail; thumb IK compensates to retain observed cap contact')
    for name in ['estimate', 'plan', 'reference', 'localization', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--body-root-inset', type=float, default=.006,
                   help='Known initial body-root inset, not combined COM; same rule for every estimate')
    a = p.parse_args()
    assert .0035 <= a.body_root_inset <= .01
    a.output.mkdir(parents=True, exist_ok=False)
    estimate=json.loads(a.estimate.read_text())
    from scripts.wuji_once_estimated_collision_geometry import build
    proxy=build(estimate,a.output/'estimated-collision')
    plan=json.loads(a.plan.read_text())
    assert 0<=a.grip_tail_shift_m<=.012
    if a.grip_tail_shift_m:plan['wrist_in_knife'][2][3]-=a.grip_tail_shift_m
    reference=json.loads(a.reference.read_text())
    loc=json.loads(a.localization.read_text())
    g=DigitGeometry()
    new, _, ref, audit=adapt(estimate, copy.deepcopy(plan),
        {'post_lift_target_q':plan['close_q']}, copy.deepcopy(reference),
        support_surface_scaling=True, geometry=g,thumb_contact_bias_m=[a.thumb_lateral_bias_m,0,a.grip_tail_shift_m] if a.grip_tail_shift_m or a.thumb_lateral_bias_m else None,support_contact_bias_m={'middle':[0,0,a.grip_tail_shift_m]} if a.preserve_middle_axis else None,thumb_normal_target=[0,-1,0] if a.thumb_face_toward_cap else [0,1,0] if a.thumb_normal_up else None)
    # Preserve the original motor reserve, rather than inheriting the nominal
    # path's certificate. Full motion and whole-hand geometry are recertified.
    new['close_q']=np.clip(new['close_q'],g.w.lower+.005,g.w.upper-.005).tolist()
    new['close_waypoints'][-1]['q']=new['close_q']
    new['open_q']=np.clip(new['open_q'],g.w.lower+.005,g.w.upper-.005).tolist()
    new['close_waypoints'][0]['q']=new['open_q']
    from scripts.wuji_once_estimated_collision_geometry import rematch_open_preform
    new=rematch_open_preform(new,proxy)
    if 'axial_jacobian_m_per_rad' in ref['rows'][0]:
        from scripts.wuji_traction_axial_geometry import attach_axial_jacobians
        ref=attach_axial_jacobians(new,ref)
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
    audit.update(grip_tail_shift_m=a.grip_tail_shift_m,scope=__doc__,body_root_inset_m=a.body_root_inset,
                 arm_ik=error,original_mesh_acquisition_and_full40_motor_certificate_pending=True,once_estimated_collision_spec=str(proxy))
    for name,value in [('motor-plan.json',new),('reference.json',ref),
                       ('localization.json',loc),('calibration.json',cal),('adaptation-audit.json',audit)]:
        (a.output/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(reference_ik_pass=ref['all_feasible'],arm_ik=error,
                         trajectory_error_m=audit['trajectory_max_error_m'])))
    assert ref['all_feasible'] and error['position_m']<.001 and error['rotation_rad']<.02


if __name__=='__main__':main()
