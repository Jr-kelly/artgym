"""Candidate CPU collection with batched GPU copies; no physical writes or sampling.

The caller chooses whether to install this after validating against the original
property reader. This module does not change any running task automatically.
"""
import numpy as np
import torch


def read_object_properties_batched(env):
    bodies = env.object_semantic_body_names
    mass = np.zeros((env.num_envs, len(bodies)), dtype=np.float32)
    friction = np.zeros((env.num_envs, 1), dtype=np.float32)
    damping = np.zeros((env.num_envs, 1), dtype=np.float32)
    stiffness = np.zeros((env.num_envs, 1), dtype=np.float32)
    default = env.object_cfg['default_props']
    if not env.randomize:
        default_mass = np.asarray(default['mass'], dtype=np.float32)
        mass[:, :default_mass.size] = default_mass
        friction.fill(float(default['friction']))
        damping.fill(float(default['dof_damping']))
        stiffness.fill(float(default.get('dof_stiffness', 0.)))
    else:
        for i in range(env.num_envs):
            handle, actor = env.envs[i], env.object_handles[i]
            rb = env.gym.get_actor_rigid_body_properties(handle, actor)
            rs = env.gym.get_actor_rigid_shape_properties(handle, actor)
            dof = env.gym.get_actor_dof_properties(handle, actor)
            body_indices = {name:j for j,name in enumerate(env.object_body_names[i])}
            mass[i] = [rb[body_indices[name]].mass for name in bodies]
            values = []
            for j, shape in enumerate(env.gym.get_actor_rigid_body_shape_indices(handle, actor)):
                if env.object_body_names[i][j] not in bodies:
                    continue
                for offset in range(shape.count):
                    values.append(rs[shape.start+offset].friction)
            friction[i, 0] = float(sum(values)/len(values)) if values else float(default['friction'])
            stiffness[i, 0] = np.asarray(dof['stiffness'], dtype=np.float32).reshape(-1)[0]
            damping[i, 0] = np.asarray(dof['damping'], dtype=np.float32).reshape(-1)[0]
    env.object_mass = torch.from_numpy(mass).to(env.device)
    env.object_friction = torch.from_numpy(friction).to(env.device)
    env.object_dof_damping = torch.from_numpy(damping).to(env.device)
    env.object_dof_stiffness = torch.from_numpy(stiffness).to(env.device)
