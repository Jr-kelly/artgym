"""Training variant with externally timed goals and learned joint actions.

Arrival earns the existing success reward once per command, but never changes
the command. Physics, reward equations and observations are inherited. Normal
evaluation remains inherited; the independent timed audit controls its clock.
"""
import math

from isaacgymenvs.tasks.wuji_acquisition import WujiAcquisition


class WujiTimedAcquisition(WujiAcquisition):
    def __init__(self, cfg, *args, **kwargs):
        period = float(cfg["env"]["commandPeriodSec"])
        dt = float(cfg["sim"]["dt"]) * int(cfg["env"]["controlFrequencyInv"])
        self.command_period_steps = round(period / dt)
        if period < 0 or not math.isclose(self.command_period_steps * dt, period, abs_tol=1e-6):
            raise ValueError("Command period must be whole control steps; zero enables the arrival control")
        if cfg["env"]["goalSwitchTimeoutSec"] != 0 or cfg["env"]["maxConsecutiveSuccesses"] != 0:
            raise ValueError("Timed training requires no arrival timeout or success-budget reset")
        super().__init__(cfg, *args, **kwargs)

    def _activate_eval_session(self, *, stage_duration, **kwargs):
        # Training disables goal timeouts in both arms. Evaluation retains its
        # independently declared timeout; the timed audit subsequently replaces
        # it with its own fixed-time protocol.
        if stage_duration is None:
            stage_duration = float(self.cfg["env"]["evaluationGoalTimeoutSec"])
        return super()._activate_eval_session(stage_duration=stage_duration, **kwargs)

    def update_goal(self, env_ids):
        # ArtManip calls this on arrival. Keep the success latch set until the
        # clock changes the goal, so success is not rewarded repeatedly.
        if self.eval_mode or self.command_period_steps == 0:
            super().update_goal(env_ids)

    def compute_reward(self, actions):
        hold_bonus = None
        coefficient = float(self.cfg["env"].get("endpointHoldReward", 0.0))
        if coefficient and not self.eval_mode:
            import torch
            from scripts.wuji_endpoint_reward import endpoint_hold_reward
            from isaacgymenvs.utils.torch_jit_utils import quat_mul, quat_conjugate
            error = torch.norm(self.obj_dof_pos - self.goal_obj_dof_pos, p=1, dim=-1)
            angle = 2 * torch.asin(torch.norm(
                quat_mul(self.object_rot, quat_conjugate(self.init_object_rot))[:, :3], dim=-1).clamp(0, 1))
            hold_bonus = endpoint_hold_reward(error,
                self.training_success_hold_time + self.success_hold_steps_dt,
                torch.norm(self.object_pos - self.init_object_pos, dim=-1), angle,
                ~self.truncated_envs, self.object_cfg["task"]["success_threshold"],
                self.success_hold_duration, coefficient)
        # The transition reward must refer to the command that produced it.
        super().compute_reward(actions)
        if hold_bonus is not None:
            self.rew_buf += hold_bonus
            self.extras["EndpointHoldReward"] = hold_bonus.mean()
        if not self.eval_mode and self.command_period_steps > 0:
            due = (self.progress_buf > 0) & (self.progress_buf % self.command_period_steps == 0)
            due &= self.reset_buf == 0
            ids = due.nonzero(as_tuple=False).squeeze(-1)
            if len(ids):
                # Bypass the arrival override. This resets the existing goal
                # bookkeeping before post_physics_step builds observations.
                super().update_goal(ids)
            self.extras["TimedCommandSwitches"] = due.float().sum()
