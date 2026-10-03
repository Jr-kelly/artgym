"""Known-command rolling-thumb reference; no live object or contact inputs.

The calibrated path is shared by all geometries and starts from the issued
initial motor targets. A new externally requested goal restarts a four-second
quintic ramp. This is a position/impedance reference, not force regulation.
"""
import torch


class ScheduledThumbReference:
    def __init__(self, specification, n, device, control_dt=1/30):
        assert specification['all_feasible']
        rows = specification['rows']
        self.shifts = torch.tensor([r['shift_m'] for r in rows], device=device)
        if specification.get('posture_preload'):
            assert specification['motor_geometry_passed'],'Rejected nominal motor geometry'
            self.q = torch.tensor([r['q_thumb_preloaded'] for r in rows], device=device)
        else:
            self.q = torch.tensor([r['q_thumb'] for r in rows], device=device)
        self.duration = float(specification.get('travel_seconds', 4.))
        self.dt = control_dt
        self.age = torch.zeros(n, device=device)
        self.previous_goal = torch.full((n,), float('nan'), device=device)
        self.start = torch.zeros(n, device=device)
        self.desired = torch.zeros(n, device=device)

    def reset(self, ids):
        self.age[ids] = 0
        self.previous_goal[ids] = float('nan')
        self.start[ids] = 0
        self.desired[ids] = 0

    def action(self, initial, issued, goal):
        goal = goal.reshape(-1).clamp(0., .04)
        changed = torch.isnan(self.previous_goal) | ((goal-self.previous_goal).abs() > 1e-6)
        self.start[changed] = self.desired[changed]
        self.age[changed] = 0
        self.previous_goal[:] = goal
        u = (self.age*self.dt/self.duration).clamp(0., 1.)
        fraction = u*u*u*(10.-15.*u+6.*u*u)
        self.desired[:] = self.start+(goal-self.start)*fraction
        index = torch.searchsorted(self.shifts, self.desired.contiguous(), right=True)-1
        index = index.clamp(0, len(self.shifts)-2)
        alpha = ((self.desired-self.shifts[index])/(self.shifts[index+1]-self.shifts[index])).unsqueeze(-1)
        desired_q = initial[:,16:]+self.q[index]*(1.-alpha)+self.q[index+1]*alpha-self.q[0]
        self.last_target = initial.clone()
        self.last_target[:,16:] = desired_q
        action = torch.zeros_like(initial)
        action[:,16:] = (desired_q-issued[:,16:])/.025
        self.age += 1
        return action.clamp(-1., 1.)
