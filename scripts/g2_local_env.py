"""Full G2+Wuji local training task. State writes occur ONLY in reset().

This is a local-training reset, never evidence of continuous acquisition.
Scene properties are the versioned effective values of R3-12. No wrist clamp,
object force, changed friction, or slider drive. Quaternion convention xyzw.
"""
from pathlib import Path
import json
import math

from isaacgym import gymapi, gymtorch  # before torch
import numpy as np
import torch
from omegaconf import OmegaConf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'configs/g2_local'


def qmul(a, b):
    return torch.cat((a[..., 3:] * b[..., :3] + b[..., 3:] * a[..., :3] +
                      torch.cross(a[..., :3], b[..., :3], dim=-1),
                      a[..., 3:] * b[..., 3:] - (a[..., :3] * b[..., :3]).sum(-1, keepdim=True)), -1)


def qinv(q):
    return torch.cat((-q[..., :3], q[..., 3:]), -1)


def qrot(q, v):
    t = 2 * torch.cross(q[..., :3], v, dim=-1)
    return v + q[..., 3:] * t + torch.cross(q[..., :3], t, dim=-1)


def local_pose(w, o):
    qi = qinv(w[..., 3:7])
    return torch.cat((qrot(qi, o[..., :3] - w[..., :3]), qmul(qi, o[..., 3:7])), -1)


def rotation_error(a, b):
    q = qmul(qinv(a), b)
    return 2 * torch.atan2(q[..., :3].norm(dim=-1), q[..., 3].abs())


