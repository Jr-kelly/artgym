"""Offline G2/Wuji command replay from measured joints and issued targets only.

This exercises the existing native R800/residual bridge without creating a
physics scene or connecting to hardware. The input NPZ has a deliberately small
allowlist; contact, current object pose, slider state and load are not accepted.
It does not establish SDK compatibility or real motor performance.
"""
import argparse, hashlib, json, time
from pathlib import Path
import isaacgym  # The installed IsaacGym package must precede torch.
import numpy as np
from scripts.g2_kinematics import G2Kinematics
from scripts.g2_r800_policy import G2R800Policy
from scripts.wuji_goal_common import configuration

R = Path(__file__).resolve().parents[1]
LEGAL_FIELDS = {'clock_s', 'hand_measured_q', 'arm_measured_q', 'issued_hand_target'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scheduled-target-holds',action='store_true',help='Knownclock finitePD issuedposition holds after complete reference; never forcefeedback');p.add_argument('--prewarm-iterations',type=int,default=0);p.add_argument('--input', type=Path, required=True)
    p.add_argument('--estimate', type=Path, required=True)
    p.add_argument('--calibration', type=Path, required=True)
    p.add_argument('--motor-prefix-plan',type=Path,help='Once-known closure/lift/transfer plan for learned acquisition; future recorded targets never used as reference')
    p.add_argument('--postlift-regrasp',type=Path,help='Known motor/arm transfer plus fixed initial operation prior; never live object/contact')
    p.add_argument('--proprioceptive-pressure-config',type=Path,help='Same legal joint/issued-history pressure proxy; requires complete prefix from before8s')
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--takeover-seconds',type=float,default=16.,help='Known learnedpreparation clock, operation still16s; requires preceding50 actualmeasured/issuedframes')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    with np.load(a.input) as data:
        assert set(data.files) == LEGAL_FIELDS, 'Supply only measured/issued legal arrays'
        samples = {k: data[k].copy() for k in LEGAL_FIELDS}
    times = samples['clock_s']
    n = len(times)
    assert 5<=a.takeover_seconds<=16 and times[0]<=a.takeover_seconds-50/30+1e-7
    assert n >= 50 and np.allclose(np.diff(times), 1/30, atol=1e-7)
    for k, width in [('hand_measured_q', 20), ('arm_measured_q', 7), ('issued_hand_target', 20)]:
        assert samples[k].shape == (n, width) and np.isfinite(samples[k]).all()
    estimate = json.loads(a.estimate.read_text())
    calibration = json.loads(a.calibration.read_text())
    obj = np.asarray(calibration['object_in_wrist'], dtype=float)
    slider = np.asarray(calibration['slider_in_wrist'], dtype=float)
    center = np.asarray(estimate.get('initial_object_center_shift_knife_m', [0, 0, 0]))
    obj[:3, 3] += obj[:3, :3] @ center
    shift = center + np.asarray(estimate['slider_contact_shift_m'])
    shift += np.array([0, (estimate['handle_size_WTL_m'][1]-.012)/2, 0])
    slider[:3, 3] += obj[:3, :3] @ shift
    cfg = configuration('wuji_geometry', 1,
        ['object=knife_wuji_real_size_20261002', 'hand=wuji_paper_official_actuator',
         '+task.env.geometryRound=real-size-student-adaptation-20261002'],
        train='wujiAcquisitionSAPG', seed=2026100301)
    teacher = R/'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth'
    student = R/'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth'
    policy = G2R800Policy(cfg, teacher, student,
        geometry=estimate['handle_size_WTL_m']+estimate.get('slider_size_WTL_m',[.01, .003, .03]),
        residual_checkpoint=a.checkpoint, thumb_reference_override=a.reference)
    pressure_spec=json.loads(a.proprioceptive_pressure_config.read_text()) if a.proprioceptive_pressure_config else policy.proprioceptive_pressure_spec
    regrasp=json.loads(a.postlift_regrasp.read_text()) if a.postlift_regrasp else None
    if pressure_spec:
        assert times[0]<8 and a.takeover_seconds==16 and a.motor_prefix_plan
        assert not pressure_spec.get('coordinate_support'), 'Selected thumb-only controller replay'
        if pressure_spec.get('model_implementation')=='analytic-torch-v1':
            from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure as Adapter
        else:
            from scripts.wuji_proprioceptive_pressure import ProprioceptivePressure as Adapter
        policy.pressure_adapter=Adapter(pressure_spec,obj[:3,1],np.array(cfg.hand.dof_props.stiffness))
    if policy.support_load_features is not None:
        assert times[0]<=14.1+1e-7, 'Loadfeatures require57 legalprefixframes from14.1s for52frame calibration and5frame causalvelocity filter'
        policy.support_load_features.reset(__import__('torch').tensor([0],device=policy.player.device),policy.tensor(obj[:3,1]))
    plan=json.loads(a.motor_prefix_plan.read_text()) if a.motor_prefix_plan else None
    assert (5 if policy.learned_acquisition_prefix else 8)<=a.takeover_seconds<=16
    if policy.learned_acquisition_prefix and a.takeover_seconds<16:
        assert plan is not None, 'Learned acquisition requires its once-known motor plan'
        assert not plan.get('lift_preload_height_m'), 'Measured-height variant needs a separate replay adapter'
    from scripts.wuji_known_acquisition_prefix import hand_reference
    if a.scheduled_target_holds:assert policy.thumb_reference is not None and not policy.thumb_reference.pacing and policy.thumb_reference.duration<5
    kin = G2Kinematics()
    taken = False
    targets, actions, errors = [], [], [];warmup=None;latencies=[]
    for i, t in enumerate(times):
        q = samples['hand_measured_q'][i]
        if policy.support_load_features is not None:
            previous=samples['issued_hand_target'][max(0,i-1)]
            policy.support_load_features.observe(policy.tensor(q),policy.tensor(previous),__import__('torch').tensor([round(float(t)*30)],device=policy.player.device))
        policy.record(q, policy.last_action if taken else np.zeros(20))
        if pressure_spec and regrasp and pressure_spec.get('transfer_normal_from_known_arm_fk'):
            axis=np.asarray(regrasp['expected_knife_world'])[:3,1]
            policy.pressure_adapter.normal=kin.forward(samples['arm_measured_q'][i])[:3,:3].T@axis
        if t < a.takeover_seconds-1e-7:
            if pressure_spec and t>=8:
                assert i>0
                desired=hand_reference(plan,float(t))
                if regrasp and t>=regrasp['times_s'][0]:
                    values=np.asarray(regrasp['hand_q']);desired=np.array([np.interp(t,regrasp['times_s'],values[:,j]) for j in range(20)])
                policy.pressure_adapter.command(q,samples['issued_hand_target'][i-1],desired,float(t))
            continue
        if not taken:
            assert i > 0 and len(policy.history) == 50
            if policy.table_initial_prior_from_measured_arm:
                assert plan is not None
                from scripts.wuji_initial_table_prior import measured_arm_relative
                obj,slider=measured_arm_relative(plan,estimate,kin.forward(samples['arm_measured_q'][i]))
            policy.takeover_estimate(q, samples['issued_hand_target'][i-1], obj, slider, clock_s=float(t))
            if a.prewarm_iterations:
                gravity=kin.forward(samples['arm_measured_q'][i])[:3,:3].T@np.array([0.,0.,-1.])
                warmup=policy.prewarm(q,0.,gravity,a.prewarm_iterations,clock_s=float(t),known_prefix_target=hand_reference(plan,float(t)) if policy.learned_acquisition_prefix and t<16 else None)
            taken = True
        goal = .04 if t>=16-1e-7 and int(round((t-16)*30))//150 % 2 == 0 else 0.
        gravity = kin.forward(samples['arm_measured_q'][i])[:3, :3].T @ np.array([0., 0., -1.])
        begin=time.perf_counter()
        target, action = policy.command(q, goal, wrist_gravity=gravity, clock_s=float(t),issued_target_hold=a.scheduled_target_holds and t>=16 and ((float(t)-16)%5)>=policy.thumb_reference.duration+1/30-1e-7,known_prefix_target=hand_reference(plan,float(t)) if policy.learned_acquisition_prefix and t<16 else None)
        latencies.append((time.perf_counter()-begin)*1000)
        assert policy.last_encoder_input.shape == (2076,)
        assert policy.last_public_features.shape == ((170 if policy.history_features else 154)+(9 if policy.support_load_features is not None else 0)+(8 if policy.support_estimator is not None else 0),)
        assert np.isfinite(target).all() and np.isfinite(policy.last_encoder_input).all()
        assert np.all(target >= policy.fk.lower-1e-6) and np.all(target <= policy.fk.upper+1e-6)
        targets.append(target); actions.append(action)
        errors.append(float(np.max(np.abs(target-samples['issued_hand_target'][i]))))
    assert taken and len(targets) > 0
    np.savez_compressed(a.output/'commands.npz', targets=targets, actions=actions)
    report = dict(scope='Offline inference only; no physics scene, robot SDK, or current object/contact/load input',
        known_prefix_plan_sha256=hashlib.sha256(a.motor_prefix_plan.read_bytes()).hexdigest() if a.motor_prefix_plan else None,initial_pose_prior_scope='Known table plus once-estimated geometry transformed by measured arm FK' if policy.table_initial_prior_from_measured_arm else 'Once loaded held prior',prewarm=warmup,physics_performance_claim=False, real_robot_ran=False,learned_takeover_seconds=a.takeover_seconds,support_latch_after_preparation=policy.support_latch_after_preparation, control_hz=30, r800_input_dim=2076,
        scheduled_target_holds=a.scheduled_target_holds,scheduled_target_hold_scope='Knowncommandclock positionhold; network/reference/measuredhistory continue; not constantforce' if a.scheduled_target_holds else None,pressure_spec=pressure_spec,postlift_regrasp_sha256=hashlib.sha256(a.postlift_regrasp.read_bytes()).hexdigest() if a.postlift_regrasp else None,
        inference_command_latency_ms=dict(first=latencies[0],median=float(np.median(latencies)),p95=float(np.percentile(latencies,95)),maximum=max(latencies),frames_above_33_333ms=sum(x>1000/30 for x in latencies),scope='Recorded legal-input offline command computation under current machine load; excludes SDK, physical motors and measurement acquisition'),
        residual_input_dim=(170 if policy.history_features else 154)+(9 if policy.support_load_features is not None else 0)+(8 if policy.support_estimator is not None else 0), support_load_feature_spec=policy.support_load_feature_spec, support_estimator_metadata={k:v for k,v in policy.support_estimator.spec.items() if k not in ['model','input_mean','input_std','history_mean','history_std']} if policy.support_estimator is not None else None,support_delta_coordinates={k:v for k,v in policy.support_delta_coordinates.spec.items() if k!='reference_actor_state'} if policy.support_delta_coordinates is not None else None, command_frames=len(targets),
        max_target_difference_from_recorded_rad=max(errors),
        hand_joint_names=policy.fk.names, arm_joint_names=kin.names,
        input_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),
        checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        remaining_hardware_requirements=['Actual G2/Wuji SDK joint-name and unit mapping',
            'Measured joint timestamps and bounded position-target interface',
            'Measured initial geometry/grip calibration; effort/gravity implementation verification'])
    (a.output/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
