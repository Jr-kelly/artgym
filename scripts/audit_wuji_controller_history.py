"""Check whether causal sent commands recover the missing controller state.

No model is fitted. Initial commanded targets are explicitly additional known
controller information, not inferred from the measured initial joint angles.
The current command is reconstructed from past actions, never future actions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.wuji_kinematics import WujiKinematics
from scripts.monitor_wuji_checkpoints import atomic_json,now

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    assert not args.output.exists()
    folder=ROOT/'runs/wuji-goal/diagnostics/state-memory-2225-v1/data'
    manifest=json.loads((folder/'manifest.json').read_text())
    dataset=folder/'memory-features.npz';assert hashlib.sha256(dataset.read_bytes()).hexdigest()==manifest['dataset_sha256']
    with np.load(dataset) as z:features=z['features'];rows=z['initial_rows'];steps=z['label_steps']
    states=np.load(ROOT/'runs/wuji-goal/bridge3-evaluation-states/mixed332.npy')[rows]
    initial_command=states[:,20:40].astype(np.float64);initial_q=states[:,:20].astype(np.float64)
    kin=WujiKinematics();results={}
    for i,source in enumerate(manifest['sources']):
        pair=ROOT/'runs'/source['path'].split('/runs/',1)[1]
        assert hashlib.sha256(pair.read_bytes()).hexdigest()==source['sha256']
        trace=pair.with_name('trace.npz')
        with np.load(trace) as z:action=z['action'][:,rows];target=z['target'][:,rows];q=z['q'][:,rows]
        measured=(features[i,:,:,:20].astype(np.float64)+1)/2*(kin.upper-kin.lower)+kin.lower
        assert np.array_equal(features[i,1:,:,20:40],action[:596])
        assert np.count_nonzero(features[i,0,:,20:40])==0
        q_error=float(np.abs(measured[1:]-q[:596]).max());assert q_error<1e-6
        command=initial_command.copy();commands=[command.copy()]
        for t in range(1,597):
            past=features[i,t,:,20:40].astype(np.float64)
            desired=initial_command+.04*past
            desired[:,16:]=command[:,16:]+.025*past[:,16:]
            command=np.clip(desired,kin.lower,kin.upper)
            commands.append(command.copy())
        commands=np.stack(commands)
        target_error=float(np.abs(commands[1:]-target[:596]).max())
        # Float64 analytical integration differs slightly from repeated float32
        # scale/unscale in PhysX's command adapter; this is a numerical tolerance.
        assert target_error<1e-4,target_error
        causal_target=np.concatenate([initial_command[None],target[:596]],axis=0)
        error=causal_target-measured
        results[source['key']]=dict(past_actions_exact=True,measured_joint_max_error_rad=q_error,
            reconstructed_command_max_error_rad=target_error,checked_causal_frames=int(597*90),
            labels_at_existing_steps=steps.tolist(),target_minus_measured_abs_q50_q90_q99_rad=np.quantile(np.abs(error),[.5,.9,.99]).tolist(),
            trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest())
    result=dict(status='passed',created=now(),scope=__doc__,sources=results,
        initial_command_minus_measured_abs_q50_q90_max_rad=np.quantile(np.abs(initial_command-initial_q),[.5,.9,1]).tolist(),
        additional_information='Known initial commanded targets20, then causal past policy actions. This cannot be silently replaced by measured initial q.',
        no_fit=True,no_physics=True,no_success_claim=True,
        prior_controller_student='Earlier controller-input latent student final54/139 failed; this audit does not establish that these inputs solve state estimation or control.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    atomic_json(args.output,result);print(json.dumps(result))


if __name__=='__main__':main()
