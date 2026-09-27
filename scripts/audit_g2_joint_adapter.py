"""Replay actual S measurements through expanded zero-thumb-residual runtime.

No physics simulation, state reset, optimization, or successful-demo claim.
Checks support-network preservation and command continuity over all600frames.
"""
import argparse
import json
from pathlib import Path
import tempfile

from scripts.g2_local_runtime import LocalPolicyRuntime
from scripts.train_g2_local import ActorCritic, expand_support_checkpoint
import numpy as np
import torch


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--trace', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    saved = torch.load(args.checkpoint, map_location='cpu')
    model = ActorCritic(124, 20)
    expand_support_checkpoint(model, saved)
    data = np.load(args.trace)
    assert data['q'].shape[1] == 1
    def state(i):
        return [data[k][i, 0] for k in ['all_dof_position', 'dof_velocity', 'wrist', 'object_rigid_state', 'slider_rigid_state']]
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)/'expanded.pth'
        torch.save(dict(model=model.state_dict(), task='S', route='joint', obs_dim=124, action_dim=20), artifact)
        a = state(0)
        rt = LocalPolicyRuntime(artifact, a[0], a[1], data['reference_targets'][0,0], *a[2:])
        errors = []
        for i in range(len(data['q'])-1):
            nominal = rt.targets[0,7:27].numpy().copy()
            nominal[16:] += .025*data['teacher_action'][i+1,0,16:]
            nominal = np.clip(nominal, rt.lower[7:27], rt.upper[7:27])
            target = rt.step(*state(i), nominal)
            errors.append(float(np.max(np.abs(target-data['reference_targets'][i+1,0,7:27]))))
        result = dict(scope='offline replay only, no physical trial', frames=len(errors),
            maximum_hand_target_error_rad=max(errors), first_frame_error_rad=errors[0],
            added_thumb_output_max=float(model.actor[-1].weight[16:].abs().max()),
            checkpoint=str(args.checkpoint), trace=str(args.trace))
        assert max(errors) < 2e-5, result
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
