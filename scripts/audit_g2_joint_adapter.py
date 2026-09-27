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
    p.add_argument('--thumb-plan',type=Path)
    p.add_argument('--static-support',action='store_true')
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
        torch.save(dict(model=model.state_dict(), task='S', route='joint', obs_dim=124, action_dim=20,
            thumb_plan=json.loads(args.thumb_plan.read_text()) if args.thumb_plan else None,
            static_support=args.static_support), artifact)
        a = state(0)
        rt = LocalPolicyRuntime(artifact, a[0], a[1], data['reference_targets'][0,0], *a[2:])
        errors = []
        for i in range(len(data['q'])-1):
            nominal = rt.targets[0,7:27].numpy().copy()
            if 'teacher_action' in data:
                nominal[16:] += .025*data['teacher_action'][i+1,0,16:]
            nominal = np.clip(nominal, rt.lower[7:27], rt.upper[7:27])
            target = rt.step(*state(i), nominal)
            errors.append(float(np.max(np.abs(target-data['reference_targets'][i+1,0,7:27]))))
        result = dict(scope='offline replay only, no physical trial', frames=len(errors),
            maximum_hand_target_error_rad=max(errors), first_frame_error_rad=errors[0],
            added_thumb_output_max=float(model.actor[-1].weight[16:].abs().max()),
            checkpoint=str(args.checkpoint), trace=str(args.trace),
            thumb_plan=str(args.thumb_plan),static_support=args.static_support)
        assert max(errors) < 2e-5, result
        if args.thumb_plan:
            class ConstantCorrection:
                def mean_action(self,obs):
                    action=torch.zeros(1,20);action[:,16:]=.25
                    return action
            rt=LocalPolicyRuntime(artifact,a[0],a[1],data['reference_targets'][0,0],*a[2:])
            rt.model=ConstantCorrection()
            commands=[]
            for i in range(150):
                commands.append(rt.step(*state(0),data['reference_targets'][0,0,7:27]))
            plan=json.loads(args.thumb_plan.read_text())
            expected=data['reference_targets'][0,0,23:27]+np.array(plan['rows'][-1]['q_thumb'])-np.array(plan['rows'][0]['q_thumb'])+.05
            expected=np.clip(expected,rt.lower[23:27].numpy(),rt.upper[23:27].numpy())
            err=float(np.max(np.abs(commands[-1][16:]-expected)))
            max_step=float(np.max(np.abs(np.diff(np.array(commands)[:,16:],axis=0))))
            assert err<2e-6 and max_step<=.025001,(err,max_step)
            result.update(constant_offset_plateau_error_rad=err,maximum_thumb_step_rad=max_step,
                offset_test='constant .05rad residual stays at planned+.05, no integration drift')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
