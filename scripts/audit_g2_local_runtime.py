"""Replay an actual trained local policy through the continuous motor adapter.

No simulation, optimization, or cached acquisition handoff. All600observations
come from the real saved local physics trajectory; compared commands are not
used to produce a new success claim.
"""
import argparse
import json
from pathlib import Path
from scripts.g2_local_runtime import LocalPolicyRuntime
import numpy as np


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--env',type=int,default=0)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();d=np.load(a.trace);s=np.load(a.source)
    keys=['all_dof_position','dof_velocity','wrist','object_rigid_state','slider_rigid_state']
    initial=[s[k] for k in keys]
    rt=LocalPolicyRuntime(a.checkpoint,initial[0],initial[1],s['reference_targets'],*initial[2:])
    errors=[];action_errors=[];residual_errors=[]
    start=1 if d['time'][0,a.env]==0 else 0
    state=initial
    for i in range(start,len(d['time'])):
        nominal=rt.targets[0,7:27].numpy().copy()
        if rt.thumb_plan is None and 'teacher_action' in d:
            nominal[16:]+=.025*d['teacher_action'][i,a.env,16:]
            nominal=np.clip(nominal,rt.lower[7:27].numpy(),rt.upper[7:27].numpy())
        target=rt.step(*state,nominal)
        errors.append(float(np.max(np.abs(target-d['reference_targets'][i,a.env,7:27]))))
        action_errors.append(float(np.max(np.abs(rt.last_action[0].numpy()-d['action'][i,a.env]))))
        residual_errors.append(float(np.max(np.abs(rt.residual[0].numpy()-d['residual'][i,a.env]))))
        state=[d[k][i,a.env] for k in keys]
    result=dict(scope='offline runtime audit, no new physical trial',checkpoint=str(a.checkpoint),trace=str(a.trace),
        env=a.env,frames=len(errors),maximum_hand_target_error_rad=max(errors),
        first_target_error_rad=errors[0],maximum_action_error=max(action_errors),maximum_residual_error_rad=max(residual_errors))
    assert max(errors)<2e-5 and max(action_errors)<2e-4,result
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
