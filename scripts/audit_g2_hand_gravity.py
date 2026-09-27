"""Reconstruct recorded motor gravity compensation, offline and independently.

Model torque is never a force-sensor measurement. Supports local resets and
continuous traces; validates actual command slew, limits and physics difference.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scripts.g2_hand_gravity import HandGravity


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    local=(a.run/'episode-000.npz').exists()
    trace=np.load(a.run/('episode-000.npz' if local else 'trace.npz' if (a.run/'trace.npz').exists() else 'partial-trace.npz'))
    physics=json.loads(Path('configs/g2_local/physics.json').read_text()) if local else json.loads((a.run/'physics.json').read_text())
    model=HandGravity(physics['robot_dof_properties']['stiffness'][7:27])
    lo=np.asarray(physics['robot_dof_properties']['lower'][7:27],np.float32)
    hi=np.asarray(physics['robot_dof_properties']['upper'][7:27],np.float32)
    slew=np.asarray([.02]*16+[.025]*4,np.float32)
    errors=[];torque_errors=[];bias_errors=[];steps=[];biases=[];limits=[]
    replicas=range(trace['time'].shape[1]) if local else [None]
    start=1 if local else 0
    for env in replicas:
        def value(key,i):return trace[key][i,env] if local else trace[key][i]
        initial=value('targets',0)[7:27] if local else value('reference_targets',0)[7:27]
        previous=initial.copy()
        for i in range(start,len(trace['time'])):
            q=value('all_dof_position',i-1)[:27] if local else value('hand_gravity_input_q',i)
            nominal=value('reference_targets',i)[7:27]
            bias,torque=model.bias(q)
            desired=nominal+bias.astype(np.float32)
            command=np.clip(previous+np.clip(desired-previous,-slew,slew),lo,hi)
            actual=value('targets',i)[7:27]
            errors.append(float(np.max(np.abs(command-actual))))
            torque_errors.append(float(np.max(np.abs(torque-value('hand_gravity_model_torque',i)))))
            bias_errors.append(float(np.max(np.abs(actual-nominal-value('hand_gravity_applied_motor_bias',i)))))
            steps.append(np.abs(actual-previous));biases.append(np.abs(actual-nominal))
            limits.append(float(max(0,np.max(lo-actual),np.max(actual-hi))))
            previous=actual.copy()
    steps=np.asarray(steps)
    result=dict(scope='Offline motor gravity chain reconstruction; model torque, not measured force',
        local_reset=local,frames=len(errors),max_command_reconstruction_error_rad=max(errors),
        max_model_torque_reconstruction_error_Nm=max(torque_errors),max_logged_bias_error_rad=max(bias_errors),
        maximum_support_command_step_rad=float(steps[:,:16].max()),maximum_thumb_command_step_rad=float(steps[:,16:].max()),
        maximum_applied_gravity_bias_rad=float(np.max(biases)),joint_limit_excess_rad=max(limits))
    assert max(errors)<2e-7 and max(torque_errors)<1e-7 and max(bias_errors)<2e-7
    assert result['maximum_support_command_step_rad']<.020001 and result['maximum_thumb_command_step_rad']<.025001 and max(limits)==0
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
