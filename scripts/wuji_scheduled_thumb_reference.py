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
        self.measured_hold_reference=bool(specification.get('calibrate_from_measured_hold'))
        self.age = torch.zeros(n, device=device)
        self.previous_goal = torch.full((n,), float('nan'), device=device)
        self.start = torch.zeros(n, device=device)
        self.desired = torch.zeros(n, device=device)
        self.pacing = specification.get('joint_lag_pacing')
        self.static_joint_lag = torch.zeros((n,4),device=device)
        self.last_progress_lag_m = torch.zeros(n,device=device)
        self.last_pacing_rate = torch.ones(n,device=device)
        self.preload_schedule=specification.get('support_preload_schedule')
        self.preload_anchor=torch.zeros((n,20),device=device)
        self.preload_delta=None
        if self.preload_schedule:self.preload_delta=torch.tensor(self.preload_schedule['delta_q'],device=device)
        self.stroke_support=None
        if 'support_offset_rad' in rows[0]:
            self.stroke_support=torch.tensor([r['support_offset_rad'] for r in rows],device=device)

    def reset(self, ids, clock_s=0.):
        self.age[ids] = 0
        self.previous_goal[ids] = float('nan')
        self.start[ids] = 0
        self.desired[ids] = 0
        if self.preload_schedule:
            value=self.preload(clock_s)
            self.preload_anchor[ids]=value[ids] if value.ndim==2 else value

    def preload(self,clock_s):
        first,last=self.preload_schedule['seconds']
        t=torch.as_tensor(clock_s,device=self.age.device,dtype=self.age.dtype)
        u=((t-first)/(last-first)).clamp(0.,1.)
        fraction=u*u*u*(10.-15.*u+6.*u*u)
        return fraction[...,None]*self.preload_delta

    def action(self, initial, issued, goal, measured_q=None,clock_s=None):
        goal = goal.reshape(-1).clamp(0., .04)
        changed = torch.isnan(self.previous_goal) | ((goal-self.previous_goal).abs() > 1e-6)
        self.start[changed] = self.desired[changed]
        self.age[changed] = 0
        self.previous_goal[:] = goal
        if self.pacing:
            assert measured_q is not None, 'Pacing requires legal measured joints'
            self.static_joint_lag[changed] = (issued[:,16:]-measured_q[:,16:])[changed]
        u = (self.age*self.dt/self.duration).clamp(0., 1.)
        fraction = u*u*u*(10.-15.*u+6.*u*u)
        self.desired[:] = self.start+(goal-self.start)*fraction
        index = torch.searchsorted(self.shifts, self.desired.contiguous(), right=True)-1
        index = index.clamp(0, len(self.shifts)-2)
        alpha = ((self.desired-self.shifts[index])/(self.shifts[index+1]-self.shifts[index])).unsqueeze(-1)
        if self.q.ndim==3:
            ids=torch.arange(len(initial),device=initial.device)
            first,last,zero=self.q[ids,index],self.q[ids,index+1],self.q[:,0]
        else:first,last,zero=self.q[index],self.q[index+1],self.q[0]
        desired_q = initial[:,16:]+first*(1.-alpha)+last*alpha-zero
        self.last_target = initial.clone()
        self.last_target[:,16:] = desired_q
        if self.stroke_support is not None:
            if self.stroke_support.ndim==3:
                ids=torch.arange(len(initial),device=initial.device)
                support_first,support_last=self.stroke_support[ids,index],self.stroke_support[ids,index+1]
                support_zero=self.stroke_support[:,0]
            else:
                support_first,support_last=self.stroke_support[index],self.stroke_support[index+1]
                support_zero=self.stroke_support[0]
            self.last_target[:,:16]+=support_first*(1.-alpha)+support_last*alpha-support_zero
        if self.preload_schedule:
            assert clock_s is not None, 'Preload transition requires the known episode clock'
            self.last_target+=self.preload(clock_s)-self.preload_anchor
        action = (self.last_target-initial)/.04
        action[:,16:] = (self.last_target[:,16:]-issued[:,16:])/.025
        rate = torch.ones_like(self.age)
        if self.pacing:
            tangent=(last-first)/(self.shifts[index+1]-self.shifts[index])[:,None]
            excess=issued[:,16:]-measured_q[:,16:]-self.static_joint_lag
            lag=(excess*tangent).sum(-1)/tangent.square().sum(-1).clamp_min(1e-6)
            # Estimate of joint tracking along the nominal trajectory, not
            # slider travel, contact state or force. Reversals use the new
            # task direction; a small minimum rate keeps finite progress.
            direction=torch.sign(goal-self.start)
            self.last_progress_lag_m=lag*direction
            rate=(1-self.last_progress_lag_m.clamp_min(0)/float(self.pacing['lag_scale_m'])).clamp(float(self.pacing['minimum_rate']),1.)
        self.last_pacing_rate=rate
        self.age += rate
        return action.clamp(-1., 1.)
