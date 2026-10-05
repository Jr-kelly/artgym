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
        self.reverse_q=None
        if specification.get('reverse_rows'):
            assert specification['reverse_motor_preload']['all_feasible']
            assert not specification.get('posture_preload')
            assert len(specification['reverse_rows'])==len(rows)
            reverse_shifts=torch.tensor([r['shift_m'] for r in specification['reverse_rows']],device=device)
            assert torch.allclose(reverse_shifts,self.shifts)
            self.reverse_q=torch.tensor([r['q_thumb'] for r in specification['reverse_rows']],device=device)
            self.direction_blend_seconds=float(specification['reverse_motor_preload']['direction_blend_seconds'])
            assert self.direction_blend_seconds>=.5
        self.direction_weight=torch.zeros(n,device=device)
        self.direction_start=self.direction_weight.clone()
        self.direction_goal=self.direction_weight.clone()
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
        self.axial_jacobian=None
        if 'axial_jacobian_m_per_rad' in rows[0]:
            self.axial_jacobian=torch.tensor([r['axial_jacobian_m_per_rad'] for r in rows],device=device)
        self.tangent_tracking = specification.get('tangent_tracking')
        self.tracking_anchor = torch.zeros((n,4),device=device)
        self.tracking_initialized = torch.zeros(n,device=device,dtype=torch.bool)
        self.last_tangent_correction = torch.zeros((n,4),device=device)
        self.reversal_recenter=specification.get('reversal_recenter')
        self.recenter_offset=torch.zeros((n,4),device=device)
        self.recenter_start=self.recenter_offset.clone()
        self.recenter_goal=self.recenter_offset.clone()
        self.initial_deflection=self.recenter_offset.clone()
        self.support_retention=specification.get('support_posture_retention')
        self.support_measured_anchor=torch.zeros((n,16),device=device)
        self.last_support_correction=self.support_measured_anchor.clone()
        if 'support_offset_rad' in rows[0]:
            self.stroke_support=torch.tensor([r['support_offset_rad'] for r in rows],device=device)

    def reset(self, ids, clock_s=0.):
        self.age[ids] = 0
        self.previous_goal[ids] = float('nan')
        self.start[ids] = 0
        self.desired[ids] = 0
        self.direction_weight[ids]=0
        self.direction_start[ids]=0
        self.direction_goal[ids]=0
        self.tracking_initialized[ids]=False
        self.last_tangent_correction[ids]=0
        self.recenter_offset[ids]=0
        self.recenter_start[ids]=0
        self.recenter_goal[ids]=0
        self.initial_deflection[ids]=0
        self.last_support_correction[ids]=0
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
        first_command = torch.isnan(self.previous_goal)
        changed = first_command | ((goal-self.previous_goal).abs() > 1e-6)
        self.start[changed] = self.desired[changed]
        self.age[changed] = 0
        if self.reverse_q is not None:
            self.direction_start[changed]=self.direction_weight[changed]
            self.direction_goal[changed]=(goal[changed]<self.start[changed]).float()
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
        if self.reverse_q is not None:
            reverse=self.reverse_q[index]*(1.-alpha)+self.reverse_q[index+1]*alpha
            u_direction=(self.age*self.dt/self.direction_blend_seconds).clamp(0.,1.)
            blend=u_direction*u_direction*u_direction*(10.-15.*u_direction+6.*u_direction*u_direction)
            self.direction_weight=self.direction_start+(self.direction_goal-self.direction_start)*blend
            desired_q+=self.direction_weight[:,None]*(reverse-(first*(1.-alpha)+last*alpha))
        if self.reversal_recenter:
            # Re-anchor the next full stroke to the measured thumb posture at
            # a task reversal. This changes only the position reference; no
            # simulator state, measured history or issued memory is reset.
            assert measured_q is not None
            self.initial_deflection[first_command]=(issued[:,16:]-measured_q[:,16:])[first_command]
            reverse=changed & ~first_command
            self.recenter_start[reverse]=self.recenter_offset[reverse]
            bound=float(self.reversal_recenter['max_joint_rad'])
            measured_anchor=measured_q[:,16:]+self.initial_deflection
            correction=measured_anchor-desired_q
            if self.reversal_recenter.get('coordinates') in ['path-tangent','cartesian-axial']:
                tangent=(last-first)/(self.shifts[index+1]-self.shifts[index])[:,None]
                distance=(correction*tangent).sum(-1)/tangent.square().sum(-1).clamp_min(1e-6)
                if self.reversal_recenter.get('coordinates')=='cartesian-axial':
                    assert self.axial_jacobian is not None
                    jac=self.axial_jacobian[index]*(1-alpha)+self.axial_jacobian[index+1]*alpha
                    distance=(correction*jac).sum(-1)
                maximum=float(self.reversal_recenter['max_distance_m'])
                correction=distance.clamp(-maximum,maximum)[:,None]*tangent
            if self.reversal_recenter.get('retraction_only'):
                correction=torch.where((goal<self.start)[:,None],correction,torch.zeros_like(correction))
            self.recenter_goal[reverse]=correction.clamp(-bound,bound)[reverse]
            u=(self.age*self.dt/float(self.reversal_recenter['blend_seconds'])).clamp(0,1)
            blend=u*u*u*(10-15*u+6*u*u)
            self.recenter_offset=self.recenter_start+(self.recenter_goal-self.recenter_start)*blend[:,None]
            desired_q=desired_q+self.recenter_offset
        if self.tangent_tracking:
            # A bounded position-reference correction, not a force estimate.
            # Project current reference tracking error onto the calibrated
            # joint-space path tangent. Never integrate previously corrected
            # targets, and retain the initial static deflection as the zero.
            assert measured_q is not None
            fresh=~self.tracking_initialized
            if self.tangent_tracking.get('deflection_reference_update'):
                mode=self.tangent_tracking['deflection_reference_update']
                assert mode in ['reversal','extension']
                update=changed & ~first_command
                if mode=='extension':update &= goal>self.start
                # Re-estimate the reference's static joint error from current
                # legal measurements at a task event. This does not reset
                # observed history, issued commands, physics or the 40mm path.
                fresh=fresh | update
            self.tracking_anchor[fresh]=(desired_q-measured_q[:,16:])[fresh]
            self.tracking_initialized[:]=True
            tangent=(last-first)/(self.shifts[index+1]-self.shifts[index])[:,None]
            if self.reverse_q is not None:
                rt=(self.reverse_q[index+1]-self.reverse_q[index])/(self.shifts[index+1]-self.shifts[index])[:,None]
                tangent=tangent*(1-self.direction_weight[:,None])+rt*self.direction_weight[:,None]
            error=desired_q-measured_q[:,16:]-self.tracking_anchor
            distance=(error*tangent).sum(-1)/tangent.square().sum(-1).clamp_min(1e-6)
            if self.tangent_tracking.get('coordinates')=='cartesian-axial':
                assert self.axial_jacobian is not None
                jac=self.axial_jacobian[index]*(1-alpha)+self.axial_jacobian[index+1]*alpha
                distance=(error*jac).sum(-1)
            distance=distance.clamp(-float(self.tangent_tracking['max_distance_m']),float(self.tangent_tracking['max_distance_m']))
            gain=torch.full_like(distance,float(self.tangent_tracking['gain']))
            if self.tangent_tracking.get('phase_gain_ramp_s'):
                # Known elapsed stroke time only; preserve the full nominal
                # reference and endpoint gain, without live task-state input.
                begin,end=self.tangent_tracking['phase_gain_ramp_s']
                phase=((self.age*self.dt-float(begin))/(float(end)-float(begin))).clamp(0,1)
                phase=phase**3*(10-15*phase+6*phase**2)
                gain*=phase
            correction=gain[:,None]*distance[:,None]*tangent
            bound=float(self.tangent_tracking['max_joint_rad'])
            correction=correction.clamp(-bound,bound)
            if self.tangent_tracking.get('filter_seconds'):
                factor=self.dt/(float(self.tangent_tracking['filter_seconds'])+self.dt)
                self.last_tangent_correction+=(correction-self.last_tangent_correction)*factor
            else:self.last_tangent_correction=correction
            desired_q=desired_q+self.last_tangent_correction
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
        if self.support_retention:
            assert measured_q is not None
            self.support_measured_anchor[first_command]=measured_q[first_command,:16]
            correction=float(self.support_retention['gain'])*(self.support_measured_anchor-measured_q[:,:16])
            correction[:,12:]=0 # Ring has no established continuous support.
            bound=float(self.support_retention['max_joint_rad'])
            correction=correction.clamp(-bound,bound)
            alpha=float(self.support_retention['filter_fraction'])
            self.last_support_correction+=(correction-self.last_support_correction)*alpha
            self.last_target[:,:16]+=self.last_support_correction
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
