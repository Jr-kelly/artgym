"""Replay retained push control on recorded legal inputs, without physics replay.

This checks the complete reference/actor/pressure/control-memory call path and
exports one actual successful entrance. Recorded controller state is used only
for this replay; it must never initialize a different live episode.
"""
import argparse, hashlib, json
from pathlib import Path
import isaacgym
import numpy as np
import torch
from scripts.wuji_goal_common import configuration
from scripts.g2_r800_policy import G2R800Policy
from scripts.g2_kinematics import G2Kinematics, transform
from scripts.wuji_joint_deflection_pressure import NativeJointDeflectionPressure
from scripts.record_wuji_flat_table_event import record


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--trial', type=Path, default=Path('runs/contact-transfer-20261006/regression/nominal-125-video-v1'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    command = json.loads((a.trial/'command.json').read_text())
    arg = lambda flag: Path(command[command.index(flag)+1])
    trace_path = a.trial/'simulation/trace.npz'
    record('retained_push_call_path_replay_started', [str(trace_path), str(a.output)],
           {'uncertainty':'Can the retained actor/reference/pressure/history reproduce issued targets from recorded legal inputs?',
            'physics_repeated':False}, next_step='Match complete push call path then use its actual entrance for pickup-to-regrasp development')
    z = np.load(trace_path)
    cfg = configuration('wuji_geometry',1,['object=knife_wuji_real_size_20261002','hand=wuji_paper_official_actuator',
                        '+task.env.geometryRound=real-size-student-adaptation-20261002'],train='wujiAcquisitionSAPG',seed=2026100301)
    estimate = json.loads(arg('--grasp-plan').read_text()).get('initial_geometry_estimate')
    geometry = estimate['handle_size_WTL_m']+estimate.get('slider_size_WTL_m',[.01,.003,.03]) if estimate else None
    policy = G2R800Policy(cfg,'runs/artmanip-recovery-20260930/aggregation1-pair6400/aggregate/E/epoch_006100.pth',
                         'runs/real-size-student-adaptation-20261002/train/R800/step_055200.pth',geometry=geometry,
                         residual_checkpoint=arg('--residual-checkpoint'),thumb_reference_override=arg('--thumb-reference-override'))
    transfer=json.loads(arg('--postlift-regrasp').read_text())
    prior=np.asarray(transfer['object_in_wrist']);slider_prior=np.asarray(transfer['slider_in_wrist'])
    if estimate:
        center=np.asarray(estimate.get('initial_object_center_shift_knife_m',[0,0,0]))
        prior[:3,3]+=prior[:3,:3]@center
        delta=center+np.asarray(estimate['slider_contact_shift_m'])+np.array([0,(estimate['handle_size_WTL_m'][1]-.012)/2,0])
        if estimate.get('newknife_contact_geometry'):delta[1]-=(estimate['slider_size_WTL_m'][1]-.003)/2
        slider_prior[:3,3]+=prior[:3,:3]@delta
    pressure_spec=json.loads(arg('--proprioceptive-pressure-config').read_text())
    policy.pressure_adapter=NativeJointDeflectionPressure(pressure_spec,prior[:3,1],np.asarray(cfg.hand.dof_props.stiffness))
    kin=G2Kinematics(); start=int(np.searchsorted(z['time'],16.,side='right'))
    # The saved input at frame i precedes the physical step ending at time[i].
    for i in range(start):policy.record(z['observed_q'][i], np.zeros(20))
    policy.pressure_adapter.model.offset[0]=torch.as_tensor(z['proprioceptive_thumb_offset_rad'][start-1])
    policy.takeover_estimate(z['observed_q'][start],z['target'][start-1,7:27],prior,slider_prior,clock_s=16.)
    errors=[]; actions=[];inputs=[]
    for i in range(start,len(z['time'])):
        t=float(z['time'][i]-1/30)
        policy.record(z['observed_q'][i],policy.last_action)
        wrist=kin.forward(z['arm_q'][i-1])
        policy.pressure_adapter.normal=wrist[:3,:3].T@np.asarray(transfer['expected_knife_world'])[:3,1]
        target,action=policy.command(z['observed_q'][i],.035,wrist_gravity=wrist[:3,:3].T@np.array([0.,0.,-1.]),
                                     clock_s=t,issued_target_hold=t-16>=policy.thumb_reference.duration+1/30-1e-7)
        errors.append(float(np.max(abs(target-z['target'][i,7:27]))))
        actions.append(float(np.max(abs(action-z['action'][i]))))
        inputs.append(policy.last_public_features.copy())
    i=start-1;O=transform(z['object'][i,:3],z['object'][i,3:7]);W=transform(z['wrist'][i,:3],z['wrist'][i,3:7])
    entrance={'source':str(trace_path),'source_sha256':hashlib.sha256(trace_path.read_bytes()).hexdigest(),
              'frame':i,'time_s':float(z['time'][i]),'object_in_wrist_actual':(np.linalg.inv(W)@O).tolist(),
              'object_in_wrist_prior':prior.tolist(),'hand_q':z['q'][i].tolist(),'issued_hand_target':z['target'][i,7:27].tolist(),
              'finger_body_contacts':z['finger_body_contacts'][i].tolist(),'finger_slider_contacts':z['finger_slider_contacts'][i].tolist(),
              'slider_q_m':float(z['slider'][i]),'active_push_m':float(z['slider'][599]-z['slider'][i]),
              'scope':'One proven simulated entrance; geometric guidance only, live handover must use current physical state and legal history'}
    (a.output/'actual-entrance.json').write_text(json.dumps(entrance,indent=2))
    result={'frames':len(errors),'max_target_error_rad':max(errors),'max_action_error':max(actions),
            'first_target_errors_rad':errors[:6],'call_path_matched':max(errors)<2e-5,
            'actor_sha256':hashlib.sha256(arg('--residual-checkpoint').read_bytes()).hexdigest(),
            'scope':'Controller replay with recorded measured inputs and persisted pressure offset; no physical run or new task success'}
    (a.output/'result.json').write_text(json.dumps(result,indent=2))
    np.savez_compressed(a.output/'call-inputs.npz',public_features=inputs,target_error=errors,action_error=actions)
    record('retained_push_call_path_replay_terminal',[str(a.output/'result.json'),str(a.output/'actual-entrance.json')],result,
           next_step='Matched: implement live retained-skill adapter; mismatch: correct interface/phase/history before any skill-capability experiment')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
