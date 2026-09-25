"""Explicit Wuji acquisition variants; no scripted trajectory inside the task."""
import torch
from isaacgymenvs.tasks.wuji_demo_aligned import WujiDemoAligned


class WujiAcquisition(WujiDemoAligned):
    def sample_grasps(self,env_ids):
        states=super().sample_grasps(env_ids)
        noise=self.cfg['env'].get('initialPoseNoise')
        if not noise or self.eval_mode:return states
        from isaacgymenvs.tasks.wuji_reset_randomization import WujiTorchForwardKinematics,perturb_states
        end=int(noise.get('ramp_epochs',0))
        scale=min(1.,float(self.policy_update_step)/end) if end>0 else 1.
        if scale<=0:return states
        if not hasattr(self,'_reset_fk'):self._reset_fk=WujiTorchForwardKinematics(states.device,states.dtype)
        def uniform(width,limit):return (torch.rand((len(states),width),device=states.device)*2-1)*limit*scale
        delta=uniform(20,float(noise['joint_rad']))
        translation=uniform(3,float(noise['position_m']))
        rotvec=uniform(3,float(noise['rotation_vector_rad']))
        self.extras['reset_noise/scale']=scale
        return perturb_states(states,self.hand_dof_lower_limits,self.hand_dof_upper_limits,
            delta,translation,rotvec,self._reset_fk)

    def actions_to_targets(self,actions):
        initial=self.init_targets[:,:20]
        targets=initial+actions*float(self.cfg['env']['supportActionSpan'])
        targets[:,16:]=self.prev_targets[:,16:20]+float(self.cfg['env']['thumbActionStep'])*actions[:,16:]
        return torch.maximum(torch.minimum(targets,self.hand_dof_upper_limits),self.hand_dof_lower_limits)

    def targets_to_actions(self,targets):
        span=float(self.cfg['env']['supportActionSpan'])
        actions=(targets-self.init_targets[:,:20])/max(span,1e-8)
        actions[:,16:]=(targets[:,16:]-self.prev_targets[:,16:20])/float(self.cfg['env']['thumbActionStep'])
        if span==0:actions[:,:16]=0
        return actions

    def compute_reward(self,actions):
        super().compute_reward(actions)
        alive=(~self.truncated_envs).float()*float(self.cfg['env']['aliveReward'])
        if self.eval_mode:alive*=self.eval_active_mask
        self.rew_buf+=alive
        self.extras['Alive']=alive.mean()
        pose_objective = self.cfg['env'].get('absolutePoseObjective')
        if pose_objective:
            from scripts.wuji_pose_objective import absolute_pose_cost
            from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
            relative = quat_mul(self.object_rot, quat_conjugate(self.init_object_rot))
            angle = 2 * torch.asin(torch.norm(relative[:, :3], dim=-1).clamp(0, 1))
            cost = absolute_pose_cost(self.object_pos, self.init_object_pos, angle,
                                      pose_objective, self.policy_update_step)
            if self.eval_mode:
                cost *= self.eval_active_mask
            self.rew_buf += cost
            self.extras['AbsolutePoseCost'] = cost.mean()
