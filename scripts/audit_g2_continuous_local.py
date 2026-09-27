"""Read-only continuous/local handoff audit; no physical simulation or reset."""
import argparse
import json
from pathlib import Path

from scripts.g2_local_runtime import LocalPolicyRuntime
from scripts.g2_local_env import local_pose
from scripts.run_g2_tabletop import score
import numpy as np
import torch
from scipy.spatial.transform import Rotation


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--evaluation', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = np.load(root/'configs/g2_local/S-actual-state.npz')
    origin = json.loads((root/'configs/g2_local/provenance.json').read_text())
    old = np.load(origin['source_trace'])
    trace = np.load(args.run/'trace.npz')
    ev = np.load(args.evaluation)
    takeover = json.loads((args.run/'takeover.json').read_text())
    indices = np.flatnonzero(trace['phase'] == 'operate')
    start = int(indices[0])
    prefix = {}
    for key in ['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state',
                'reference_targets','targets','arm_integral_state','wrist','q','action']:
        prefix[key] = float(np.max(np.abs(trace[key][:start]-old[key][:start])))
    initial = {key: float(np.max(np.abs(trace[key][start-1]-source[key])))
               for key in source.files if key in trace and trace[key][start-1].shape == source[key].shape}
    initial['history_q'] = float(np.max(np.abs(trace['q'][start-50:start]-source['history_q'])))
    initial['history_action'] = float(np.max(np.abs(trace['action'][start-50:start]-source['history_action'])))

    def measured(j, logged_obs):
        # Trace pose(wrist) was matrix-derived, while learned_observation kept
        # PhysX's native quaternion sign. Reconstruct the sign from that actual
        # logged relative quaternion; no estimated physical pose is substituted.
        wrist = trace['wrist'][j].copy()
        obj = trace['object_rigid_state'][j]
        qrel = local_pose(torch.tensor(wrist[None],dtype=torch.float32),
                          torch.tensor(obj[None],dtype=torch.float32))[0,3:7].numpy()
        if np.dot(qrel, logged_obs[69:73]) < 0:
            wrist[3:7] *= -1
        return [trace['all_dof_position'][j], trace['dof_velocity'][j], wrist,
                obj, trace['slider_rigid_state'][j]]

    state = measured(start-1, trace['learned_observation'][start])
    targets = trace['reference_targets'][start-1]
    comparisons = {}
    for compatibility in [False, True]:
        rt = LocalPolicyRuntime(args.checkpoint, state[0], state[1], targets, *state[2:],
                                reset_quaternion_compat=compatibility)
        command = rt.step(*state, targets[7:27])
        comparisons[str(compatibility)] = dict(
            observation=rt.last_observation[0].numpy().tolist(),
            first_action=rt.last_action[0].numpy().tolist(),
            max_action_difference_from_local=float(np.max(np.abs(rt.last_action[0].numpy()-ev['action'][0,0]))),
            max_command_difference_from_local_rad=float(np.max(np.abs(command-ev['reference_targets'][0,0,7:27]))),
            targets_before_step=targets.tolist(),
        )
    a = np.array(comparisons['False']['observation'])
    b = np.array(comparisons['True']['observation'])
    changed = np.flatnonzero(np.abs(a-b)>1e-6).tolist()
    assert changed == [69,70,71,72], changed
    assert comparisons['True']['max_action_difference_from_local'] < 2e-6
    assert comparisons['True']['max_command_difference_from_local_rad'] < 2e-6

    scored = score(trace,takeover,'B')
    obj = trace['object'][indices]
    ref = np.array(takeover['object_world'])
    drift = np.linalg.norm(obj[:,:3]-ref[:3],axis=1)
    rotation = (Rotation.from_quat(ref[3:]).inv()*Rotation.from_quat(obj[:,3:])).magnitude()
    bad = np.flatnonzero((drift>=.01)|(rotation>=.25))
    contacts = trace['finger_knife_contacts'][indices]
    slider_contacts = trace['finger_slider_contacts'][indices,0]
    loss = np.flatnonzero(slider_contacts==0)
    scored.update(first_instability_s=float((bad[0]+1)/30) if len(bad) else None,
                  first_thumb_slider_contact_loss_s=float((loss[0]+1)/30) if len(loss) else None,
                  finger_contact_fraction=np.mean(contacts>0,axis=0).tolist(),
                  thumb_slider_contact_fraction=float(np.mean(slider_contacts>0)))
    result = dict(scope='offline state/input audit; physical state untouched', run=str(args.run),
                  checkpoint=str(args.checkpoint), operation_frames=len(indices), prefix_frames=start,
                  prefix_max_errors=prefix, takeover_max_errors=initial,
                  quaternion_observation_indices_changed=changed,
                  first_observation_comparisons=comparisons, strict_rescore=scored,
                  interpretation='Identical acquired physical state; first reset observation uses the other equivalent wrist quaternion sign. Compatibility matches the frozen local first action; causal contribution requires its own continuous trial.')
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(prefix_max=max(prefix.values()),initial_max=max(initial.values()),
        first_action_error_before=comparisons['False']['max_action_difference_from_local'],
        first_action_error_after=comparisons['True']['max_action_difference_from_local'],
        first_instability_s=scored['first_instability_s'],success=scored['required_task_success'])))


if __name__ == '__main__':
    main()
