"""Bounded physics stress from the last logged finite Sharpa state.

Restore hand/object positions and velocities, the next logged joint targets,
and logged object mass/friction/damping. Hold those targets for one second.
PhysX contact warm starts and original hand randomization are not serialized;
this is a state reconstruction diagnostic, not exact replay of the crash.
Eight identical local states exercise GPU batching; they are not independent
trials or learned-policy evaluations. No policy or reward is involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.wuji_goal_common import configuration,make_env
from isaacgym import gymtorch
from isaacgymenvs.utils.torch_jit_utils import quat_apply,quat_mul
import numpy as np
import torch
from omegaconf import OmegaConf


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--substeps',type=int,choices=[4,8],required=True)
    parser.add_argument('--damping-factor',type=float,choices=[1.,.1],required=True)
    parser.add_argument('--object-profile',default='knife_sharpa_official')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    assert not (args.output/'report.json').exists()
    root=Path(__file__).resolve().parents[1]
    source=root/'runs/sharpa_paper_reference_substeps8_recover1350_v1/teacher/physics-audit/rank0/nonfinite-physics.pth'
    payload=torch.load(source,map_location='cpu');row=9524
    old=payload['previous_refresh'];current=payload['current'];context=payload['context']
    instance=context['instance_id_list'][int(context['env2instance'][row])]
    mass=context['object_mass'][row].tolist();friction=float(context['object_friction'][row,0])
    damping=float(context['object_dof_damping'][row,0])*args.damping_factor
    cfg=configuration('artmanip_paper_reference',8,
        ['hand=sharpa','object='+args.object_profile,'test=False',"object.asset.instance_id_list=['"+instance+"']",
         'object.randomization.randomize=False','task.task.randomize=False',
         'object.default_props.mass='+str(mass),'object.default_props.friction='+str(friction),
         'object.default_props.dof_damping='+str(damping),'object.default_props.dof_stiffness=0.0',
         'task.sim.substeps='+str(args.substeps)],train='paperReferenceSAPG',seed=20261055)
    (args.output/'config.yaml').write_text(OmegaConf.to_yaml(cfg,resolve=True))
    env=make_env(cfg);trace=[]
    try:
        env.reset();env._refresh_gym()
        # Original Sharpa mass randomization explicitly recomputes inertia.
        # Reproduce that operation after installing the logged masses.
        for handle,obj in zip(env.envs,env.object_handles):
            properties=env.gym.get_actor_rigid_body_properties(handle,obj)
            env.gym.set_actor_rigid_body_properties(handle,obj,properties,True)
        def repeat(name,part=old):return part[name][row].to(env.device).expand(env.num_envs,-1).clone()
        env.hand_dof_pos[:]=repeat('hand_dof_pos');env.hand_dof_vel[:]=repeat('hand_dof_vel')
        env.obj_dof_pos[:]=repeat('obj_dof_pos');env.obj_dof_state_vel[:]=repeat('obj_dof_state_vel')
        hand_pos,hand_rot=env._get_hand_base_pose()
        roots=env.root_state_tensor
        roots[env.object_indices,:3]=quat_apply(hand_rot,repeat('object_pos'))+hand_pos
        roots[env.object_indices,3:7]=quat_mul(hand_rot,repeat('object_rot'))
        roots[env.object_indices,7:10]=quat_apply(hand_rot,repeat('object_linvel'))
        roots[env.object_indices,10:13]=quat_apply(hand_rot,repeat('object_angvel'))
        ids=env.object_indices.to(torch.int32)
        env.gym.set_actor_root_state_tensor_indexed(env.sim,gymtorch.unwrap_tensor(roots),gymtorch.unwrap_tensor(ids),len(ids))
        env.gym.set_dof_state_tensor(env.sim,gymtorch.unwrap_tensor(env.dof_state))
        targets=repeat('cur_targets',current)
        assert targets.shape==env.cur_targets.shape and torch.isfinite(targets).all()
        env.cur_targets[:]=targets;env.prev_targets[:]=targets
        env.gym.set_dof_position_target_tensor(env.sim,gymtorch.unwrap_tensor(env.cur_targets))
        properties=[]
        for i in [0,7]:
            actor=env.gym.find_actor_handle(env.envs[i],'object')
            rigid=env.gym.get_actor_rigid_body_properties(env.envs[i],actor)
            body_names=env.gym.get_actor_rigid_body_names(env.envs[i],actor)
            semantic=[body_names.index(name) for name in ['link_0','link_1']]
            dof=env.gym.get_actor_dof_properties(env.envs[i],actor)
            shape=env.gym.get_actor_rigid_shape_properties(env.envs[i],actor)
            assert np.allclose([rigid[index].mass for index in semantic],mass,rtol=1e-5)
            assert np.allclose(dof['damping'],damping) and np.allclose(dof['stiffness'],0.)
            assert all(np.isclose(s.friction,friction) for s in shape)
            properties.append(dict(env=i,body_names=body_names,mass=[b.mass for b in rigid],damping=dof['damping'].tolist(),
                inertia=[[b.inertia.x.x,b.inertia.y.y,b.inertia.z.z] for b in rigid]))
        first_nonfinite=None
        names=['object_pos','object_rot','object_linvel','object_angvel','hand_dof_pos','hand_dof_vel','obj_dof_pos','obj_dof_state_vel']
        for tick in range(120):
            env.gym.simulate(env.sim);env.gym.fetch_results(env.sim,True);env._refresh_gym()
            values={k:getattr(env,k).detach().cpu().numpy().copy() for k in names}
            trace.append(values)
            if not all(np.isfinite(v).all() for v in values.values()):
                first_nonfinite=tick+1;break
        arrays={k:np.stack([frame[k] for frame in trace]) for k in names}
        np.savez_compressed(args.output/'trace.npz',**arrays)
        finite_stats={k:float(np.abs(v[np.isfinite(v)]).max()) if np.isfinite(v).any() else None for k,v in arrays.items()}
        result=dict(status='completed',scope=__doc__,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            instance=instance,object_profile=args.object_profile,source_row=row,num_identical_states=8,substeps=args.substeps,damping_factor=args.damping_factor,
            requested_damping=damping,properties=properties,first_nonfinite_sim_tick=first_nonfinite,
            simulated_ticks=len(trace),dt=env.dt,max_abs_finite=finite_stats,source_control_step=25,
            failure_next_control_window_ticks=4,physx_warm_start_restored=False,
            object_inertia_recomputed_as_original_dr=True,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        (args.output/'source.py').write_bytes(Path(__file__).read_bytes())
        print(json.dumps(result),flush=True)
    finally:env.gym.destroy_sim(env.sim)


if __name__=='__main__':main()
