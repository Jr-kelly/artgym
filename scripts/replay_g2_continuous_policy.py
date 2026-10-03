"""Replay measured inputs through the actual G2 policy, with file-only output.

Compare independently inferred actions and motor targets with a retained
continuous simulation trace. History follows recorded issued commands so an
error does not silently change subsequent input packets. No physics or robot
transport is constructed, and current object/contact/slider truth is not read.
"""
import argparse, hashlib, json
from pathlib import Path
from scripts.wuji_goal_common import configuration
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics
from scripts.wuji_robust_learning import R800, TEACHER
import numpy as np
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    trace = np.load(args.demo/'trace.npz')
    plan = json.loads((args.demo/'plan.json').read_text())
    physics = json.loads((args.demo/'physics.json').read_text())
    assert plan['args']['residual_checkpoint'] and not plan['args']['thumb_script']
    source_report = json.loads((args.demo/'report.json').read_text())
    assert source_report['weight_sha256'][plan['args']['residual_checkpoint']] == hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    calibration = plan['handover_calibration']
    assert calibration
    cfg = configuration('wuji_geometry', 1, ['object=knife_wuji_real_size_20261002', 'hand=wuji_paper_official_actuator', '+task.env.geometryRound=real-size-student-adaptation-20261002'], train='wujiAcquisitionSAPG', seed=2026100381)
    policy = G2R800Policy(cfg, TEACHER, R800, residual_checkpoint=args.checkpoint,thumb_action_gain=plan['args']['thumb_action_gain'],support_action_gain=plan['args']['support_action_gain'])
    kin = G2Kinematics()
    hand = physics['hand_indices']
    takeover = round(plan['args'].get('takeover_seconds', 16)*30)
    previous = np.zeros(20, np.float32)
    rows = []
    for i in range(len(trace['time'])):
        q = trace['observed_q'][i]
        policy.record(q, previous)
        if i < takeover:
            continue
        if i == takeover:
            policy.takeover_estimate(q, trace['target'][i-1, hand], np.array(calibration['object_in_wrist']), np.array(calibration['slider_in_wrist']))
        goal = .04 if i >= 480 and ((i-480)//150)%2 == 0 else 0.
        gravity = kin.forward(trace['arm_q'][i-1])[:3,:3].T @ np.array([0., 0., -1.])
        before = policy.known.issued.clone()
        target, action = policy.command(q, goal, wrist_gravity=gravity)
        rows.append(dict(time=float(trace['time'][i]), observed_q=q.copy(), arm_q=trace['arm_q'][i-1].copy(), goal=goal, target=target.copy(), action=action.copy(), encoder=policy.last_encoder_input.copy(), target_error=float(abs(target-trace['target'][i, hand]).max()), action_error=float(abs(action-trace['action'][i]).max()), raw_base_error=float(abs(policy.last_raw_action-trace['raw_base_action'][i]).max())))
        actual = trace['action'][i].copy()
        policy.known.issued[:] = before
        policy.known.step(policy.tensor(actual))
        policy.last_action = actual
        previous = actual
    report = dict(trace_sha256=hashlib.sha256((args.demo/'trace.npz').read_bytes()).hexdigest(), checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(), samples=len(rows), maximum_motor_target_error_rad=max(r['target_error'] for r in rows), maximum_action_error=max(r['action_error'] for r in rows), maximum_raw_base_error=max(r['raw_base_error'] for r in rows), motor_parity_passed=max(r['target_error'] for r in rows)<2e-6, mapping=dict(hand_names=policy.fk.names, arm_names=kin.names, hand_simulator_indices=hand, original_hand_lower_rad=policy.fk.lower.tolist(), original_hand_upper_rad=policy.fk.upper.tolist(), policy_hz=30, motor_PD_simulator_hz=240, encoder_shape=[1,2076], encoder_parts='50*(20 normalized measured q +20 previous issued actions)+55 once-calibrated initial features+20 known targets+1 scheduled goal', frame='Measured G2 wrist FK; relative object/slider calibration loaded once before episode', action='16 support controls offset .04rad from initial issued targets;4 thumb controls increment .025rad/30Hz step; original limits and actual issued-target memory', SDK_index_scope='URDF names and simulator indices only; hardware SDK indices/directions/units require an explicit adapter and hardware calibration'), scope='Offline file-only deployment-policy inference on retained measured inputs and actual issued history; no new physical episode, independent validation or hardware success claim')
    np.savez_compressed(args.output/'commands.npz', **{key:np.stack([r[key] for r in rows]) for key in ['time','observed_q','arm_q','goal','target','action','encoder']})
    (args.output/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    assert report['motor_parity_passed'], 'Offline inferred commands differ from recorded deployment interface'


if __name__ == '__main__':
    main()