class LocalG2:
    """CPU tensor pipeline, GPU PhysX, batched observations and real G2 servo.

    Residual changes motor reference only: <=0.20rad offset and <=0.60rad/s.
    Those are new control bounds, below asset velocity limits, not physics edits.
    Route A: support16 absolute bounded residuals. Route B: same support16,
    plus4 corrections to frozen thumb increments, total <=.025rad/step.
    """
    def __init__(self, task='H', num_envs=1, route='support', graphics=False,
                 state_path=None, residual_span=.20, residual_speed=.60, hand_gravity=False):
        self.task, self.n, self.route = task, num_envs, route
        self.goal_override = None  # only for explicitly scored physical preparation diagnostics
        self.thumb_first_stroke_q4_correction = 0.  # explicit diagnostic only, never changed by training
        self.thumb_plan = None
        self.span, self.speed = residual_span, residual_speed
        self.action_dim = 16 if route == 'support' else 20
        self.steps = 660 if task == 'H' else 600
        self.dt = 1 / 30
        self.metadata = json.loads((DATA / 'physics.json').read_text())
        self.source = {k: torch.as_tensor(v.copy()) for k, v in np.load(
            state_path or DATA / (task + '-actual-state.npz')).items()}
        self.cfg = OmegaConf.load(DATA / 'frozen-config.yaml')
        self.gym = gymapi.acquire_gym()
        sp = gymapi.SimParams()
        sp.dt = float(self.cfg.task.sim.dt)
        sp.substeps = int(self.cfg.task.sim.substeps)
        assert abs(sp.dt * 4 - self.dt) < 1e-7
        sp.up_axis = gymapi.UP_AXIS_Z
        sp.gravity = gymapi.Vec3(0, 0, -9.81)
        sp.use_gpu_pipeline = False
        for name in ['solver_type', 'num_position_iterations', 'num_velocity_iterations',
                     'contact_offset', 'rest_offset', 'bounce_threshold_velocity',
                     'max_depenetration_velocity', 'default_buffer_size_multiplier', 'max_gpu_contact_pairs']:
            setattr(sp.physx, name, self.cfg.task.sim.physx[name])
        sp.physx.num_threads = 2
        sp.physx.use_gpu = True
        sp.physx.contact_collection = gymapi.ContactCollection.CC_ALL_SUBSTEPS
        self.sim = self.gym.create_sim(0, 0 if graphics else -1, gymapi.SIM_PHYSX, sp)
        if self.sim is None:
            raise RuntimeError('Failed to create full G2 PhysX simulation')
        opt = gymapi.AssetOptions()
        opt.fix_base_link = True
        opt.collapse_fixed_joints = False
        opt.disable_gravity = False
        opt.thickness = .001
        opt.angular_damping = .01
        opt.use_physx_armature = True
        opt.default_dof_drive_mode = gymapi.DOF_MODE_POS
        robot_asset = self.gym.load_asset(self.sim, str(ROOT), 'assets/robots/g2_wuji/g2_wuji.urdf', opt)
        opt = gymapi.AssetOptions()
        opt.fix_base_link = True
        table_asset = self.gym.create_box(self.sim, .60, .80, .05, opt)
        opt = gymapi.AssetOptions()
        opt.override_com = True
        opt.override_inertia = True
        opt.fix_base_link = False
        opt.disable_gravity = False
        opt.thickness = .01
        opt.density = 1000
        opt.collapse_fixed_joints = False
        opt.default_dof_drive_mode = gymapi.DOF_MODE_POS
        knife_asset = self.gym.load_asset(self.sim, str(ROOT),
            'assets/objects/knife_wuji_bridge3_20260922/000/mobility.urdf', opt)
        floor = gymapi.PlaneParams()
        floor.normal = gymapi.Vec3(0, 0, 1)
        self.gym.add_ground(self.sim, floor)
        self.envs, self.origins, self.robot_ids, self.knife_ids = [], [], [], []
        self.contact_maps = []
        self.body_ids = {k: [] for k in ['wrist', 'object', 'slider', 'table']}
        self.hand_body_ids = []
        for i in range(num_envs):
            env = self.gym.create_env(self.sim, gymapi.Vec3(-2, -2, 0), gymapi.Vec3(2, 2, 3),
                                      max(1, int(math.sqrt(num_envs))))
            self.envs.append(env)
            origin = self.gym.get_env_origin(env)
            self.origins.append([origin.x, origin.y, origin.z])
            robot = self.gym.create_actor(env, robot_asset, gymapi.Transform(), 'g2', i, 0)
            names = self.gym.get_actor_dof_names(env, robot)
            assert names == self.metadata['robot_dof_names']
            props = self.gym.get_actor_dof_properties(env, robot)
            for field, values in self.metadata['robot_dof_properties'].items():
                props[field] = values
            self.gym.set_actor_dof_properties(env, robot, props)
            bodyprops = self.gym.get_actor_rigid_body_properties(env, robot)
            for p, flag, name in zip(bodyprops, self.metadata['robot_gravity_flags'],self.metadata['robot_body_names']):
                p.flags = 0 if hand_gravity and name.startswith('hand_r_') else flag
            self.gym.set_actor_rigid_body_properties(env, robot, bodyprops)
            if i==0:
                self.effective_gravity_flags=[int(p.flags) for p in self.gym.get_actor_rigid_body_properties(env,robot)]
            shapes = self.gym.get_actor_rigid_shape_properties(env, robot)
            assert len(shapes) == len(self.metadata['collision_filters'])
            for p, filt in zip(shapes, self.metadata['collision_filters']):
                p.filter = filt
                p.friction = 1.
            self.gym.set_actor_rigid_shape_properties(env, robot, shapes)
            t = gymapi.Transform()
            t.p = gymapi.Vec3(.60, -.25, self.metadata['table_top'] - .025)
            table = self.gym.create_actor(env, table_asset, t, 'table', i, 0)
            self.gym.set_rigid_body_color(env, table, 0, gymapi.MESH_VISUAL, gymapi.Vec3(.40, .31, .23))
            t = gymapi.Transform()
            o = self.source['object_rigid_state']
            t.p = gymapi.Vec3(*o[:3].tolist())
            t.r = gymapi.Quat(*o[3:7].tolist())
            knife = self.gym.create_actor(env, knife_asset, t, 'knife', i, 0)
            props = self.gym.get_actor_dof_properties(env, knife)
            for field, values in self.metadata['knife_dof_properties'].items():
                props[field] = values
            self.gym.set_actor_dof_properties(env, knife, props)
            bodies = self.gym.get_actor_rigid_body_properties(env, knife)
            for p, mass in zip(bodies, self.metadata['knife_mass']):
                p.mass = mass
            self.gym.set_actor_rigid_body_properties(env, knife, bodies)
            shapes = self.gym.get_actor_rigid_shape_properties(env, knife)
            for p in shapes:
                p.friction, p.filter = 3., 1
            self.gym.set_actor_rigid_shape_properties(env, knife, shapes)
            self.robot_ids.append(self.gym.get_actor_index(env, robot, gymapi.DOMAIN_SIM))
            self.knife_ids.append(self.gym.get_actor_index(env, knife, gymapi.DOMAIN_SIM))
            for key, actor, name in [('wrist', robot, 'hand_r_base_link'), ('object', knife, 'link_0'),
                                      ('slider', knife, 'link_1')]:
                self.body_ids[key].append(self.gym.find_actor_rigid_body_index(env, actor, name, gymapi.DOMAIN_SIM))
            self.body_ids['table'].append(self.gym.get_actor_rigid_body_index(env, table, 0, gymapi.DOMAIN_SIM))
            rb_names = self.gym.get_actor_rigid_body_names(env, robot)
            self.contact_maps.append({self.gym.get_actor_rigid_body_index(env, actor, j, gymapi.DOMAIN_ENV): name
                for actor in [robot, table, knife]
                for j, name in enumerate(self.gym.get_actor_rigid_body_names(env, actor))})
            self.hand_body_ids.append([self.gym.find_actor_rigid_body_index(env, robot, n, gymapi.DOMAIN_SIM)
                                      for n in rb_names if n.startswith('hand_r_')])
        self.origins = torch.tensor(self.origins)
        self.robot_ids = torch.tensor(self.robot_ids, dtype=torch.int32)
        self.knife_ids = torch.tensor(self.knife_ids, dtype=torch.int32)
        self.body_ids = {k: torch.tensor(v) for k, v in self.body_ids.items()}
        self.hand_body_ids = torch.tensor(self.hand_body_ids)
        self.gym.prepare_sim(self.sim)
        self.roots = gymtorch.wrap_tensor(self.gym.acquire_actor_root_state_tensor(self.sim))
        self.gym.refresh_actor_root_state_tensor(self.sim)
        self.dof = gymtorch.wrap_tensor(self.gym.acquire_dof_state_tensor(self.sim)).view(self.n, 28, 2)
        self.rb = gymtorch.wrap_tensor(self.gym.acquire_rigid_body_state_tensor(self.sim))
        self.contact = gymtorch.wrap_tensor(self.gym.acquire_net_contact_force_tensor(self.sim))
        self.lower = torch.tensor(self.metadata['robot_dof_properties']['lower'])
        self.upper = torch.tensor(self.metadata['robot_dof_properties']['upper'])
        self.slider_lower = float(self.metadata['knife_dof_properties']['lower'][0])
        self.targets = torch.zeros(self.n, 28)
        self.command = self.targets.clone()
        self.integral = torch.zeros(self.n, 7)
        self.age = torch.zeros(self.n, dtype=torch.long)
        self.residual = torch.zeros(self.n, self.action_dim)
        self.last_action = torch.zeros_like(self.residual)
        self.object = torch.zeros(self.n, 13)
        self.slider_pose = self.object.clone()
        self.wrist = self.object.clone()
        self.initial_object = torch.zeros(self.n, 7)
        self.initial_local = self.initial_object.clone()
        self.max_drift = torch.zeros(self.n)
        self.max_rotation = torch.zeros(self.n)
        self.max_hand_drift = torch.zeros(self.n)
        self.max_hand_rotation = torch.zeros(self.n)
        self.endpoint_errors = torch.zeros(self.n, 4)
        self.min_slider = torch.zeros(self.n)
        self.max_slider = torch.zeros(self.n)
        self.max_slider_goal_error = torch.zeros(self.n)
        self.first_unstable = torch.full((self.n,), -1, dtype=torch.long)
        self.ever_drop = torch.zeros(self.n, dtype=torch.bool)
        self.teacher = None
        self.reset()

    def reset(self, ids=None):
        """The only physics-state write path, explicitly a local episode reset."""
        ids = torch.arange(self.n) if ids is None else ids.long()
        self.dof[ids, :, 0] = self.source['all_dof_position'].float()
        self.dof[ids, :, 1] = self.source['dof_velocity'].float()
        self.roots[self.knife_ids[ids].long()] = self.source['object_rigid_state'].float()
        # This installed IsaacGym CPU tensor pipeline reports poses in each
        # environment's world frame (confirmed using root/rigid APIs in N=2).
        # Adding create_env grid origins displaces only the free knife and is
        # WRONG. Origins are scene-layout metadata, never reset coordinates.
        actor_ids = torch.cat((self.robot_ids[ids], self.knife_ids[ids])).contiguous()
        self.gym.set_dof_state_tensor_indexed(self.sim, gymtorch.unwrap_tensor(self.dof),
                                            gymtorch.unwrap_tensor(actor_ids), len(actor_ids))
        knife_ids = self.knife_ids[ids].contiguous()
        self.gym.set_actor_root_state_tensor_indexed(self.sim, gymtorch.unwrap_tensor(self.roots),
                                                    gymtorch.unwrap_tensor(knife_ids), len(knife_ids))
        self.targets[ids] = self.source['reference_targets'].float()
        self.command[ids] = self.source['targets'].float()
        self.integral[ids] = self.source['arm_integral_state'].float()
        self.gym.set_dof_position_target_tensor(self.sim, gymtorch.unwrap_tensor(self.command))
        self.age[ids] = 0
        self.residual[ids] = 0
        self.last_action[ids] = 0
        self.object[ids] = self.source['object_rigid_state'].float()
        self.slider_pose[ids] = self.source['slider_rigid_state'].float()
        self.wrist[ids] = 0
        self.wrist[ids, :7] = self.source['wrist'].float()
        self.initial_object[ids] = self.object[ids, :7]
        self.initial_local[ids] = local_pose(self.wrist[ids], self.object[ids])
        self.max_drift[ids] = 0
        self.max_rotation[ids] = 0
        self.max_hand_drift[ids] = 0
        self.max_hand_rotation[ids] = 0
        self.endpoint_errors[ids] = 0
        self.min_slider[ids] = self.dof[ids, 27, 0]
        self.max_slider[ids] = self.dof[ids, 27, 0]
        self.max_slider_goal_error[ids] = 0
        self.first_unstable[ids] = -1
        self.ever_drop[ids] = False
        if self.teacher is not None:
            self.teacher.reset(ids)
        return self.observation()

    def refresh(self):
        self.gym.refresh_dof_state_tensor(self.sim)
        self.gym.refresh_rigid_body_state_tensor(self.sim)
        self.gym.refresh_net_contact_force_tensor(self.sim)
        for key in ['object', 'slider', 'wrist']:
            dst = self.slider_pose if key == 'slider' else getattr(self, key)
            dst[:] = self.rb[self.body_ids[key]]

    def goal(self):
        if self.goal_override is not None:
            return torch.full((self.n,), self.slider_lower + self.goal_override)
        if self.task == 'H':
            return self.source['slider'].float().expand(self.n)
        return self.slider_lower + ((self.age // 150) % 2 == 0).float() * .04

    def start_operation_window(self):
        """Once-only stage boundary: metrics/clock reference, NO physics reset.

        Used only after an explicitly logged physical closed-goal preparation.
        q/qd, object, motor targets, residual, integrator, teacher RNN/init/history
        are untouched. Preparation is independently scored against its old ref.
        """
        self.goal_override = None
        self.age.zero_()
        self.initial_object[:] = self.object[:, :7]
        self.initial_local[:] = local_pose(self.wrist,self.object)
        for name in ['max_drift','max_rotation','max_hand_drift','max_hand_rotation','max_slider_goal_error']:
            getattr(self,name).zero_()
        self.endpoint_errors.zero_()
        self.min_slider[:] = self.dof[:,27,0]
        self.max_slider[:] = self.dof[:,27,0]
        self.first_unstable.fill_(-1)
        self.ever_drop.zero_()

    def observation(self):
        """Privileged upper bound: q/qd/refs, object+slider pose/vel, wrist, clock.

        Fixed initial reference, current bodytruth, no tactile sensor assumption.
        All normalized scales are fixed, never success thresholds.
        """
        q = self.dof[:, 7:27, 0]
        qn = 2 * (q - self.lower[7:27]) / (self.upper[7:27] - self.lower[7:27]) - 1
        local = local_pose(self.wrist, self.object)
        qe = qmul(qinv(self.initial_object[:, 3:7]), self.object[:, 3:7])
        qe = qe * torch.where(qe[:, 3:] < 0, -1., 1.)
        return torch.cat((qn, self.dof[:, 7:27, 1] * .1,
            (self.targets[:, 7:27] - q) * 5,
            (self.object[:, :3] - self.initial_object[:, :3]) * 100,
            qe[:, :3] * 4, local[:, :3] * 10, local[:, 3:7],
            self.object[:, 7:10] * 10, self.object[:, 10:13],
            (self.dof[:, 27:28, 0] - self.slider_lower) * 25,
            self.dof[:, 27:28, 1] * 10, (self.goal().unsqueeze(-1) - self.slider_lower) * 25,
            (self.goal() - self.dof[:, 27, 0]).unsqueeze(-1) * 25,
            (self.age.float() / self.steps).unsqueeze(-1), self.residual / self.span,
            self.last_action), -1).clamp(-20, 20)

    def step(self, action, baseline='learned'):
        action = action.detach().cpu().clamp(-1, 1)
        if action.shape != (self.n, self.action_dim):
            raise ValueError('Action order/shape mismatch')
        previous_action = self.last_action.clone()
        self.last_action[:] = action
        previous_thumb = self.targets[:, 23:27].clone()
        if self.teacher is not None and self.task == 'S':
            self.teacher.step(full=baseline == 'full-teacher')
            if self.thumb_first_stroke_q4_correction:
                assert self.route == 'support' and baseline != 'full-teacher'
                # One preregistered first-stroke articulation diagnostic. Total
                # thumb motion remains <= the original .025rad/control bound.
                self.targets[:, 26] += .025 * self.thumb_first_stroke_q4_correction * (self.age < 150)
                self.targets[:, 23:27] = previous_thumb + (self.targets[:, 23:27]-previous_thumb).clamp(-.025,.025)
        if self.thumb_plan is not None:
            assert self.task == 'S' and self.teacher is None
            from scripts.g2_thumb_path import thumb_path_targets
            target, _ = thumb_path_targets(self.thumb_plan,self.age.numpy(),self.source['reference_targets'][23:27].numpy())
            target = torch.as_tensor(target,dtype=torch.float32)
            self.targets[:,23:27] = target if self.route=='joint' else previous_thumb + (target-previous_thumb).clamp(-.025,.025)
        if baseline == 'learned':
            wanted = action[:, :16] * self.span
            self.residual[:, :16] += (wanted - self.residual[:, :16]).clamp(-self.speed * self.dt, self.speed * self.dt)
            self.targets[:, 7:23] = self.source['reference_targets'][7:23] + self.residual[:, :16]
            if self.route == 'joint':
                nominal_thumb = torch.max(self.lower[23:27], torch.min(self.upper[23:27], self.targets[:, 23:27]))
                if self.thumb_plan is not None:
                    # Moving kinematic prior + bounded persistent joint offset.
                    # Unlike an incremental teacher, this absolute prior would
                    # erase yesterday's .025rad correction on every step.
                    wanted_thumb=action[:,16:]*self.span
                    self.residual[:,16:]+=(wanted_thumb-self.residual[:,16:]).clamp(-self.speed*self.dt,self.speed*self.dt)
                    increment=(nominal_thumb+self.residual[:,16:]-previous_thumb).clamp(-.025,.025)
                else:
                    increment = (nominal_thumb - previous_thumb + .025 * action[:, 16:]).clamp(-.025, .025)
                self.targets[:, 23:27] = torch.max(self.lower[23:27], torch.min(self.upper[23:27], previous_thumb + increment))
                if self.thumb_plan is None:
                    self.residual[:, 16:] = self.targets[:, 23:27] - nominal_thumb
        self.targets[:, :27] = torch.max(self.lower, torch.min(self.upper, self.targets[:, :27]))
        if (self.route == 'joint' or self.thumb_first_stroke_q4_correction) and self.teacher is not None:
            self.teacher.last_action[:, 16:] = (self.targets[:, 23:27] - previous_thumb) / .025
        self.integral += self.dt * (self.targets[:, :7] - self.dof[:, :7, 0])
        self.integral.clamp_(-.08, .08)
        self.command[:] = self.targets
        self.command[:, :7] = torch.max(self.lower[:7], torch.min(self.upper[:7], self.targets[:, :7] + self.integral))
        self.gym.set_dof_position_target_tensor(self.sim, gymtorch.unwrap_tensor(self.command))
        old_goal = self.goal().clone()
        for _ in range(4):
            self.gym.simulate(self.sim)
            self.gym.fetch_results(self.sim, True)
        self.refresh()
        if self.teacher is not None:
            self.teacher.record()
        drift = (self.object[:, :3] - self.initial_object[:, :3]).norm(dim=-1)
        rot = rotation_error(self.initial_object[:, 3:7], self.object[:, 3:7])
        err = (self.dof[:, 27, 0] - old_goal).abs()
        self.max_slider_goal_error = torch.maximum(self.max_slider_goal_error, err)
        self.max_drift = torch.maximum(self.max_drift, drift)
        self.max_rotation = torch.maximum(self.max_rotation, rot)
        rel = local_pose(self.wrist, self.object)
        self.max_hand_drift = torch.maximum(self.max_hand_drift,
            (rel[:, :3]-self.initial_local[:, :3]).norm(dim=-1))
        self.max_hand_rotation = torch.maximum(self.max_hand_rotation,
            rotation_error(self.initial_local[:, 3:7], rel[:, 3:7]))
        self.min_slider = torch.minimum(self.min_slider, self.dof[:, 27, 0])
        self.max_slider = torch.maximum(self.max_slider, self.dof[:, 27, 0])
        bad = (drift >= .01) | (rot >= .25)
        first = (self.first_unstable < 0) & bad
        self.first_unstable[first] = self.age[first] + 1
        drop = (self.object[:, 2] < self.metadata['table_top'] + .05) | (drift > .1)
        self.ever_drop |= drop
        if self.task == 'S':
            window = self.age % 150 >= 141
            ids = window.nonzero(as_tuple=False).squeeze(-1)
            stage = (self.age[ids] // 150).clamp(max=3)
            self.endpoint_errors[ids, stage] = torch.maximum(self.endpoint_errors[ids, stage], err[ids])
        # Dense shaping is separate from independent max-over-episode metrics.
        hold = torch.exp(-((drift / .008) ** 2 + (rot / .20) ** 2))
        reward = 3 * hold - .25 * (drift / .01).clamp(max=10) - .25 * (rot / .25).clamp(max=10)
        if self.task == 'S':
            # Sliding only rewarded with stable body; no passive/drop credit.
            reward += 3 * torch.exp(-err / .01) * hold
        else:
            reward -= .25 * (err / .01).clamp(max=5)
        reward -= .01 * action.square().mean(-1) + .01 * (action - previous_action).square().mean(-1)
        reward -= 10 * drop.float()
        self.age += 1
        # Hard safety failures terminate training, never count success.
        invalid = ~torch.isfinite(self.dof).all(dim=-1).all(dim=-1) | ~torch.isfinite(self.object).all(-1)
        terminated = drop | (rot > 1.5) | invalid
        timeout = self.age >= self.steps
        # A safety reset must not erase the failed remainder of a finite task.
        # Charge an absorbing -8/step through the original horizon, discounted
        # exactly as PPO (gamma=.995). -8 is below the bounded valid shaping
        # reward (H >= -6.30, S >= -5.05). No change to physics or evaluation.
        remaining = (self.steps - self.age + 1).clamp(min=1)
        absorbing = -8. * (1. - .995 ** remaining.float()) / (1. - .995)
        reward = torch.where(terminated, absorbing, reward.clamp(min=-8.))
        info = dict(drift=drift, rotation=rot, endpoint_error=err, terminated=terminated, timeout=timeout,
                    absorbing_terminal_reward=torch.where(terminated, absorbing, torch.zeros_like(reward)))
        return self.observation(), reward, terminated | timeout, info

    def metrics(self):
        complete = self.age >= self.steps
        stable = (self.max_drift < .01) & (self.max_rotation < .25) & ~self.ever_drop
        endpoint = (self.endpoint_errors < .01).all(-1) if self.task == 'S' else self.max_slider_goal_error < .01
        return dict(complete=complete, stable=stable, endpoints_10mm=complete & endpoint,
            endpoints_2mm=complete & ((self.endpoint_errors < .002).all(-1) if self.task=='S' else self.max_slider_goal_error < .002),
            endpoint_windows_observed=self.age.unsqueeze(-1) >= torch.tensor([150,300,450,600]) if self.task=='S' else complete.unsqueeze(-1),
            success=complete & stable & endpoint, maximum_slider_goal_error_m=self.max_slider_goal_error,
            world_drift_m=self.max_drift, world_rotation_rad=self.max_rotation,
            hand_relative_drift_m=self.max_hand_drift, hand_relative_rotation_rad=self.max_hand_rotation,
            endpoint_max_errors_m=self.endpoint_errors, slider_travel_m=self.max_slider-self.min_slider,
            first_instability_s=torch.where(self.first_unstable<0, -1., self.first_unstable.float()/30), drop=self.ever_drop)

    def contacts_for_evaluation(self):
        """Contact pairs are evaluation-only diagnostics, not force measurements."""
        counts = torch.zeros(self.n, 5, dtype=torch.int32)
        slider = counts.clone()
        table = torch.zeros(self.n, dtype=torch.int32)
        for i, env in enumerate(self.envs):
            names = self.contact_maps[i]
            for c in self.gym.get_env_rigid_contacts(env):
                if c['lambda'] <= 1e-6:
                    continue
                pair = [names.get(int(c[key]), 'ground') for key in ['body0','body1']]
                knife = any(n in ['link_0','link_1'] for n in pair)
                for j, finger in enumerate(['thumb','index','middle','ring','pinky']):
                    if any('_'+finger+'_' in n for n in pair) and knife:
                        counts[i,j] += 1
                        if 'link_1' in pair:
                            slider[i,j] += 1
                if knife and 'box' in pair:
                    table[i] += 1
        return dict(finger_knife_contacts=counts.numpy(), finger_slider_contacts=slider.numpy(), knife_table_contacts=table.numpy())

    def frame(self):
        frame = dict(time=self.age.numpy().copy()/30, q=self.dof[:, 7:27, 0].numpy().copy(),
            all_dof_position=self.dof[:, :, 0].numpy().copy(), dof_velocity=self.dof[:, :, 1].numpy().copy(),
            object_rigid_state=self.object.numpy().copy(), slider_rigid_state=self.slider_pose.numpy().copy(),
            wrist=self.wrist[:, :7].numpy().copy(), targets=self.command.numpy().copy(),
            reference_targets=self.targets.numpy().copy(), arm_integral_state=self.integral.numpy().copy(),
            action=self.last_action.numpy().copy(), residual=self.residual.numpy().copy(),
            slider=self.dof[:, 27, 0].numpy().copy(), hand_force=self.contact[self.hand_body_ids].numpy().copy(),
            fixed_object_reference=self.initial_object.numpy().copy(),
            object_hand=local_pose(self.wrist,self.object).numpy().copy(),
            fixed_hand_reference=self.initial_local.numpy().copy())
        if self.teacher is not None:
            frame.update(teacher_raw_action=self.teacher.raw_action.numpy().copy(),
                teacher_action=self.teacher.last_action.numpy().copy(),
                teacher_observation=self.teacher.last_obs.numpy().copy())
        if self.thumb_plan is not None:
            from scripts.g2_thumb_path import thumb_path_targets
            target, distance = thumb_path_targets(self.thumb_plan,(self.age-1).clamp(min=0).numpy(),self.source['reference_targets'][23:27].numpy())
            frame.update(thumb_plan_motor_targets=target, thumb_plan_desired_distance_m=distance)
        return frame

    def close(self):
        self.gym.destroy_sim(self.sim)
