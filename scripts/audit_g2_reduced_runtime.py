"""Replay an actual input-ablation evaluation; prove motor parity and no leaks."""
from scripts.g2_local_runtime import LocalPolicyRuntime
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=json.loads((a.run/'report.json').read_text());mode=report['args']['input_ablation'];assert mode
    t=np.load(a.run/'episode-000.npz');errors=[];obs_errors=[];leaks=[]
    for replica in range(t['q'].shape[1]):
        def state(j):
            return [t['all_dof_position'][j,replica].copy(),t['dof_velocity'][j,replica].copy(),
                t['wrist'][j,replica].copy(),t['object_rigid_state'][j,replica].copy(),t['slider_rigid_state'][j,replica].copy()]
        s=state(0);targets=t['reference_targets'][0,replica]
        normal=LocalPolicyRuntime(report['args']['checkpoint'],s[0],s[1],targets,*s[2:],input_ablation=mode)
        poisoned=LocalPolicyRuntime(report['args']['checkpoint'],s[0],s[1],targets,*s[2:],input_ablation=mode)
        for j in range(600):
            s=state(j);nominal=t['reference_targets'][j,replica,7:27]
            command=normal.step(*s,nominal)
            fake=[v.copy() for v in s]
            fake[2][:3]+=3.;fake[3][:3]-=2.;fake[3][7:13]+=10.;fake[4][:3]+=5.
            # Current wrist truth is also unavailable to the FK controller.
            fake[2][3:7]*=-1;fake[3][3:7]*=-1
            if mode=='fixed-body-proprio-slider':fake[0][27]+=.4;fake[1][27]+=20.
            contaminated=poisoned.step(*fake,nominal)
            errors.append(float(np.max(np.abs(command-t['reference_targets'][j+1,replica,7:27]))))
            obs_errors.append(float(np.max(np.abs(normal.last_observation.numpy()-t['input_observation'][j+1,replica:replica+1]))))
            leaks.append(float(np.max(np.abs(command-contaminated))))
    result=dict(scope='offline replay of actual reduced-input physical trials; no simulation or reset',mode=mode,
        frames_per_replica=600,replicas=t['q'].shape[1],maximum_motor_parity_error_rad=max(errors),
        maximum_observation_parity_error=max(obs_errors),maximum_forbidden_input_effect_rad=max(leaks),
        forbidden_inputs='current wrist/object/slider rigid state; slider q/qd additionally when proprio mode',
        initialization='same one-time ideal initial object/slider state in both runtimes')
    assert max(errors)<2e-6 and max(obs_errors)<2e-5 and max(leaks)==0.
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
