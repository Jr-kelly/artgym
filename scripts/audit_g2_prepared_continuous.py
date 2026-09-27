"""Independent full H→S continuous audit; no physics execution or state writes."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

from scripts.g2_local_runtime import LocalPolicyRuntime
import numpy as np
from scipy.spatial.transform import Rotation


def pose_error(poses,reference):
    distance=np.linalg.norm(poses[:,:3]-reference[:3],axis=-1)
    rotation=(Rotation.from_quat(reference[3:7]).inv()*Rotation.from_quat(poses[:,3:7])).magnitude()
    return distance,rotation


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--launch',type=Path,required=True)
    p.add_argument('--prefix-trace',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-hand-gravity',action='store_true',help='Audit separately labeled gravity-ON continuous condition; require exactly hand-body gravity flags changed, other effective physics equal. Prefix need not match physically.')
    p.add_argument('--prefix-until-phase',help='Declared control intervention: compare exact actual source prefix before this phase in both traces; later acquisition may differ. Task criteria remain unchanged.')
    a=p.parse_args();t=np.load(a.run/'trace.npz');prefix=np.load(a.prefix_trace)
    launch=json.loads(a.launch.read_text());pin=Path(launch['cwd'])
    takeover=json.loads((a.run/'takeover.json').read_text());reported=json.loads((a.run/'report.json').read_text())
    indices=np.flatnonzero(t['phase']=='operate');start=int(indices[0]);complete=len(indices)==600 and np.all(np.diff(indices)==1)
    ref=np.asarray(takeover['object_world']);obj=t['object'][indices];dp,dr=pose_error(obj,ref)
    physics=json.loads((a.run/'physics.json').read_text());lower=physics['knife_dof_properties']['lower'][0]
    prefix_physics=json.loads((a.prefix_trace.parent/'physics.json').read_text())
    physics_equal=physics==prefix_physics
    physics_differences=[key for key in set(physics)|set(prefix_physics) if physics.get(key)!=prefix_physics.get(key)]
    if a.allow_hand_gravity:
        assert physics_differences==['robot_gravity_flags'], physics_differences
        for name,old,new in zip(physics['robot_body_names'],prefix_physics['robot_gravity_flags'],physics['robot_gravity_flags']):
            assert (old==1 and new==0) if name.startswith('hand_r_') else old==new
    else:
        assert physics_equal, 'Actual physics properties differ from the frozen preparation source'
    errors=[];goal_errors=[]
    for phase in range(4):
        last=indices[phase*150+141:(phase+1)*150];goal=lower+(.04 if phase%2==0 else 0.)
        errors.append(float(np.max(np.abs(t['slider'][last]-goal))) if len(last)==9 else None)
        group=indices[phase*150:(phase+1)*150]
        goal_errors.append(float(np.max(np.abs(t['goal'][group]-goal))) if len(group) else None)
    no_drop=bool(np.all(obj[:,2]>=takeover['table_height']+.05) and not np.any(t['knife_table_contacts'][indices]))
    op_success=bool(complete and all(e is not None and e<.01 for e in errors) and dp.max()<.01 and dr.max()<.25 and no_drop)
    hold_phase='fixed_motor_hold' if reported['args'].get('fixed_preparation_hold') else 'learned_hold'
    held=np.flatnonzero(t['phase']==hold_phase);h0=held[0]-1;hd,hr=pose_error(t['object'][held],t['object'][h0]);hs=float(np.max(np.abs(t['slider'][held]-t['slider'][h0])))
    hold_success=bool(len(held)==660 and hd.max()<.01 and hr.max()<.25 and hs<.01 and not np.any(t['knife_table_contacts'][held]) and np.all(t['object'][held,2]>=takeover['table_height']+.05))
    fields=['all_dof_position','dof_velocity','object_rigid_state','slider_rigid_state','reference_targets','targets','arm_integral_state','q','wrist','action']
    compare_frames=start
    if a.prefix_until_phase:
        assert not a.allow_hand_gravity, 'Use a matched-physics intervention source'
        compare_frames=int(np.flatnonzero(t['phase']==a.prefix_until_phase)[0])
        assert compare_frames==int(np.flatnonzero(prefix['phase']==a.prefix_until_phase)[0]) and compare_frames>0
    prefix_same_length=len(prefix['time'])==start if not a.prefix_until_phase else len(prefix['time'])>=compare_frames
    if not a.allow_hand_gravity:assert prefix_same_length
    prefix_errors={k:float(np.max(np.abs(t[k][:compare_frames]-prefix[k][:compare_frames]))) for k in fields} if prefix_same_length else {}
    if a.prefix_until_phase:assert max(prefix_errors.values())<1e-7, 'The preceding physical prefix must be identical'
    source=ast.parse((pin/'scripts/run_g2_tabletop.py').read_text())
    tick=next(n for n in ast.walk(source) if isinstance(n,ast.FunctionDef) and n.name=='tick')
    setters=[];forbidden=[]
    for node in ast.walk(source):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute):continue
        name=node.func.attr
        if name in ['set_actor_dof_states','set_actor_root_state_tensor_indexed','set_dof_state_tensor','set_dof_state_tensor_indexed']:
            setters.append(dict(name=name,line=node.lineno))
        if name.startswith('apply_') and 'force' in name or 'attractor' in name:
            forbidden.append(dict(name=name,line=node.lineno))
    assert len(setters)==3 and all(v['line']<tick.lineno for v in setters) and not forbidden

    # Reconstruct the native PhysX wrist quaternion sign from the NEXT recorded
    # observation's relative quaternion. At frame0 legacy compatibility uses
    # the matrix-derived sign; the opt-in runtime applies that same convention.
    from scripts.g2_local_env import local_pose
    import torch
    def state(j,obs):
        w=t['wrist'][j].copy();o=t['object_rigid_state'][j]
        rel=local_pose(torch.tensor(w[None],dtype=torch.float32),torch.tensor(o[None],dtype=torch.float32))[0,3:7].numpy()
        if np.dot(rel,obs[69:73])<0:w[3:7]*=-1
        return [t['all_dof_position'][j],t['dof_velocity'][j],w,o,t['slider_rigid_state'][j]]
    initial=state(start-1,t['learned_observation'][start]);targets=t['reference_targets'][start-1]
    rt=LocalPolicyRuntime(a.checkpoint,initial[0],initial[1],targets,*initial[2:],reset_quaternion_compat=True,
        freeze_initial_action=reported['args'].get('operation_static_policy',False))
    command_errors=[];action_errors=[];observation_errors=[]
    for idx in indices:
        command=rt.step(*state(idx-1,t['learned_observation'][idx]),rt.targets[0,7:27].numpy())
        command_errors.append(float(np.max(np.abs(command-t['reference_targets'][idx,7:27]))))
        action_errors.append(float(np.max(np.abs(rt.last_action[0].numpy()-t['learned_action'][idx]))))
        observation_errors.append(float(np.max(np.abs(rt.last_observation[0].numpy()-t['learned_observation'][idx]))))
    parity=max(command_errors)<2e-6 and max(action_errors)<2e-6 and max(observation_errors)<2e-5
    first=np.flatnonzero((dp>=.01)|(dr>=.25))
    result=dict(scope='independent scoring of an actual uncut continuous table→H→S run; offline audit only',
        run=str(a.run),operation_complete=bool(complete),operation_success=op_success,hold_success=hold_success,
        grasp_success=reported['grasp_success'],independent_whole_success=bool(reported['grasp_success'] and hold_success and op_success),
        strict_2mm=all(e is not None and e<.002 for e in errors),endpoint_max_errors_m=errors,
        world_drift_m=float(dp.max()),world_rotation_rad=float(dr.max()),no_drop_or_table_support=no_drop,
        first_instability_s=float((first[0]+1)/30) if len(first) else None,
        hold_drift_m=float(hd.max()),hold_rotation_rad=float(hr.max()),hold_slider_error_m=hs,
        physical_goals_max_error_m=max(goal_errors),operation_start_frame=start,prefix_frames=compare_frames,prefix_errors=prefix_errors,
        prefix_verified=bool(prefix_same_length and max(prefix_errors.values())<1e-7),
        prefix_comparison_scope='Exact physical prefix before declared intervention '+a.prefix_until_phase if a.prefix_until_phase else 'Diagnostic only: different hand gravity changes real acquisition dynamics' if a.allow_hand_gravity else 'Exact original frozen preparation prefix',
        input_command_parity_verified=bool(parity),maximum_motor_command_error_rad=max(command_errors),
        maximum_action_error=max(action_errors),maximum_observation_error=max(observation_errors),
        state_reset_after_start=False,state_setter_source_locations=setters,
        static_state_write_audit='All3 initial state setters precede tick definition; actual pin reviewed. Runtime has no simulator handle; measured source prefix compared.',
        checkpoint_sha256=hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
        hold_method=hold_phase,
        hold_checkpoint_sha256=hashlib.sha256(Path(reported['args']['learned_hold_policy']).read_bytes()).hexdigest() if reported['args'].get('learned_hold_policy') else None,
        effective_physics_equal_to_successful_prefix=physics_equal,
        allowed_physics_differences=physics_differences,
        actual_history_frames=takeover['history_frames'],learner_memory='feedforward; actual acquisition history retained, never injected from cache',
        original_teacher_executed=reported['original_actor_executed_in_operation'])
    assert result['independent_whole_success']==reported['required_task_success']
    assert max(goal_errors)<1e-8 and parity
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['prefix_errors','state_setter_source_locations']}))


if __name__=='__main__':main()
