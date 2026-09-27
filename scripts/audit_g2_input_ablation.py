"""Offline input provenance and FK audit against a real continuous success."""
from scripts.g2_input_ablation import InputAblation
import json
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation


def main():
    root=Path('runs/g2-local-policy-20260928')
    t=np.load(root/'R7-03-continuous-learned-H-then-joint-S/trace.npz')
    ids=np.flatnonzero(t['phase']=='operate');start=ids[0]-1
    f=lambda x:torch.as_tensor(np.array(x),dtype=torch.float32)
    initial=f(t['object_rigid_state'][start:start+1]);slider=f(t['slider'][start:start+1]);q=f(t['all_dof_position'][start:start+1,:27])
    observer=InputAblation('fixed-body-proprio-slider',initial,slider,q)
    props=json.loads(Path('configs/g2_local/physics.json').read_text())
    lower=f(props['robot_dof_properties']['lower']);upper=f(props['robot_dof_properties']['upper'])
    slider_lower=props['knife_dof_properties']['lower'][0]
    errors=[];fkerrors=[];signs=[];robot_channel_errors=[];obs=[]
    for age,idx in enumerate(ids):
        old=idx-1;q=f(t['all_dof_position'][old:old+1,:27]);qd=f(t['dof_velocity'][old:old+1,:27])
        residual=f(t['learned_residual'][old:old+1]) if age else torch.zeros(1,20)
        action=f(t['learned_action'][old:old+1]) if age else torch.zeros(1,20)
        out=observer.observation(q,qd,f(t['reference_targets'][old:old+1]),torch.tensor([age]),residual,action,
            f(t['goal'][idx:idx+1]),lower,upper,slider_lower)
        errors.append(float(observer.estimated_slider[0]-t['slider'][old]))
        wrist=observer.arm.forward(q[0,:7].numpy())
        fkerrors.append(float(np.linalg.norm(wrist[:3,3]-t['wrist'][old,:3])))
        raw=t['learned_observation'][idx]
        # Robot normalization, command error, clock and recurrent action state
        # are unchanged. Body/slider blocks intentionally differ.
        robot_channel_errors.append(float(np.max(np.abs(np.r_[out[0,:60].numpy()-raw[:60],out[0,83:].numpy()-raw[83:]]))))
        # Compare against frozen-body quaternion expressed with the actual
        # wrist sign encoded in the policy observation. No online truth usage.
        body_change=Rotation.from_quat(t['object'][old,3:]).inv()*Rotation.from_quat(initial[0,3:7].numpy())
        expected=(Rotation.from_quat(raw[69:73])*body_change).as_quat()
        expected*=1 if np.dot(expected,raw[69:73])>=0 else -1
        signs.append(float(np.dot(out[0,69:73].numpy(),expected)))
        obs.append(out.numpy())
    assert max(robot_channel_errors)<2e-5
    assert max(fkerrors)<2e-6
    assert min(signs)>.9999, 'FK quaternion sign convention incompatible with trained observations'
    result=dict(scope='offline actual-success replay; not physical input-ablation success',frames=len(ids),
        max_slider_estimation_error_m=float(np.max(np.abs(errors))),rms_slider_estimation_error_m=float(np.sqrt(np.mean(np.square(errors)))),
        max_wrist_fk_position_error_m=max(fkerrors),min_quaternion_alignment=min(signs),
        max_unchanged_robot_input_error=max(robot_channel_errors),
        live_object_inputs='none in observation signature',input_contract=observer.description())
    (root/'R8-input-offline-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
