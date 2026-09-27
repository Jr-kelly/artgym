"""Validate one-inference S against actual local trials; poison later sensors."""
from scripts.g2_local_runtime import LocalPolicyRuntime
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=json.loads((a.run/'report.json').read_text());assert report['args']['baseline']=='learned-static'
    t=np.load(a.run/'episode-000.npz');errors=[];actions=[];leaks=[];calls=[]
    for env in range(t['q'].shape[1]):
        def state(i):return [t[k][i,env].copy() for k in ['all_dof_position','dof_velocity','wrist','object_rigid_state','slider_rigid_state']]
        s=state(0);targets=t['reference_targets'][0,env]
        runtimes=[LocalPolicyRuntime(report['args']['checkpoint'],s[0],s[1],targets,*s[2:],freeze_initial_action=True) for _ in range(2)]
        for step in range(600):
            current=state(step);fake=[v.copy() for v in current]
            if step>0:
                for v in fake:v[:]=np.nan
            nominal=t['reference_targets'][step,env,7:27]
            first=runtimes[0].step(*current,nominal);second=runtimes[1].step(*fake,nominal)
            errors.append(float(np.max(np.abs(first-t['reference_targets'][step+1,env,7:27]))))
            actions.append(float(np.max(np.abs(runtimes[0].last_action[0].numpy()-t['action'][step+1,env]))))
            leaks.append(float(np.max(np.abs(first-second))))
        calls.append([v.model_calls for v in runtimes])
    result=dict(scope='Offline command parity and late-input isolation, not new physical execution',frames=len(errors),
        max_motor_error_rad=max(errors),max_action_error=max(actions),max_poisoned_input_effect_rad=max(leaks),
        model_calls_per_replica_and_runtime=calls,
        poisoned_after_first_frame='all robot q/qd, wrist pose, object pose/velocity, slider pose/q/qd set NaN; no effect on motor targets',
        initial_state='one actual ideal initialization; source prepared H, still privileged',
        limitation='S only; real actuator servo still needs proprioception; acquisition/H not made deployable')
    assert max(errors)<2e-6 and max(actions)<2e-6 and max(leaks)==0 and all(v==[1,1] for v in calls)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
